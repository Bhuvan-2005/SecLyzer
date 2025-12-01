import json
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from processing.extractors import app_tracker as app_tracker_mod
from processing.extractors import keystroke_extractor, mouse_extractor


class DummyPubSub:
    def __init__(self, messages):
        self._messages = messages

    def listen(self):
        for m in self._messages:
            yield m


def _make_message(payload):
    return {"type": "message", "data": json.dumps(payload)}


def test_keystroke_process_events_triggers_save():
    extractor = keystroke_extractor.KeystrokeExtractor.__new__(
        keystroke_extractor.KeystrokeExtractor
    )
    extractor.window_seconds = 60
    extractor.update_interval = 0
    extractor.events = deque()
    extractor.last_update = datetime.now() - timedelta(seconds=10)
    extractor.dev_mode = None
    extractor.pubsub = DummyPubSub(
        [
            _make_message(
                {
                    "type": "keystroke",
                    "ts": int(datetime.now().timestamp() * 1_000_000),
                    "key": "A",
                    "event": "press",
                }
            ),
            _make_message(
                {
                    "type": "keystroke",
                    "ts": int(datetime.now().timestamp() * 1_000_000),
                    "key": "A",
                    "event": "release",
                }
            ),
        ]
    )
    extractor.redis_client = MagicMock()
    extractor.db = MagicMock()
    extractor.extract_features = MagicMock(return_value={"dummy": 1})
    extractor._save_features = MagicMock()
    keystroke_extractor.logger = MagicMock()
    extractor.process_events()
    extractor._save_features.assert_called()


def test_mouse_process_events_triggers_save():
    extractor = mouse_extractor.MouseExtractor.__new__(mouse_extractor.MouseExtractor)
    extractor.window_seconds = 60
    extractor.update_interval = 0
    extractor.events = deque()
    extractor.last_update = datetime.now() - timedelta(seconds=10)
    extractor.dev_mode = None
    extractor.pubsub = DummyPubSub(
        [
            _make_message(
                {
                    "type": "mouse",
                    "ts": int(datetime.now().timestamp() * 1_000_000),
                    "event": "move",
                    "x": 0,
                    "y": 0,
                }
            ),
            _make_message(
                {
                    "type": "mouse",
                    "ts": int(datetime.now().timestamp() * 1_000_000),
                    "event": "move",
                    "x": 1,
                    "y": 1,
                }
            ),
        ]
    )
    extractor.redis_client = MagicMock()
    extractor.db = MagicMock()
    extractor.extract_features = MagicMock(return_value={"dummy": 1})
    extractor._save_features = MagicMock()
    mouse_extractor.logger = MagicMock()
    extractor.process_events()
    extractor._save_features.assert_called()


def test_app_tracker_process_events_triggers_update_patterns():
    tracker = app_tracker_mod.AppTracker.__new__(app_tracker_mod.AppTracker)
    tracker.update_interval = 0
    tracker.transitions = {}
    tracker.app_durations = {}
    tracker.time_patterns = {}
    tracker.current_app = None
    tracker.current_app_start = None
    tracker.recent_events = deque(maxlen=1000)
    tracker.last_update = datetime.now() - timedelta(seconds=10)
    tracker.ts_db = MagicMock()
    tracker.redis_client = MagicMock()
    tracker.db = MagicMock()
    tracker._handle_app_switch = MagicMock()
    tracker._update_patterns = MagicMock()
    tracker.pubsub = DummyPubSub(
        [
            _make_message(
                {
                    "type": "app",
                    "ts": int(datetime.now().timestamp() * 1_000_000),
                    "app_name": "test_app",
                }
            ),
        ]
    )
    app_tracker_mod.logger = MagicMock()
    tracker.process_events()
    tracker._handle_app_switch.assert_called()
