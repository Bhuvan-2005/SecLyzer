from pathlib import Path

from common.developer_mode import DeveloperMode


def _write_config(path: Path, magic_file_path: str):
    import yaml

    config = {
        "enabled": True,
        "magic_file": {"enabled": True, "path": magic_file_path},
        "env_var": {"enabled": True, "name": "SECLYZER_DEV_MODE"},
        "security": {
            "auto_disable_hours": 0,
            "audit_file": str(path.parent / "dev_mode.log"),
            "show_warning": False,
        },
    }
    path.write_text(yaml.safe_dump(config))


def test_magic_file_activation(tmp_path, monkeypatch):
    config_path = tmp_path / "dev_mode.yml"
    magic_file = tmp_path / ".dev_mode_magic"
    _write_config(config_path, str(magic_file))
    dm = DeveloperMode(config_path=str(config_path))
    assert not dm.is_active()
    magic_file.write_text("x")
    assert dm.is_active()
    meta = dm.get_metadata_tag()
    assert meta["dev_mode"] is True
    assert "dev_mode_method" in meta


def test_env_var_activation(tmp_path, monkeypatch):
    config_path = tmp_path / "dev_mode.yml"
    magic_file = tmp_path / ".dev_mode_magic"
    _write_config(config_path, str(magic_file))
    dm = DeveloperMode(config_path=str(config_path))
    monkeypatch.setenv("SECLYZER_DEV_MODE", "1")
    assert dm.is_active()
    assert not dm.should_include_in_training()
