import json
from collections import deque
from datetime import datetime

from processing.extractors.mouse_extractor import MouseExtractor


def test_extract_features_basic():
    extractor = MouseExtractor.__new__(MouseExtractor)
    extractor.window_seconds = 60
    extractor.update_interval = 5
    extractor.events = deque()
    extractor.dev_mode = None
    now = datetime.now().timestamp()
    for i in range(60):
        extractor.events.append(
            {
                "timestamp": now - 1 + i * 0.01,
                "x": i,
                "y": i,
                "event_type": "move",
                "button": None,
                "scroll_delta": None,
                "dev_mode": False,
            }
        )
    for i in range(3):
        t = now - 0.5 + i * 0.1
        extractor.events.append(
            {
                "timestamp": t,
                "x": None,
                "y": None,
                "event_type": "press",
                "button": "Left",
                "scroll_delta": None,
                "dev_mode": False,
            }
        )
        extractor.events.append(
            {
                "timestamp": t + 0.05,
                "x": None,
                "y": None,
                "event_type": "release",
                "button": "Left",
                "scroll_delta": None,
                "dev_mode": False,
            }
        )
    for i in range(5):
        extractor.events.append(
            {
                "timestamp": now - 0.2 + i * 0.02,
                "x": None,
                "y": None,
                "event_type": "scroll",
                "button": None,
                "scroll_delta": 1,
                "dev_mode": False,
            }
        )
    features = MouseExtractor.extract_features(extractor)
    assert features is not None
    assert "move_0" in features
    assert "click_0" in features
    assert "scroll_0" in features


def test_save_features_writes_to_db_and_redis():
    class DummyDB:
        def __init__(self):
            self.calls = []

        def write_mouse_features(self, features, **kwargs):
            self.calls.append(features.copy())

    class DummyRedis:
        def __init__(self):
            self.published = []

        def publish(self, channel, payload):
            self.published.append((channel, payload))

    extractor = MouseExtractor.__new__(MouseExtractor)
    extractor.db = DummyDB()
    extractor.redis_client = DummyRedis()
    features = {"dev_mode": False}
    MouseExtractor._save_features(extractor, features)
    assert extractor.db.calls
    assert extractor.redis_client.published
    channel, payload = extractor.redis_client.published[0]
    assert channel == "seclyzer:features:mouse"
    data = json.loads(payload)
    assert data["type"] == "mouse"
