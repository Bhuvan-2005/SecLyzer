#!/usr/bin/env python3
"""
Locking Engine for SecLyzer
Handles system actions (screen lock, notifications) based on authentication state.
Separate from Decision Engine to allow independent operation.
"""

import json
import os
import subprocess
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import redis

from common.logger import get_logger
from common.developer_mode import get_developer_mode

logger = get_logger(__name__)


class LockingEngine:
    """
    Locking engine for system actions.
    
    Listens to decision engine state changes and executes
    appropriate system actions (lock screen, notifications).
    Can be enabled/disabled independently of decision engine.
    """

    def __init__(
        self,
        enable_lock: bool = True,
        enable_notifications: bool = True,
        lock_on_restricted: bool = False,
        lock_on_lockdown: bool = True,
    ):
        """
        Initialize locking engine.

        Args:
            enable_lock: Whether to enable screen locking
            enable_notifications: Whether to enable desktop notifications
            lock_on_restricted: Lock screen on RESTRICTED state (default: False)
            lock_on_lockdown: Lock screen on LOCKDOWN state (default: True)
        """
        self.enable_lock = enable_lock
        self.enable_notifications = enable_notifications
        self.lock_on_restricted = lock_on_restricted
        self.lock_on_lockdown = lock_on_lockdown

        # Redis connection
        redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=redis_password if redis_password else None,
            decode_responses=True,
        )
        self.pubsub = self.redis_client.pubsub()

        # Developer mode
        self.dev_mode = get_developer_mode()

        # Running state
        self._running = False
        self._enabled = True

        # Lock screen command (platform-specific)
        self._lock_command = self._detect_lock_command()

        # Action callbacks
        self._action_callbacks: List[Callable[[str, Dict], None]] = []

    def _detect_lock_command(self) -> List[str]:
        """Detect the appropriate screen lock command for the system."""
        lock_commands = [
            ["loginctl", "lock-session"],  # systemd
            ["gnome-screensaver-command", "-l"],  # GNOME
            ["xdg-screensaver", "lock"],  # XDG
            ["dm-tool", "lock"],  # LightDM
            ["xscreensaver-command", "-lock"],  # XScreenSaver
        ]

        for cmd in lock_commands:
            try:
                result = subprocess.run(
                    ["which", cmd[0]],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return cmd
            except Exception:
                continue

        return ["loginctl", "lock-session"]

    def add_action_callback(self, callback: Callable[[str, Dict], None]):
        """Add a callback for actions."""
        self._action_callbacks.append(callback)

    def enable(self):
        """Enable locking actions."""
        self._enabled = True
        logger.info("Locking Engine enabled")

    def disable(self):
        """Disable locking actions (decision engine continues)."""
        self._enabled = False
        logger.info("Locking Engine disabled - actions will be skipped")

    def is_enabled(self) -> bool:
        """Check if locking is enabled."""
        return self._enabled

    def lock_screen(self) -> bool:
        """
        Lock the screen.
        
        Returns:
            True if lock was successful
        """
        if not self.enable_lock or not self._enabled:
            logger.debug("Screen lock skipped (disabled)")
            return False

        # Check developer mode
        if self.dev_mode and self.dev_mode.is_active():
            logger.info("Screen lock skipped (developer mode)")
            return False

        logger.warning("Executing screen lock")

        try:
            subprocess.run(
                self._lock_command,
                capture_output=True,
                timeout=5,
            )
            logger.info("Screen locked successfully")
            self._notify_callbacks("lock", {"success": True})
            return True
        except subprocess.TimeoutExpired:
            logger.error("Lock command timed out")
        except Exception as e:
            logger.error(f"Failed to lock screen: {e}")

        self._notify_callbacks("lock", {"success": False})
        return False

    def send_notification(
        self, 
        title: str, 
        message: str, 
        urgency: str = "normal",
        icon: str = None
    ) -> bool:
        """
        Send desktop notification.
        
        Args:
            title: Notification title
            message: Notification body
            urgency: low, normal, or critical
            icon: Icon name (optional)
            
        Returns:
            True if notification was sent
        """
        if not self.enable_notifications or not self._enabled:
            logger.debug("Notification skipped (disabled)")
            return False

        if icon is None:
            icon = "dialog-warning" if urgency == "critical" else "dialog-information"

        try:
            subprocess.run(
                [
                    "notify-send",
                    title,
                    message,
                    f"--urgency={urgency}",
                    f"--icon={icon}",
                ],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as e:
            logger.debug(f"Notification failed: {e}")
            return False

    def handle_state_change(self, old_state: str, new_state: str, score: float):
        """
        Handle a state change from decision engine.
        
        Args:
            old_state: Previous authentication state
            new_state: New authentication state
            score: Current confidence score
        """
        if not self._enabled:
            logger.debug(f"State change {old_state} -> {new_state} (actions disabled)")
            return

        # Check developer mode
        if self.dev_mode and self.dev_mode.is_active():
            logger.debug(f"State change {old_state} -> {new_state} (dev mode - no action)")
            return

        logger.info(f"Handling state change: {old_state} -> {new_state}")

        if new_state == "lockdown":
            self._handle_lockdown(score)
        elif new_state == "restricted":
            self._handle_restricted(score)
        elif new_state == "monitoring":
            self._handle_monitoring(score)
        elif new_state == "normal" and old_state != "normal":
            self._handle_restored(score)

    def _handle_lockdown(self, score: float):
        """Handle LOCKDOWN state."""
        if self.lock_on_lockdown:
            self.lock_screen()

        self.send_notification(
            "SecLyzer Security Alert",
            f"Unusual behavior detected (confidence: {score:.0f}%). Screen locked for security.",
            urgency="critical",
        )

    def _handle_restricted(self, score: float):
        """Handle RESTRICTED state."""
        if self.lock_on_restricted:
            self.lock_screen()

        self.send_notification(
            "SecLyzer Warning",
            f"Unusual behavior detected (confidence: {score:.0f}%). Some features may be restricted.",
            urgency="normal",
        )

    def _handle_monitoring(self, score: float):
        """Handle MONITORING state."""
        self.send_notification(
            "SecLyzer Notice",
            f"Behavior confidence dropped to {score:.0f}%. Monitoring active.",
            urgency="low",
        )

    def _handle_restored(self, score: float):
        """Handle restoration to NORMAL state."""
        self.send_notification(
            "SecLyzer",
            f"Normal behavior confirmed (confidence: {score:.0f}%). Full access restored.",
            urgency="low",
            icon="dialog-information",
        )

    def _notify_callbacks(self, action: str, data: Dict):
        """Notify action callbacks."""
        for callback in self._action_callbacks:
            try:
                callback(action, data)
            except Exception as e:
                logger.error(f"Action callback error: {e}")

    def run(self):
        """Main loop to listen for state changes."""
        logger.info("Locking Engine starting...")

        # Subscribe to state change channel
        self.pubsub.subscribe("seclyzer:state_change")

        self._running = True

        logger.info("Listening for state changes...")
        status = "ENABLED" if self._enabled else "DISABLED"
        print(f"[Locking Engine] Ready - {status}")

        for message in self.pubsub.listen():
            if not self._running:
                break

            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                old_state = data.get("old_state", "normal")
                new_state = data.get("new_state", "normal")
                score = data.get("score", 50.0)

                self.handle_state_change(old_state, new_state, score)

            except json.JSONDecodeError:
                logger.warning("Invalid JSON in state change message")
            except Exception as e:
                logger.error(f"Error handling state change: {e}")

    def stop(self):
        """Stop the locking engine."""
        self._running = False
        self.pubsub.unsubscribe()
        logger.info("Locking Engine stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the locking engine."""
        return {
            "enabled": self._enabled,
            "running": self._running,
            "enable_lock": self.enable_lock,
            "enable_notifications": self.enable_notifications,
            "lock_on_restricted": self.lock_on_restricted,
            "lock_on_lockdown": self.lock_on_lockdown,
            "lock_command": self._lock_command,
        }


# Global instance
_locking_engine: Optional[LockingEngine] = None


def get_locking_engine() -> LockingEngine:
    """Get or create the global locking engine instance."""
    global _locking_engine
    if _locking_engine is None:
        _locking_engine = LockingEngine()
    return _locking_engine


if __name__ == "__main__":
    engine = LockingEngine()
    try:
        engine.run()
    except KeyboardInterrupt:
        engine.stop()
