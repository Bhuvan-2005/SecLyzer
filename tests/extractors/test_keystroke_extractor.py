import json
from collections import deque
from datetime import datetime

import polars as pl

from processing.extractors.keystroke_extractor import KeystrokeExtractor


def _make_df_for_dwell():
    events = []
    t0 = 0.0
    for i in range(3):
        t_press = t0 + i * 0.2
        t_release = t_press + 0.1
        events.append(
            {"timestamp": t_press, "key": "A", "event_type": "press", "dev_mode": False}
        )
        events.append(
            {
                "timestamp": t_release,
                "key": "A",
                "event_type": "release",
                "dev_mode": False,
            }
        )
    return pl.DataFrame(events)


def test_calculate_dwell_times():
    df = _make_df_for_dwell()
    dwell = KeystrokeExtractor._calculate_dwell_times(object(), df)
    assert dwell
    assert all(0 < d < 1000 for d in dwell)


def test_extract_features_basic():
    extractor = KeystrokeExtractor.__new__(KeystrokeExtractor)
    extractor.window_seconds = 60
    extractor.update_interval = 5
    extractor.events = deque()
    extractor.dev_mode = None
    now = datetime.now().timestamp()
    for i in range(10):
        t_press = now - 1 + i * 0.01
        t_release = t_press + 0.005
        extractor.events.append(
            {"timestamp": t_press, "key": "A", "event_type": "press", "dev_mode": False}
        )
        extractor.events.append(
            {
                "timestamp": t_release,
                "key": "A",
                "event_type": "release",
                "dev_mode": False,
            }
        )
    features = KeystrokeExtractor.extract_features(extractor)
    assert features is not None
    assert "dwell_mean" in features
    assert "flight_mean" in features
    assert features["total_keys"] == len(extractor.events) // 2


def test_save_features_writes_to_db_and_redis():
    class DummyDB:
        def __init__(self):
            self.calls = []

        def write_keystroke_features(self, features, **kwargs):
            self.calls.append(features.copy())

    class DummyRedis:
        def __init__(self):
            self.published = []

        def publish(self, channel, payload):
            self.published.append((channel, payload))

    extractor = KeystrokeExtractor.__new__(KeystrokeExtractor)
    extractor.db = DummyDB()
    extractor.redis_client = DummyRedis()
    features = {"dev_mode": False}
    KeystrokeExtractor._save_features(extractor, features)
    assert extractor.db.calls
    assert extractor.redis_client.published
    channel, payload = extractor.redis_client.published[0]
    assert channel == "seclyzer:features:keystroke"
    data = json.loads(payload)
    assert data["type"] == "keystroke"
