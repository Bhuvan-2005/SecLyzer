"""
Tests for locking engine
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from processing.actions.locking_engine import LockingEngine


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = MagicMock()
    redis_mock.pubsub.return_value = MagicMock()
    return redis_mock


@pytest.fixture
def engine(mock_redis):
    """Create locking engine with mocked dependencies"""
    with patch(
        "processing.actions.locking_engine.redis.Redis", return_value=mock_redis
    ):
        with patch(
            "processing.actions.locking_engine.get_developer_mode", return_value=None
        ):
            engine = LockingEngine(
                enable_lock=True,
                enable_notifications=True,
                lock_on_restricted=False,
                lock_on_lockdown=True,
            )
            engine.redis_client = mock_redis
            return engine


class TestLockingEngineInitialization:
    """Test locking engine initialization"""

    def test_initialization(self, engine):
        """Test basic initialization"""
        assert engine.enable_lock is True
        assert engine.enable_notifications is True
        assert engine.lock_on_restricted is False
        assert engine.lock_on_lockdown is True
        assert engine._enabled is True

    def test_lock_command_detected(self, engine):
        """Test lock command is detected"""
        assert isinstance(engine._lock_command, list)
        assert len(engine._lock_command) > 0


class TestEnableDisable:
    """Test enable/disable functionality"""

    def test_enable(self, engine):
        """Test enabling locking"""
        engine._enabled = False
        engine.enable()
        assert engine._enabled is True

    def test_disable(self, engine):
        """Test disabling locking"""
        engine._enabled = True
        engine.disable()
        assert engine._enabled is False

    def test_is_enabled(self, engine):
        """Test is_enabled check"""
        engine._enabled = True
        assert engine.is_enabled() is True

        engine._enabled = False
        assert engine.is_enabled() is False


class TestLockScreen:
    """Test screen locking"""

    def test_lock_screen_when_disabled(self, engine):
        """Test lock screen skipped when disabled"""
        engine._enabled = False
        result = engine.lock_screen()
        assert result is False

    def test_lock_screen_when_lock_disabled(self, engine):
        """Test lock screen skipped when enable_lock is False"""
        engine.enable_lock = False
        result = engine.lock_screen()
        assert result is False

    def test_lock_screen_dev_mode(self, engine):
        """Test lock screen skipped in dev mode"""
        dev_mode_mock = MagicMock()
        dev_mode_mock.is_active.return_value = True
        engine.dev_mode = dev_mode_mock

        result = engine.lock_screen()
        assert result is False

    def test_lock_screen_success(self, engine):
        """Test successful screen lock"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = engine.lock_screen()
            assert result is True
            mock_run.assert_called_once()

    def test_lock_screen_failure(self, engine):
        """Test screen lock failure handling"""
        with patch("subprocess.run", side_effect=Exception("Lock failed")):
            result = engine.lock_screen()
            assert result is False


class TestNotifications:
    """Test notification sending"""

    def test_notification_when_disabled(self, engine):
        """Test notification skipped when disabled"""
        engine._enabled = False
        result = engine.send_notification("Test", "Message")
        assert result is False

    def test_notification_when_notifications_disabled(self, engine):
        """Test notification skipped when enable_notifications is False"""
        engine.enable_notifications = False
        result = engine.send_notification("Test", "Message")
        assert result is False

    def test_notification_success(self, engine):
        """Test successful notification"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = engine.send_notification("Test", "Message")
            assert result is True

    def test_notification_failure(self, engine):
        """Test notification failure handling"""
        with patch("subprocess.run", side_effect=Exception("No notify-send")):
            result = engine.send_notification("Test", "Message")
            assert result is False


class TestStateChangeHandling:
    """Test state change handling"""

    def test_handle_lockdown(self, engine):
        """Test handling lockdown state"""
        with patch.object(engine, "lock_screen") as mock_lock:
            with patch.object(engine, "send_notification") as mock_notify:
                engine.handle_state_change("normal", "lockdown", 15.0)

                mock_lock.assert_called_once()
                mock_notify.assert_called_once()

    def test_handle_restricted_no_lock(self, engine):
        """Test handling restricted state without locking"""
        engine.lock_on_restricted = False

        with patch.object(engine, "lock_screen") as mock_lock:
            with patch.object(engine, "send_notification") as mock_notify:
                engine.handle_state_change("normal", "restricted", 30.0)

                mock_lock.assert_not_called()
                mock_notify.assert_called_once()

    def test_handle_restricted_with_lock(self, engine):
        """Test handling restricted state with locking enabled"""
        engine.lock_on_restricted = True

        with patch.object(engine, "lock_screen") as mock_lock:
            with patch.object(engine, "send_notification") as mock_notify:
                engine.handle_state_change("normal", "restricted", 30.0)

                mock_lock.assert_called_once()
                mock_notify.assert_called_once()

    def test_handle_monitoring(self, engine):
        """Test handling monitoring state"""
        with patch.object(engine, "send_notification") as mock_notify:
            engine.handle_state_change("normal", "monitoring", 55.0)
            mock_notify.assert_called_once()

    def test_handle_restored(self, engine):
        """Test handling restoration to normal"""
        with patch.object(engine, "send_notification") as mock_notify:
            engine.handle_state_change("restricted", "normal", 85.0)
            mock_notify.assert_called_once()

    def test_handle_disabled(self, engine):
        """Test state change handling when disabled"""
        engine._enabled = False

        with patch.object(engine, "lock_screen") as mock_lock:
            with patch.object(engine, "send_notification") as mock_notify:
                engine.handle_state_change("normal", "lockdown", 15.0)

                mock_lock.assert_not_called()
                mock_notify.assert_not_called()

    def test_handle_dev_mode(self, engine):
        """Test state change handling in dev mode"""
        dev_mode_mock = MagicMock()
        dev_mode_mock.is_active.return_value = True
        engine.dev_mode = dev_mode_mock

        with patch.object(engine, "lock_screen") as mock_lock:
            with patch.object(engine, "send_notification") as mock_notify:
                engine.handle_state_change("normal", "lockdown", 15.0)

                mock_lock.assert_not_called()
                mock_notify.assert_not_called()


class TestActionCallbacks:
    """Test action callbacks"""

    def test_add_callback(self, engine):
        """Test adding action callback"""
        callback = MagicMock()
        engine.add_action_callback(callback)
        assert callback in engine._action_callbacks

    def test_callback_called_on_lock(self, engine):
        """Test callback called on lock action"""
        callback = MagicMock()
        engine.add_action_callback(callback)

        with patch("subprocess.run"):
            engine.lock_screen()

        callback.assert_called()


class TestStatus:
    """Test status reporting"""

    def test_get_status(self, engine):
        """Test status retrieval"""
        status = engine.get_status()

        assert "enabled" in status
        assert "running" in status
        assert "enable_lock" in status
        assert "enable_notifications" in status
        assert "lock_on_restricted" in status
        assert "lock_on_lockdown" in status
        assert "lock_command" in status


class TestEngineControl:
    """Test engine control methods"""

    def test_stop(self, engine):
        """Test stopping the engine"""
        engine._running = True
        engine.stop()

        assert engine._running is False
        engine.pubsub.unsubscribe.assert_called_once()
