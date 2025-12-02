#!/usr/bin/env python3
"""
SecLyzer Daemon
Main daemon that runs inference, decision, and locking engines.
Each engine can be enabled/disabled independently.
"""

import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.logger import get_logger
from common.developer_mode import get_developer_mode
from processing.inference.inference_engine import InferenceEngine
from processing.decision.decision_engine import DecisionEngine
from processing.actions.locking_engine import LockingEngine

logger = get_logger(__name__)


class SecLyzerDaemon:
    """Main SecLyzer daemon that coordinates inference, decision, and locking engines."""

    def __init__(
        self,
        models_dir: str = "data/models",
        user_id: str = "default",
        enable_locking: bool = True,
    ):
        """
        Initialize the daemon.

        Args:
            models_dir: Directory containing trained models
            user_id: User identifier
            enable_locking: Whether to enable the locking engine
        """
        self.models_dir = models_dir
        self.user_id = user_id
        self.enable_locking = enable_locking

        self.inference_engine: InferenceEngine = None
        self.decision_engine: DecisionEngine = None
        self.locking_engine: LockingEngine = None

        self._running = False
        self._threads: list = []

        # Developer mode
        self.dev_mode = get_developer_mode()

    def start(self):
        """Start the daemon."""
        print("╔════════════════════════════════════════════════════════╗")
        print("║           SecLyzer Authentication Daemon               ║")
        print("║                                                        ║")
        print("║  Behavioral Biometric Continuous Authentication       ║")
        print("╚════════════════════════════════════════════════════════╝")
        print()

        logger.info("SecLyzer Daemon starting...")

        # Check developer mode
        if self.dev_mode and self.dev_mode.is_active():
            print("⚠️  DEVELOPER MODE ACTIVE - Authentication bypassed")
            logger.warning("Developer mode is active")

        # Initialize engines
        print("Loading models...")
        self.inference_engine = InferenceEngine(
            models_dir=self.models_dir,
            user_id=self.user_id,
        )

        print("Initializing decision engine...")
        self.decision_engine = DecisionEngine()

        # Initialize locking engine (optional)
        if self.enable_locking:
            print("Initializing locking engine...")
            self.locking_engine = LockingEngine()

        # Start threads
        self._running = True

        inference_thread = threading.Thread(
            target=self._run_inference,
            name="InferenceEngine",
            daemon=True,
        )
        inference_thread.start()
        self._threads.append(inference_thread)

        decision_thread = threading.Thread(
            target=self._run_decision,
            name="DecisionEngine",
            daemon=True,
        )
        decision_thread.start()
        self._threads.append(decision_thread)

        # Start locking engine if enabled
        if self.locking_engine:
            locking_thread = threading.Thread(
                target=self._run_locking,
                name="LockingEngine",
                daemon=True,
            )
            locking_thread.start()
            self._threads.append(locking_thread)

        print()
        print("✓ SecLyzer Daemon started")
        print("  - Inference Engine: Running")
        print("  - Decision Engine: Running")
        locking_status = "Running" if self.enable_locking else "Disabled"
        print(f"  - Locking Engine: {locking_status}")
        print()
        print("Press Ctrl+C to stop")
        print("-" * 60)

        logger.info("SecLyzer Daemon started successfully")

    def _run_inference(self):
        """Run inference engine in thread."""
        try:
            self.inference_engine.process_features()
        except Exception as e:
            logger.error(f"Inference engine error: {e}")

    def _run_decision(self):
        """Run decision engine in thread."""
        try:
            self.decision_engine.process_scores()
        except Exception as e:
            logger.error(f"Decision engine error: {e}")

    def _run_locking(self):
        """Run locking engine in thread."""
        try:
            self.locking_engine.run()
        except Exception as e:
            logger.error(f"Locking engine error: {e}")

    def stop(self):
        """Stop the daemon."""
        print()
        print("Stopping SecLyzer Daemon...")
        logger.info("SecLyzer Daemon stopping...")

        self._running = False

        if self.inference_engine:
            self.inference_engine.stop()

        if self.decision_engine:
            self.decision_engine.stop()

        if self.locking_engine:
            self.locking_engine.stop()

        # Wait for threads
        for thread in self._threads:
            thread.join(timeout=5)

        print("✓ SecLyzer Daemon stopped")
        logger.info("SecLyzer Daemon stopped")

    def reload_models(self):
        """Reload models without restarting."""
        if self.inference_engine:
            print("Reloading models...")
            self.inference_engine.reload_models()
            print("✓ Models reloaded")

    def enable_locking_engine(self):
        """Enable the locking engine."""
        if self.locking_engine:
            self.locking_engine.enable()
            print("✓ Locking engine enabled")

    def disable_locking_engine(self):
        """Disable the locking engine (decision engine continues)."""
        if self.locking_engine:
            self.locking_engine.disable()
            print("✓ Locking engine disabled (scores still calculated)")

    def get_status(self) -> dict:
        """Get daemon status."""
        status = {
            "running": self._running,
            "dev_mode": self.dev_mode.is_active() if self.dev_mode else False,
            "inference_engine": self.inference_engine is not None,
            "decision_engine": self.decision_engine is not None,
            "locking_engine": self.locking_engine is not None,
        }

        if self.decision_engine:
            status["decision_status"] = self.decision_engine.get_status()

        if self.locking_engine:
            status["locking_status"] = self.locking_engine.get_status()

        return status


def main():
    parser = argparse.ArgumentParser(
        description="SecLyzer Authentication Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--models-dir",
        default="data/models",
        help="Directory containing trained models (default: data/models)",
    )
    parser.add_argument(
        "--user",
        default="default",
        help="User ID (default: default)",
    )
    parser.add_argument(
        "--no-locking",
        action="store_true",
        help="Disable locking engine (scores only, no system actions)",
    )

    args = parser.parse_args()

    # Create daemon
    daemon = SecLyzerDaemon(
        models_dir=args.models_dir,
        user_id=args.user,
        enable_locking=not args.no_locking,
    )

    # Handle signals
    def signal_handler(signum, frame):
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start daemon
    daemon.start()

    # Keep main thread alive
    try:
        while daemon._running:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()


if __name__ == "__main__":
    main()
