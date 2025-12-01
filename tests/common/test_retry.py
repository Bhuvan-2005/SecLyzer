import pytest

from common.retry import retry_with_backoff


def test_retry_succeeds_after_failures():
    calls = {"count": 0}

    @retry_with_backoff(max_attempts=3, initial_delay=0.01)
    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("fail")
        return "ok"

    assert flaky() == "ok"
    assert calls["count"] == 3


def test_retry_raises_after_max_attempts():
    calls = {"count": 0}

    @retry_with_backoff(max_attempts=2, initial_delay=0.01)
    def always_fail():
        calls["count"] += 1
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        always_fail()
    assert calls["count"] == 2
