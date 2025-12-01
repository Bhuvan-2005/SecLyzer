from pathlib import Path

from storage.database import Database, get_database


def create_schema(db: Database):
    db.conn.executescript(
        """
        CREATE TABLE user_profile(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            training_status TEXT,
            last_updated TEXT
        );
        INSERT INTO user_profile(username, training_status, last_updated)
        VALUES ('default', 'idle', datetime('now'));
        CREATE TABLE models(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            model_type TEXT,
            version TEXT,
            accuracy REAL,
            model_path TEXT,
            trained_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE config(
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );
        CREATE TABLE audit_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            confidence_score REAL,
            state TEXT,
            details TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        """
    )
    db.conn.commit()


def test_user_profile_and_status(tmp_path):
    db_path = tmp_path / "db.sqlite"
    db = Database(str(db_path))
    try:
        create_schema(db)
        user = db.get_user("default")
        assert user is not None
        assert user["username"] == "default"
        db.update_user_status("default", "training")
        user2 = db.get_user("default")
        assert user2["training_status"] == "training"
    finally:
        db.close()


def test_model_metadata_roundtrip(tmp_path):
    db_path = tmp_path / "db.sqlite"
    db = Database(str(db_path))
    try:
        create_schema(db)
        model_id = db.save_model_metadata(
            model_type="keystroke",
            version="1.0",
            accuracy=0.95,
            model_path="/tmp/model",
        )
        assert isinstance(model_id, int)
        latest = db.get_latest_model("keystroke")
        assert latest is not None
        assert latest["model_type"] == "keystroke"
        models = db.list_models()
        assert len(models) >= 1
    finally:
        db.close()


def test_config_and_audit_logging(tmp_path):
    db_path = tmp_path / "db.sqlite"
    db = Database(str(db_path))
    try:
        create_schema(db)
        db.set_config("threshold", {"value": 0.5})
        assert db.get_config("threshold") == {"value": 0.5}
        db.set_config("mode", "strict")
        assert db.get_config("mode") == "strict"
        db.log_event("TEST", confidence_score=0.9, state="OK", details="details")
        recent = db.get_recent_events(limit=1)
        assert recent and recent[0]["event_type"] == "TEST"
        by_type = db.get_events_by_type("TEST")
        assert any(ev["event_type"] == "TEST" for ev in by_type)
    finally:
        db.close()


def test_get_database_custom_path(tmp_path):
    db_path = tmp_path / "db.sqlite"
    db = get_database(str(db_path))
    try:
        assert isinstance(db, Database)
        assert db.db_path == str(db_path)
    finally:
        db.close()
