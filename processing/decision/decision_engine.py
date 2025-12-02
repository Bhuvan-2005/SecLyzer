#!/usr/bin/env python3
"""
Decision Engine for SecLyzer
Makes authentication decisions based on confidence scores from inference engine
"""

import json
import os
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import redis

from common.developer_mode import get_developer_mode
from common.logger import get_logger
from storage.database import get_database

logger = get_logger(__name__)


class AuthState(Enum):
    """Authentication states."""

    NORMAL = "normal"  # Full access, high confidence
    MONITORING = "monitoring"  # Logging events, medium confidence
    RESTRICTED = "restricted"  # Limited access, low confidence
    LOCKDOWN = "lockdown"  # Screen locked, very low confidence


class DecisionEngine:
    """
    Decision engine for behavioral biometric authentication.

    Receives confidence scores from inference engine and makes
    authentication decisions (allow, restrict, lockdown).
    """

    def __init__(
        self,
        normal_threshold: float = 70.0,
        monitoring_threshold: float = 50.0,
        restricted_threshold: float = 35.0,
        lockdown_threshold: float = 20.0,
        confirmation_count: int = 3,
    ):
        """
        Initialize decision engine.

        Args:
            normal_threshold: Score above this = normal operation
            monitoring_threshold: Score above this = monitoring mode
            restricted_threshold: Score above this = restricted mode
            lockdown_threshold: Score below this = lockdown
            confirmation_count: Consecutive low scores before action
        """
        self.normal_threshold = normal_threshold
        self.monitoring_threshold = monitoring_threshold
        self.restricted_threshold = restricted_threshold
        self.lockdown_threshold = lockdown_threshold
        self.confirmation_count = confirmation_count

        # Current state
        self.current_state = AuthState.NORMAL
        self.previous_state = AuthState.NORMAL

        # Score history for confirmation
        self.score_history: deque = deque(maxlen=confirmation_count * 2)
        self.low_score_count = 0

        # Redis connection
        redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=redis_password if redis_password else None,
            decode_responses=True,
        )
        self.pubsub = self.redis_client.pubsub()

        # Database for audit logging
        try:
            self.db = get_database()
        except Exception:
            self.db = None
            logger.warning("Database not available for audit logging")

        # Developer mode
        self.dev_mode = get_developer_mode()

        # Running state
        self._running = False

        # Callbacks for state changes
        self._state_callbacks: List[Callable[[AuthState, AuthState, float], None]] = []

    def add_state_callback(
        self, callback: Callable[[AuthState, AuthState, float], None]
    ):
        """
        Add a callback for state changes.

        Args:
            callback: Function(old_state, new_state, score) to call on state change
        """
        self._state_callbacks.append(callback)

    def determine_state(self, score: float) -> AuthState:
        """
        Determine authentication state based on score.

        Args:
            score: Fused confidence score (0-100)

        Returns:
            Appropriate AuthState
        """
        if score >= self.normal_threshold:
            return AuthState.NORMAL
        elif score >= self.monitoring_threshold:
            return AuthState.MONITORING
        elif score >= self.restricted_threshold:
            return AuthState.RESTRICTED
        else:
            return AuthState.LOCKDOWN

    def process_score(self, score: float, dev_mode: bool = False) -> Dict[str, Any]:
        """
        Process a confidence score and make a decision.

        Args:
            score: Fused confidence score (0-100)
            dev_mode: Whether developer mode is active

        Returns:
            Decision result dictionary
        """
        # Store score in history
        self.score_history.append(score)

        # Check developer mode bypass
        if dev_mode or (self.dev_mode and self.dev_mode.is_active()):
            return {
                "action": "allow",
                "state": AuthState.NORMAL.value,
                "score": 100.0,
                "reason": "Developer mode active (BYPASS)",
                "dev_mode": True,
            }

        # Determine target state
        target_state = self.determine_state(score)

        # Track consecutive low scores
        if target_state in [AuthState.RESTRICTED, AuthState.LOCKDOWN]:
            self.low_score_count += 1
        else:
            self.low_score_count = 0

        # Only change state after confirmation
        should_change = False
        if target_state.value < self.current_state.value:
            # Degrading - require confirmation
            if self.low_score_count >= self.confirmation_count:
                should_change = True
        elif target_state.value > self.current_state.value:
            # Improving - change immediately
            should_change = True

        # Apply state change
        if should_change and target_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = target_state
            self._on_state_change(self.previous_state, self.current_state, score)

        # Determine action
        action = self._get_action_for_state(self.current_state)

        # Build result
        result = {
            "action": action,
            "state": self.current_state.value,
            "score": score,
            "reason": self._get_reason(self.current_state, score),
            "dev_mode": False,
            "low_score_count": self.low_score_count,
            "confirmation_needed": (
                self.confirmation_count - self.low_score_count
                if self.low_score_count < self.confirmation_count
                else 0
            ),
        }

        # Log to database
        self._log_decision(result)

        return result

    def _get_action_for_state(self, state: AuthState) -> str:
        """Get the action string for a state."""
        actions = {
            AuthState.NORMAL: "allow",
            AuthState.MONITORING: "allow_log",
            AuthState.RESTRICTED: "restrict",
            AuthState.LOCKDOWN: "lockdown",
        }
        return actions.get(state, "allow")

    def _get_reason(self, state: AuthState, score: float) -> str:
        """Get human-readable reason for the decision."""
        reasons = {
            AuthState.NORMAL: f"High confidence ({score:.1f}%) - normal operation",
            AuthState.MONITORING: f"Medium confidence ({score:.1f}%) - monitoring active",
            AuthState.RESTRICTED: f"Low confidence ({score:.1f}%) - restricted access",
            AuthState.LOCKDOWN: f"Very low confidence ({score:.1f}%) - lockdown initiated",
        }
        return reasons.get(state, f"Score: {score:.1f}%")

    def _on_state_change(
        self, old_state: AuthState, new_state: AuthState, score: float
    ):
        """Handle state change."""
        logger.info(
            f"State change: {old_state.value} -> {new_state.value} (score: {score:.1f})"
        )

        # Notify callbacks (locking engine subscribes via Redis, not callbacks)
        for callback in self._state_callbacks:
            try:
                callback(old_state, new_state, score)
            except Exception as e:
                logger.error(f"State callback error: {e}")

        # Publish state change event (locking engine listens to this)
        self._publish_state_change(old_state, new_state, score)

    def _publish_state_change(
        self, old_state: AuthState, new_state: AuthState, score: float
    ):
        """Publish state change to Redis."""
        event = {
            "old_state": old_state.value,
            "new_state": new_state.value,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.redis_client.publish("seclyzer:state_change", json.dumps(event))

    def _log_decision(self, decision: Dict[str, Any]):
        """Log decision to database."""
        if self.db is None:
            return

        try:
            self.db.log_event(
                event_type="DECISION",
                confidence_score=decision["score"],
                state=decision["state"],
                details=json.dumps(
                    {
                        "action": decision["action"],
                        "reason": decision["reason"],
                        "dev_mode": decision["dev_mode"],
                    }
                ),
            )
        except Exception as e:
            logger.debug(f"Failed to log decision: {e}")

    def process_scores(self):
        """Main loop to process incoming scores from inference engine."""
        logger.info("Decision Engine starting...")

        # Subscribe to fused score channel
        self.pubsub.subscribe("seclyzer:scores:fused")

        self._running = True

        logger.info("Listening for scores...")
        print("[Decision Engine] Ready - monitoring confidence scores")

        for message in self.pubsub.listen():
            if not self._running:
                break

            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                score = data.get("fused_score", 50.0)
                dev_mode = data.get("dev_mode", False)

                # Process the score
                decision = self.process_score(score, dev_mode)

                # Publish decision
                self.redis_client.publish(
                    "seclyzer:decisions",
                    json.dumps(decision),
                )

                # Log to console (for debugging)
                state_emoji = {
                    "normal": "✅",
                    "monitoring": "👁️",
                    "restricted": "⚠️",
                    "lockdown": "🔒",
                }
                emoji = state_emoji.get(decision["state"], "❓")
                print(
                    f"[Decision Engine] {emoji} {decision['state'].upper()} | "
                    f"Score: {score:.1f}% | Action: {decision['action']}"
                )

            except json.JSONDecodeError:
                logger.warning("Invalid JSON in score message")
            except Exception as e:
                logger.error(f"Error processing score: {e}")

    def stop(self):
        """Stop the decision engine."""
        self._running = False
        self.pubsub.unsubscribe()
        logger.info("Decision Engine stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the decision engine."""
        recent_scores = list(self.score_history)
        avg_score = sum(recent_scores) / len(recent_scores) if recent_scores else 50.0

        return {
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value,
            "recent_scores": recent_scores,
            "average_score": avg_score,
            "low_score_count": self.low_score_count,
            "thresholds": {
                "normal": self.normal_threshold,
                "monitoring": self.monitoring_threshold,
                "restricted": self.restricted_threshold,
                "lockdown": self.lockdown_threshold,
            },
            "confirmation_count": self.confirmation_count,
        }

    def force_state(self, state: AuthState, reason: str = "Manual override"):
        """
        Force a specific state (for testing/admin purposes).

        Args:
            state: State to force
            reason: Reason for the override
        """
        old_state = self.current_state
        self.current_state = state
        self.previous_state = old_state

        logger.warning(f"State forced: {old_state.value} -> {state.value} ({reason})")

        # Log the override
        if self.db:
            self.db.log_event(
                event_type="STATE_OVERRIDE",
                confidence_score=None,
                state=state.value,
                details=reason,
            )


# Global instance
_decision_engine: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """Get or create the global decision engine instance."""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine


if __name__ == "__main__":
    engine = DecisionEngine()
    try:
        engine.process_scores()
    except KeyboardInterrupt:
        engine.stop()
