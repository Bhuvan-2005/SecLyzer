import subprocess
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_dev_help_smoke():
    root = project_root()
    result = subprocess.run(
        ["./scripts/dev", "help"], cwd=root, capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "SecLyzer Developer Console" in result.stdout


def test_seclyzer_help_smoke():
    root = project_root()
    result = subprocess.run(
        ["./scripts/seclyzer", "help"], cwd=root, capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "SecLyzer Control Interface" in result.stdout
