import os
from pathlib import Path

import yaml

from common.config import get_config


def test_load_defaults_when_config_missing(tmp_path, monkeypatch):
    cfg = get_config()
    monkeypatch.delenv("SECLYZER_CONFIG", raising=False)
    missing = tmp_path / "nonexistent.yaml"
    cfg.load(config_path=str(missing))
    assert cfg.get("user.id") == "primary"
    assert cfg.get("databases.sqlite.path").endswith("seclyzer.db")
    redis_conf = cfg.get_redis_config()
    assert redis_conf["host"]
    assert isinstance(redis_conf["port"], int)


def test_load_from_yaml_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_data = {
        "user": {"id": "custom"},
        "databases": {"redis": {"host": "redis.local", "port": 6380}},
    }
    config_path.write_text(yaml.safe_dump(config_data))
    cfg = get_config()
    cfg.load(config_path=str(config_path))
    assert cfg.get("user.id") == "custom"
    assert cfg.get("databases.redis.host") == "redis.local"
    redis_conf = cfg.get_redis_config()
    assert redis_conf["host"] == "redis.local"
    assert redis_conf["port"] == 6380


def test_influx_config_env_overrides(tmp_path, monkeypatch):
    config_data = {
        "databases": {"influxdb": {"url": "http://local", "org": "o", "bucket": "b"}}
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data))
    cfg = get_config()
    cfg.load(config_path=str(config_path))
    monkeypatch.setenv("INFLUX_URL", "http://override")
    monkeypatch.setenv("INFLUX_ORG", "override_org")
    monkeypatch.setenv("INFLUX_BUCKET", "override_bucket")
    monkeypatch.setenv("INFLUX_TOKEN", "token")
    influx_conf = cfg.get_influx_config()
    assert influx_conf["url"] == "http://override"
    assert influx_conf["org"] == "override_org"
    assert influx_conf["bucket"] == "override_bucket"
    assert influx_conf["token"] == "token"
