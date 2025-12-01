import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from processing.extractors.app_tracker import AppTracker


def test_handle_app_switch_updates_transitions_and_patterns():
    class DummyTS:
        def __init__(self):
            self.calls = []

        def write_app_transition(self, **kwargs):
            self.calls.append(kwargs)

    class DummyRedis:
        def __init__(self):
            self.published = []

        def publish(self, channel, payload):
            self.published.append((channel, payload))

    tracker = AppTracker.__new__(AppTracker)
    tracker.update_interval = 60
    tracker.transitions = defaultdict(int)
    tracker.app_durations = defaultdict(list)
    tracker.time_patterns = defaultdict(lambda: defaultdict(int))
    tracker.current_app = "old_app"
    tracker.current_app_start = datetime.now(timezone.utc) - timedelta(seconds=10)
    tracker.recent_events = deque(maxlen=1000)
    tracker.last_update = datetime.now(timezone.utc)
    tracker.ts_db = DummyTS()
    tracker.db = None
    tracker.dev_mode = None
    ts_micro = int(time.time() * 1_000_000)
    current_time = datetime.fromtimestamp(ts_micro / 1_000_000, tz=timezone.utc)
    event = {"app_name": "new_app", "ts": ts_micro}
    AppTracker._handle_app_switch(tracker, event)
    assert tracker.current_app == "new_app"
    assert tracker.transitions[("old_app", "new_app")] == 1
    assert tracker.app_durations["old_app"]
    assert tracker.ts_db.calls
    assert tracker.recent_events
    assert tracker.time_patterns["new_app"][current_time.hour] == 1


def test_update_patterns_saves_to_db():
    class DummyDB:
        def __init__(self):
            self.saved = None

        def set_config(self, key, value):
            self.saved = (key, value)

    tracker = AppTracker.__new__(AppTracker)
    tracker.transitions = defaultdict(int)
    tracker.transitions[("a", "b")] = 2
    tracker.app_durations = defaultdict(list)
    tracker.app_durations["a"].extend([1.0, 2.0])
    tracker.time_patterns = defaultdict(lambda: defaultdict(int))
    tracker.time_patterns["a"][10] = 3
    tracker.recent_events = deque([{"dev_mode": False}], maxlen=1000)
    tracker.db = DummyDB()
    AppTracker._update_patterns(tracker)
    key, value = tracker.db.saved
    assert key == "app_patterns"
    assert "transition_matrix" in value
    assert "time_preferences" in value
    assert "usage_stats" in value


def test_anomaly_score_between_zero_and_one():
    tracker = AppTracker.__new__(AppTracker)
    tracker.transitions = defaultdict(int)
    tracker.transitions[("a", "b")] = 1
    tracker.time_patterns = defaultdict(lambda: defaultdict(int))
    tracker.time_patterns["b"][datetime.now().hour] = 1
    score = AppTracker.calculate_anomaly_score(tracker, ["a", "b"])
    assert 0.0 <= score <= 1.0
