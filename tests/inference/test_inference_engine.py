"""
Tests for inference engine
"""

import json
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from processing.inference.inference_engine import InferenceEngine


@pytest.fixture
def temp_models_dir():
    """Create temporary models directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = MagicMock()
    redis_mock.pubsub.return_value = MagicMock()
    return redis_mock


@pytest.fixture
def engine(temp_models_dir, mock_redis):
    """Create inference engine with mocked dependencies"""
    with patch("processing.inference.inference_engine.redis.Redis", return_value=mock_redis):
        with patch("processing.inference.inference_engine.get_developer_mode", return_value=None):
            engine = InferenceEngine(models_dir=temp_models_dir, user_id="test")
            engine.redis_client = mock_redis
            return engine


class TestInferenceEngineInitialization:
    """Test inference engine initialization"""

    def test_initialization(self, engine, temp_models_dir):
        """Test basic initialization"""
        assert engine.models_dir == Path(temp_models_dir)
        assert engine.user_id == "test"
        assert engine.keystroke_model is None  # No models in temp dir
        assert engine.mouse_model is None
        assert engine.app_model is None

    def test_score_history_initialized(self, engine):
        """Test score history deques are initialized"""
        assert isinstance(engine.keystroke_scores, deque)
        assert isinstance(engine.mouse_scores, deque)
        assert isinstance(engine.app_scores, deque)
        assert engine.keystroke_scores.maxlen == 10


class TestKeystrokeScoring:
    """Test keystroke feature scoring"""

    def test_score_without_model_returns_neutral(self, engine):
        """Test scoring returns 50 when no model loaded"""
        features = {"dwell_mean": 100, "flight_mean": 50}
        score = engine.score_keystroke_features(features)
        assert score == 50.0

    def test_score_with_mock_model(self, engine):
        """Test scoring with a mock model"""
        # Create mock model
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = np.array([[0.2, 0.8]])
        engine.keystroke_model = mock_model
        engine.keystroke_feature_names = ["feat1", "feat2"]

        features = {"feat1": 100.0, "feat2": 50.0}
        score = engine.score_keystroke_features(features)

        assert score == 80.0  # 0.8 * 100
        assert len(engine.keystroke_scores) == 1

    def test_score_with_binary_prediction(self, engine):
        """Test scoring with model that only has predict"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])
        del mock_model.predict_proba  # Remove predict_proba
        engine.keystroke_model = mock_model
        engine.keystroke_feature_names = ["feat1"]

        features = {"feat1": 100.0}
        score = engine.score_keystroke_features(features)

        assert score == 100.0

    def test_score_handles_missing_features(self, engine):
        """Test scoring handles missing features gracefully"""
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])
        engine.keystroke_model = mock_model
        engine.keystroke_feature_names = ["feat1", "feat2", "feat3"]

        # Only provide some features
        features = {"feat1": 100.0}
        score = engine.score_keystroke_features(features)

        assert 0 <= score <= 100


