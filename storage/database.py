"""
Database wrapper for SQLite
Handles metadata, models, configuration, and audit logs
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Register datetime adapters for Python 3.12+ compatibility
def adapt_datetime(dt):
    """Adapt datetime for SQLite storage"""
    return dt.isoformat() if dt else None


def convert_datetime(s):
    """Convert ISO format string back to datetime"""
    if s:
        # Handle timezone-aware and naive datetimes
        dt = datetime.fromisoformat(s.decode() if isinstance(s, bytes) else s)
        return dt
    return None


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)


class Database:
    def __init__(self, db_path: str = "/var/lib/seclyzer/databases/seclyzer.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = None
        self._connect()

    def _connect(self):
        """Establish database connection"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row  # Access by column name

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    # ===== User Profile =====

    def get_user(self, username: str = "default") -> Optional[Dict]:
        """Get user profile"""
        cursor = self.conn.execute(
            "SELECT * FROM user_profile WHERE username = ?", (username,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_user_status(self, username: str, status: str):
        """Update training status"""
        self.conn.execute(
            "UPDATE user_profile SET training_status = ?, last_updated = ? WHERE username = ?",
            (status, datetime.now(), username),
        )
        self.conn.commit()

    # ===== Models =====

    def save_model_metadata(
        self,
        model_type: str,
        version: str,
        accuracy: float,
        model_path: str,
        username: str = "default",
    ) -> int:
        """Save model metadata"""
        user = self.get_user(username)
        if not user:
            raise ValueError(f"User {username} not found")

        cursor = self.conn.execute(
            """INSERT INTO models (user_id, model_type, version, accuracy, model_path)
               VALUES (?, ?, ?, ?, ?)""",
            (user["user_id"], model_type, version, accuracy, model_path),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_latest_model(
        self, model_type: str, username: str = "default"
    ) -> Optional[Dict]:
        """Get most recent model of given type"""
        user = self.get_user(username)
        if not user:
            return None

        cursor = self.conn.execute(
            """SELECT * FROM models 
               WHERE user_id = ? AND model_type = ?
               ORDER BY trained_at DESC LIMIT 1""",
            (user["user_id"], model_type),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_models(self, username: str = "default") -> List[Dict]:
        """List all models for user"""
        user = self.get_user(username)
        if not user:
            return []

        cursor = self.conn.execute(
            "SELECT * FROM models WHERE user_id = ? ORDER BY trained_at DESC",
            (user["user_id"],),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ===== Configuration =====

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        cursor = self.conn.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            # Try to parse as JSON, fallback to string
            try:
                return json.loads(row["value"])
            except (json.JSONDecodeError, TypeError, ValueError):
                return row["value"]
        return default

    def set_config(self, key: str, value: Any):
        """Set configuration value"""
        # Convert to JSON string
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        self.conn.execute(
            """INSERT OR REPLACE INTO config (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (key, value_str, datetime.now()),
        )
        self.conn.commit()

    # ===== Audit Log =====

    def log_event(
        self,
        event_type: str,
        confidence_score: Optional[float] = None,
        state: Optional[str] = None,
        details: Optional[str] = None,
    ):
        """Log system event"""
        self.conn.execute(
            """INSERT INTO audit_log (event_type, confidence_score, state, details)
               VALUES (?, ?, ?, ?)""",
            (event_type, confidence_score, state, details),
        )
        self.conn.commit()

    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries"""
        cursor = self.conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_events_by_type(self, event_type: str, limit: int = 100) -> List[Dict]:
        """Get events of specific type"""
        cursor = self.conn.execute(
            """SELECT * FROM audit_log 
               WHERE event_type = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (event_type, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ===== Utility =====

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute custom query"""
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()


# Convenience function
def get_database(db_path: str = None) -> Database:
    """Get database instance"""
    if db_path is None:
        # Try default locations
        home = Path.home()
        for path in [
            "/var/lib/seclyzer/databases/seclyzer.db",
            str(home / ".seclyzer/databases/seclyzer.db"),
            str(Path(__file__).parent.parent / "data/databases/seclyzer.db"),
        ]:
            if Path(path).exists() or Path(path).parent.exists():
                db_path = path
                break

    return Database(db_path)
