from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from storage.timeseries import TimeSeriesDB


class DummyPoint:
    def __init__(self, measurement):
        self.measurement = measurement
        self.tags = {}
        self.fields = {}
        self._time = None

    def tag(self, key, value):
        self.tags[key] = value
        return self

    def field(self, key, value):
        self.fields[key] = value
        return self

    def time(self, timestamp, precision):
        self._time = (timestamp, precision)
        return self


def make_db(monkeypatch):
    import storage.timeseries as ts

    ts.Point = DummyPoint  # type: ignore
    db = TimeSeriesDB(
        url="http://localhost:8086",
        token="token",
        org="org",
        bucket="bucket",
    )
    db.write_api = MagicMock()
    db.query_api = MagicMock()
    db.client = MagicMock()
    return db


def test_write_keystroke_features_builds_point(monkeypatch):
    db = make_db(monkeypatch)
    features = {"a": 1.0, "b": 2, "ignored": "x"}
    now = datetime.now(timezone.utc)
    db.write_keystroke_features(features, user_id="u", device_id="dev", timestamp=now)
    db.write_api.write.assert_called_once()
    args, kwargs = db.write_api.write.call_args
    point = kwargs.get("record") or args[0]
    assert isinstance(point, DummyPoint)
    assert point.measurement == "keystroke_features"
    assert point.tags["user_id"] == "u"
    assert point.tags["device_id"] == "dev"
    assert "ignored" not in point.fields


def test_query_keystroke_features_uses_bucket_and_org(monkeypatch):
    db = make_db(monkeypatch)
    fake_record = SimpleNamespace(
        get_time=lambda: datetime.now(timezone.utc),
        get_field=lambda: "value",
        get_value=lambda: 1.0,
        values={"user_id": "u"},
    )
    fake_table = SimpleNamespace(records=[fake_record])
    db.query_api.query.return_value = [fake_table]
    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    end = datetime.now(timezone.utc)
    result = db.query_keystroke_features(start_time=start, end_time=end, user_id="u")
    db.query_api.query.assert_called_once()
    assert result and result[0]["value"] == 1.0


def test_delete_old_data_calls_delete_api(monkeypatch):
    db = make_db(monkeypatch)
    delete_api = MagicMock()
    db.client.delete_api.return_value = delete_api
    db.delete_old_data(older_than_days=1)
    delete_api.delete.assert_called_once()
    call_kwargs = delete_api.delete.call_args.kwargs
    assert call_kwargs["bucket"] == db.bucket
    assert call_kwargs["org"] == db.org