class TestMouseScoring:
    """Test mouse feature scoring"""

    def test_score_without_model_returns_neutral(self, engine):
        """Test scoring returns 50 when no model loaded"""
        features = {"move_0": 100, "click_0": 5}
        score = engine.score_mouse_features(features)
        assert score == 50.0

    def test_score_with_mock_svm(self, engine):
        """Test scoring with mock One-Class SVM"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([1])  # Normal
        mock_model.decision_function.return_value = np.array([2.0])  # Positive = normal
        
        mock_scaler = MagicMock()
        mock_scaler.transform.return_value = np.array([[0.5, 0.5]])
        
        engine.mouse_model = mock_model
        engine.mouse_scaler = mock_scaler
        engine.mouse_feature_names = ["feat1", "feat2"]

        features = {"feat1": 100.0, "feat2": 50.0}
        score = engine.score_mouse_features(features)

        assert 0 <= score <= 100
        assert len(engine.mouse_scores) == 1

    def test_score_anomaly_detection(self, engine):
        """Test anomaly detection scoring"""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([-1])  # Anomaly
        mock_model.decision_function.return_value = np.array([-2.0])  # Negative = anomaly
        
        engine.mouse_model = mock_model
        engine.mouse_scaler = None
        engine.mouse_feature_names = ["feat1"]

        features = {"feat1": 100.0}
        score = engine.score_mouse_features(features)

        # Negative decision should result in low score
        assert score < 50


class TestAppScoring:
    """Test app transition scoring"""

    def test_score_without_model_returns_neutral(self, engine):
        """Test scoring returns 50 when no model loaded"""
        score = engine.score_app_transition("firefox", "chrome", 14)
        assert score == 50.0

    def test_score_with_known_transition(self, engine):
        """Test scoring with known transition"""
        engine.app_model = {
            "markov_chain": {
                "transitions": {
                    "firefox->chrome": {"probability": 0.5}
                }
            },
            "time_patterns": {
                "chrome": {
                    "hourly_distribution": {
                        "14": {"probability": 0.1}
                    }
                }
            }
        }

        score = engine.score_app_transition("firefox", "chrome", 14)
        assert 0 <= score <= 100
        assert len(engine.app_scores) == 1

    def test_score_unknown_transition(self, engine):
        """Test scoring with unknown transition"""
        engine.app_model = {
            "markov_chain": {"transitions": {}},
            "time_patterns": {}
        }

        score = engine.score_app_transition("unknown1", "unknown2", 12)
        assert 0 <= score <= 100


class TestScoreSmoothing:
    """Test score smoothing functionality"""

    def test_get_smoothed_scores_empty(self, engine):
        """Test smoothed scores with no history"""
        smoothed = engine.get_smoothed_scores()
        
        assert smoothed["keystroke"] == 50.0
        assert smoothed["mouse"] == 50.0
        assert smoothed["app"] == 50.0

    def test_get_smoothed_scores_with_history(self, engine):
        """Test smoothed scores with history"""
        engine.keystroke_scores.extend([80, 85, 90])
        engine.mouse_scores.extend([70, 75, 80])
        engine.app_scores.extend([60, 65, 70])

        smoothed = engine.get_smoothed_scores()

        assert 80 <= smoothed["keystroke"] <= 90
        assert 70 <= smoothed["mouse"] <= 80
        assert 60 <= smoothed["app"] <= 70


class TestFusedScore:
    """Test fused score calculation"""

    def test_fused_score_default_weights(self, engine):
        """Test fused score with default weights"""
        engine.keystroke_scores.append(80)
        engine.mouse_scores.append(70)
        engine.app_scores.append(60)

        fused = engine.get_fused_score()

        # Weighted average: 0.4*80 + 0.35*70 + 0.25*60 = 32 + 24.5 + 15 = 71.5
        assert 70 <= fused <= 75

    def test_fused_score_custom_weights(self, engine):
        """Test fused score with custom weights"""
        engine.keystroke_scores.append(100)
        engine.mouse_scores.append(0)
        engine.app_scores.append(0)

        # All weight on keystroke
        fused = engine.get_fused_score(
            keystroke_weight=1.0,
            mouse_weight=0.0,
            app_weight=0.0,
        )

        assert fused == 100.0


class TestModelLoading:
    """Test model loading functionality"""

    def test_load_keystroke_model_not_found(self, engine, temp_models_dir):
        """Test loading when no model exists"""
        engine._load_keystroke_model()
        assert engine.keystroke_model is None

    def test_load_mouse_model_not_found(self, engine, temp_models_dir):
        """Test loading when no model exists"""
        engine._load_mouse_model()
        assert engine.mouse_model is None

    def test_load_app_model_not_found(self, engine, temp_models_dir):
        """Test loading when no model exists"""
        engine._load_app_model()
        assert engine.app_model is None


class TestPublishing:
    """Test score publishing"""

    def test_publish_score(self, engine, mock_redis):
        """Test publishing individual score"""
        engine._publish_score("keystroke", 85.0, False)

        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "seclyzer:scores:keystroke"
        
        data = json.loads(call_args[0][1])
        assert data["modality"] == "keystroke"
        assert data["score"] == 85.0
        assert data["dev_mode"] is False

    def test_publish_fused_score(self, engine, mock_redis):
        """Test publishing fused score"""
        engine.keystroke_scores.append(80)
        engine.mouse_scores.append(70)
        engine.app_scores.append(60)

        engine._publish_fused_score(75.0, False)

        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "seclyzer:scores:fused"
        
        data = json.loads(call_args[0][1])
        assert "fused_score" in data
        assert "keystroke_score" in data
        assert "mouse_score" in data
        assert "app_score" in data


class TestEngineControl:
    """Test engine control methods"""

    def test_stop(self, engine, mock_redis):
        """Test stopping the engine"""
        engine._running = True
        engine.stop()
        
        assert engine._running is False
        engine.pubsub.unsubscribe.assert_called_once()

    def test_reload_models(self, engine):
        """Test model reloading"""
        with patch.object(engine, "_load_models") as mock_load:
            engine.reload_models()
            mock_load.assert_called_once()
