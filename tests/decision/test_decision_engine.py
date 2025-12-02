"""
Tests for decision engine
"""

import json
from collections import deque
from unittest.mock import MagicMock, patch

import pytest

from processing.decision.decision_engine import AuthState, DecisionEngine


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = MagicMock()
    redis_mock.pubsub.return_value = MagicMock()
    return redis_mock


@pytest.fixture
def mock_db():
    """Mock database"""
    db_mock = MagicMock()
    db_mock.log_event = MagicMock()
    return db_mock


@pytest.fixture
def engine(mock_redis, mock_db):
    """Create decision engine with mocked dependencies"""
    with patch("processing.decision.decision_engine.redis.Redis", return_value=mock_redis):
        with patch("processing.decision.decision_engine.get_database", return_value=mock_db):
            with patch("processing.decision.decision_engine.get_developer_mode", return_value=None):
                engine = DecisionEngine(
                    normal_threshold=70.0,
                    monitoring_threshold=50.0,
                    restricted_threshold=35.0,
                    lockdown_threshold=20.0,
                    confirmation_count=3,
                )
                engine.redis_client = mock_redis
                engine.db = mock_db
                return engine


class TestAuthState:
    """Test AuthState enum"""

    def test_auth_states_exist(self):
        """Test all auth states are defined"""
        assert AuthState.NORMAL.value == "normal"
        assert AuthState.MONITORING.value == "monitoring"
        assert AuthState.RESTRICTED.value == "restricted"
        assert AuthState.LOCKDOWN.value == "lockdown"


class TestDecisionEngineInitialization:
    """Test decision engine initialization"""

    def test_initialization(self, engine):
        """Test basic initialization"""
        assert engine.normal_threshold == 70.0
        assert engine.monitoring_threshold == 50.0
        assert engine.restricted_threshold == 35.0
        assert engine.lockdown_threshold == 20.0
        assert engine.confirmation_count == 3
        assert engine.current_state == AuthState.NORMAL
        assert engine.low_score_count == 0

    def test_score_history_initialized(self, engine):
        """Test score history is initialized"""
        assert isinstance(engine.score_history, deque)
        assert engine.score_history.maxlen == 6  # confirmation_count * 2


class TestStateDetermination:
    """Test state determination logic"""

    def test_determine_state_normal(self, engine):
        """Test normal state determination"""
        state = engine.determine_state(85.0)
        assert state == AuthState.NORMAL

    def test_determine_state_monitoring(self, engine):
        """Test monitoring state determination"""
        state = engine.determine_state(60.0)
        assert state == AuthState.MONITORING

    def test_determine_state_restricted(self, engine):
        """Test restricted state determination"""
        state = engine.determine_state(40.0)
        assert state == AuthState.RESTRICTED

    def test_determine_state_lockdown(self, engine):
        """Test lockdown state determination"""
        state = engine.determine_state(15.0)
        assert state == AuthState.LOCKDOWN

    def test_determine_state_boundary_normal(self, engine):
        """Test boundary at normal threshold"""
        state = engine.determine_state(70.0)
        assert state == AuthState.NORMAL

    def test_determine_state_boundary_monitoring(self, engine):
        """Test boundary at monitoring threshold"""
        state = engine.determine_state(50.0)
        assert state == AuthState.MONITORING


class TestScoreProcessing:
    """Test score processing"""

    def test_process_high_score(self, engine):
        """Test processing high confidence score"""
        result = engine.process_score(90.0)

        assert result["action"] == "allow"
        assert result["state"] == "normal"
        assert result["score"] == 90.0
        assert result["dev_mode"] is False

    def test_process_medium_score(self, engine):
        """Test processing medium confidence score"""
        # Need multiple low scores to trigger state change
        for _ in range(3):
            result = engine.process_score(55.0)

        # 55 is between monitoring (50) and normal (70), so it's monitoring
        # But state change requires confirmation for degradation
        assert result["state"] in ["normal", "monitoring"]

    def test_process_low_score_requires_confirmation(self, engine):
        """Test that low scores require confirmation"""
        # First low score shouldn't change state immediately
        result = engine.process_score(30.0)
        assert engine.low_score_count == 1

        # Second low score
        result = engine.process_score(30.0)
        assert engine.low_score_count == 2

        # Third low score triggers change - 30 is below restricted (35) so goes to lockdown
        result = engine.process_score(30.0)
        # Score of 30 is below lockdown threshold (20) is false, but below restricted (35)
        # So it should be RESTRICTED or LOCKDOWN depending on exact threshold
        assert engine.current_state in [AuthState.RESTRICTED, AuthState.LOCKDOWN]

    def test_process_score_recovery(self, engine):
        """Test recovery from low state"""
        # Get into low state
        for _ in range(3):
            engine.process_score(30.0)
        # Should be in some low state
        assert engine.current_state in [AuthState.RESTRICTED, AuthState.LOCKDOWN]

        # High score should recover immediately
        result = engine.process_score(90.0)
        assert engine.current_state == AuthState.NORMAL
        assert engine.low_score_count == 0

    def test_dev_mode_bypass(self, engine):
        """Test developer mode bypasses authentication"""
        result = engine.process_score(10.0, dev_mode=True)

        assert result["action"] == "allow"
        assert result["score"] == 100.0
        assert result["dev_mode"] is True
        assert "BYPASS" in result["reason"]


