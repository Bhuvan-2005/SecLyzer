import json

from common.logger import get_logger


def test_correlation_logger_emits_json(capsys):
    logger = get_logger("test_logger")
    logger.info("hello", user="tester")
    captured = capsys.readouterr()
    line = captured.out.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["message"] == "hello"
    assert data["logger"] == "test_logger"
    assert "correlation_id" in data
    assert data["extra"]["user"] == "tester"
