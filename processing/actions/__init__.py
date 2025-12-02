"""Actions module for SecLyzer - system actions like screen locking."""

from processing.actions.locking_engine import LockingEngine, get_locking_engine

__all__ = ["LockingEngine", "get_locking_engine"]