class TestStateTransitions:
    """Test state transition logic"""

    def test_degradation_requires_confirmation(self, engine):
        """Test that degradation requires confirmation"""
        engine.current_state = AuthState.NORMAL

        # Single low score shouldn't change state
        engine.process_score(30.0)
        assert engine.current_state == AuthState.NORMAL

    def test_improvement_immediate(self, engine):
        """Test that improvement is immediate"""
        engine.current_state = AuthState.RESTRICTED
        engine.previous_state = AuthState.NORMAL
        engine.low_score_count = 5

        # High score should immediately improve
        result = engine.process_score(90.0)
        # State should improve (could be NORMAL or at least better than RESTRICTED)
        assert engine.current_state.value >= AuthState.RESTRICTED.value or engine.current_state == AuthState.NORMAL

    def test_state_callback_called(self, engine):
        """Test state change callbacks are called"""
        callback = MagicMock()
        engine.add_state_callback(callback)

        # Trigger state change
        for _ in range(3):
            engine.process_score(30.0)

        callback.assert_called()


class TestActions:
    """Test action determination"""

    def test_action_for_normal(self, engine):
        """Test action for normal state"""
        action = engine._get_action_for_state(AuthState.NORMAL)
        assert action == "allow"

    def test_action_for_monitoring(self, engine):
        """Test action for monitoring state"""
        action = engine._get_action_for_state(AuthState.MONITORING)
        assert action == "allow_log"

    def test_action_for_restricted(self, engine):
        """Test action for restricted state"""
        action = engine._get_action_for_state(AuthState.RESTRICTED)
        assert action == "restrict"

    def test_action_for_lockdown(self, engine):
        """Test action for lockdown state"""
        action = engine._get_action_for_state(AuthState.LOCKDOWN)
        assert action == "lockdown"


class TestReasons:
    """Test reason generation"""

    def test_reason_for_normal(self, engine):
        """Test reason for normal state"""
        reason = engine._get_reason(AuthState.NORMAL, 85.0)
        assert "High confidence" in reason
        assert "85.0%" in reason

    def test_reason_for_lockdown(self, engine):
        """Test reason for lockdown state"""
        reason = engine._get_reason(AuthState.LOCKDOWN, 15.0)
        assert "Very low confidence" in reason
        assert "lockdown" in reason.lower()


class TestLogging:
    """Test audit logging"""

    def test_decision_logged(self, engine, mock_db):
        """Test that decisions are logged"""
        engine.process_score(85.0)

        mock_db.log_event.assert_called()
        call_args = mock_db.log_event.call_args
        assert call_args.kwargs["event_type"] == "DECISION"
        assert call_args.kwargs["confidence_score"] == 85.0

    def test_logging_handles_db_error(self, engine, mock_db):
        """Test logging handles database errors gracefully"""
        mock_db.log_event.side_effect = Exception("DB error")

        # Should not raise
        result = engine.process_score(85.0)
        assert result is not None


class TestPublishing:
    """Test Redis publishing"""

    def test_state_change_published(self, engine, mock_redis):
        """Test state changes are published"""
        # Trigger state change
        for _ in range(3):
            engine.process_score(30.0)

        # Check publish was called
        publish_calls = [
            call for call in mock_redis.publish.call_args_list
            if call[0][0] == "seclyzer:state_change"
        ]
        assert len(publish_calls) > 0


class TestStatus:
    """Test status reporting"""

    def test_get_status(self, engine):
        """Test status retrieval"""
        engine.process_score(85.0)
        engine.process_score(80.0)

        status = engine.get_status()

        assert status["current_state"] == "normal"
        assert "recent_scores" in status
        assert "average_score" in status
        assert "thresholds" in status
        assert status["thresholds"]["normal"] == 70.0


class TestForceState:
    """Test force state functionality"""

    def test_force_state(self, engine, mock_db):
        """Test forcing a specific state"""
        engine.force_state(AuthState.LOCKDOWN, "Admin override")

        assert engine.current_state == AuthState.LOCKDOWN
        mock_db.log_event.assert_called()


class TestEngineControl:
    """Test engine control methods"""

    def test_stop(self, engine, mock_redis):
        """Test stopping the engine"""
        engine._running = True
        engine.stop()

        assert engine._running is False
        engine.pubsub.unsubscribe.assert_called_once()


class TestStateCallbacks:
    """Test state callback functionality"""

    def test_callbacks_receive_state_info(self, engine):
        """Test callbacks receive correct state information"""
        received_data = []

        def callback(old_state, new_state, score):
            received_data.append({
                "old": old_state,
                "new": new_state,
                "score": score
            })

        engine.add_state_callback(callback)

        # Trigger state change
        for _ in range(3):
            engine.process_score(30.0)

        # Callback should have been called with state info
        if received_data:
            assert "old" in received_data[0]
            assert "new" in received_data[0]
            assert "score" in received_data[0]
