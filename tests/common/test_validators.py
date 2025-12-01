from datetime import datetime, timedelta

import pytest

from common.validators import AppEvent, KeystrokeEvent, validate_event


def _near_now_us(offset_sec: int = 0) -> int:
    return int((datetime.now() + timedelta(seconds=offset_sec)).timestamp() * 1_000_000)


def test_keystroke_event_valid_timestamp():
    now_us = _near_now_us()
    ev = KeystrokeEvent(event="press", key="A", ts=now_us)
    assert ev.key == "A"


def test_keystroke_event_invalid_timestamp_raises():
    far_future = _near_now_us(offset_sec=7200)
    with pytest.raises(ValueError):
        KeystrokeEvent(event="press", key="A", ts=far_future)


def test_app_event_sanitizes_name():
    now_us = _near_now_us()
    ev = AppEvent(app_name="evil</script>", ts=now_us)
    assert "<" not in ev.app_name
    assert ">" not in ev.app_name
    assert ev.app_name


def test_validate_event_dispatches_and_unknown_type():
    now_us = _near_now_us()
    model = validate_event("keystroke", {"event": "press", "key": "A", "ts": now_us})
    assert isinstance(model, KeystrokeEvent)
    assert model.key == "A"
    with pytest.raises(ValueError):
        validate_event("unknown", {})
