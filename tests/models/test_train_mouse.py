"""
Tests for mouse model training
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from processing.models.train_mouse import MouseModelTrainer


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_db():
    """Mock database connection"""
    db = MagicMock()
    db.save_model_metadata = MagicMock()
    db.set_config = MagicMock()
    return db


@pytest.fixture
def mock_ts_db():
    """Mock time-series database connection"""
    ts_db = MagicMock()
    ts_db.bucket = "test_bucket"
    ts_db.org = "test_org"

    # Mock query API
    query_api = MagicMock()
    ts_db.query_api = query_api

    return ts_db


@pytest.fixture
def trainer(temp_output_dir, mock_db, mock_ts_db):
    """Create trainer instance with mocked dependencies"""
    with (
        patch(
            "processing.models.train_mouse.get_timeseries_db",
            return_value=mock_ts_db,
        ),
        patch("processing.models.train_mouse.get_database", return_value=mock_db),
    ):
        trainer = MouseModelTrainer(
            user_id="test_user", days_back=7, min_samples=20, output_dir=temp_output_dir
        )
        trainer.ts_db = mock_ts_db
        trainer.db = mock_db
        return trainer


def test_trainer_initialization(trainer, temp_output_dir):
    """Test trainer initialization"""
    assert trainer.user_id == "test_user"
    assert trainer.days_back == 7
    assert trainer.min_samples == 20
    assert str(trainer.output_dir) == temp_output_dir
    assert trainer.n_features == 38
    assert trainer.model is None
    assert trainer.scaler is not None


def test_model_config_for_one_class_svm(trainer):
    """Test One-Class SVM configuration"""
    config = trainer.model_config

    # Verify kernel type
    assert config["kernel"] == "rbf"

    # Verify gamma scaling
    assert config["gamma"] == "scale"

    # Verify nu parameter (outlier fraction)
    assert config["nu"] == 0.1
    assert 0 < config["nu"] < 1

    # Verify cache size is laptop-friendly
    assert config["cache_size"] == 500

    # Verify max iterations limit
    assert config["max_iter"] == 1000


def test_generate_anomaly_samples(trainer):
    """Test synthetic anomaly sample generation"""
    # Create normal samples
    X_normal = np.random.randn(100, 38).astype(np.float64)
    X_normal = np.abs(X_normal) * 50  # Realistic mouse values

    # Generate anomaly samples
    X_anomaly, y_anomaly = trainer.generate_anomaly_samples(X_normal, ratio=0.2)

    # Verify shape and labels
    assert len(X_anomaly) == 20  # 20% of 100
    assert X_anomaly.shape[1] == 38
    assert len(y_anomaly) == 20
    assert np.all(y_anomaly == -1)  # One-Class SVM uses -1 for anomalies

    # Verify all values are non-negative
    assert np.all(X_anomaly >= 0)


def test_anomaly_samples_are_different_from_normal(trainer):
    """Test that anomaly samples are actually anomalous"""
    X_normal = np.random.randn(100, 38).astype(np.float64)
    X_normal = np.abs(X_normal) * 50

    X_anomaly, y_anomaly = trainer.generate_anomaly_samples(X_normal, ratio=0.3)

    # Calculate distances from normal samples
    distances = []
    for anomaly_sample in X_anomaly[:10]:
        min_dist = min(
            np.linalg.norm(anomaly_sample - normal) for normal in X_normal[:10]
        )
        distances.append(min_dist)

    # Anomalies should be reasonably different
    assert np.mean(distances) > 1.0


def test_train_model_with_synthetic_data(trainer):
    """Test model training with synthetic data"""
    # Create synthetic normal data
    n_samples = 100
    X = np.random.randn(n_samples, 38).astype(np.float64)
    X = np.abs(X) * 50  # Scale to realistic mouse values

    # Train model (One-Class SVM only uses normal data)
    metrics = trainer.train_model(X)

    # Verify model was created
    assert trainer.model is not None

    # Verify scaler was fitted
    assert hasattr(trainer.scaler, "mean_")

    # Verify metrics
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "auc" in metrics
    assert "training_time_seconds" in metrics
    assert "n_samples" in metrics
    assert "n_features" in metrics
    assert "n_support_vectors" in metrics

    # Verify metric values are reasonable
    assert 0 <= metrics["accuracy"] <= 1
    assert 0 <= metrics["precision"] <= 1
    assert 0 <= metrics["recall"] <= 1
    assert 0 <= metrics["f1_score"] <= 1
    assert 0 <= metrics["auc"] <= 1
    assert metrics["training_time_seconds"] > 0
    assert metrics["n_samples"] == n_samples
    assert metrics["n_features"] == 38
    assert metrics["n_support_vectors"] > 0


def test_feature_scaling(trainer):
    """Test that features are properly scaled"""
    X = np.random.randn(100, 38).astype(np.float64)
    X = np.abs(X) * 100  # Unscaled data with large variance

    # Train model (will scale internally)
    trainer.train_model(X)

    # Verify scaler has been fitted
    assert hasattr(trainer.scaler, "mean_")
    assert hasattr(trainer.scaler, "scale_")
    assert len(trainer.scaler.mean_) == 38
    assert len(trainer.scaler.scale_) == 38


def test_save_model(trainer, temp_output_dir):
    """Test model saving"""
    # Train a simple model first
    X = np.random.randn(100, 38).astype(np.float64)
    X = np.abs(X) * 50

    trainer.feature_names = [f"feature_{i}" for i in range(38)]
    metrics = trainer.train_model(X)

    # Save model
    pkl_path, onnx_path = trainer.save_model(metrics)

    # Verify files were created
    assert Path(pkl_path).exists()
    assert Path(onnx_path).exists()
    assert pkl_path.endswith(".pkl")
    assert onnx_path.endswith(".onnx")

    # Verify database calls
    assert trainer.db.save_model_metadata.called
    assert trainer.db.set_config.called


def test_save_model_includes_scaler(trainer, temp_output_dir):
    """Test that saved model includes the scaler"""
    X = np.random.randn(100, 38).astype(np.float64)
    X = np.abs(X) * 50

    trainer.feature_names = (
        [f"move_{i}" for i in range(20)]
        + [f"click_{i}" for i in range(10)]
        + [f"scroll_{i}" for i in range(8)]
    )
    metrics = trainer.train_model(X)

    pkl_path, onnx_path = trainer.save_model(metrics)

    # Load and verify scaler is included
    import joblib

    model_data = joblib.load(pkl_path)
    assert "scaler" in model_data
    assert "model" in model_data
    assert model_data["scaler"] is not None


def test_fetch_training_data_insufficient_samples(trainer, mock_ts_db):
    """Test error handling when insufficient data"""
    # Mock query that returns too few samples
    mock_record = MagicMock()
    mock_record.get_time.return_value = datetime.now(timezone.utc)
    mock_record.get_field.return_value = "move_0"
    mock_record.get_value.return_value = 100.0

    mock_table = MagicMock()
    mock_table.records = [mock_record]

    mock_ts_db.query_api.query.return_value = [mock_table]

    # Should raise error due to insufficient samples
    with pytest.raises(ValueError, match="Insufficient data"):
        trainer.fetch_training_data()


def test_fetch_training_data_success(trainer, mock_ts_db):
    """Test successful data fetching"""
    # Mock query with sufficient samples
    mock_records = []

    # Create 30 timestamped feature vectors
    for i in range(30):
        timestamp = datetime.now(timezone.utc)

        # Each timestamp has multiple fields
        for feature in ["move_0", "move_1", "click_0", "scroll_0"]:
            mock_record = MagicMock()
            mock_record.get_time.return_value = timestamp
            mock_record.get_field.return_value = feature
            mock_record.get_value.return_value = float(50 + i)
            mock_records.append(mock_record)

    mock_table = MagicMock()
    mock_table.records = mock_records

    mock_ts_db.query_api.query.return_value = [mock_table]

    # Fetch data
    X, y = trainer.fetch_training_data()

    # Verify results
    assert len(X) == 30
    assert len(y) == 30
    assert np.all(y == 1)  # All normal samples
    assert trainer.feature_names is not None
    assert trainer.n_features > 0


def test_full_pipeline_run_failure_handling(trainer, mock_ts_db):
    """Test error handling in full pipeline"""
    # Make query fail
    mock_ts_db.query_api.query.side_effect = Exception("Database connection error")

    # Run should return False on error
    success = trainer.run()

    assert success is False


def test_metadata_save_handles_errors(trainer, mock_db):
    """Test that metadata save failures don't crash the system"""
    # Make metadata save fail
    mock_db.save_model_metadata.side_effect = Exception("Database error")

    # Should not raise, just log error
    trainer._save_metadata(
        "v1.0.0", {"accuracy": 0.9}, "/fake/path.pkl", "/fake/path.onnx"
    )

    # Verify it tried to save
    assert mock_db.save_model_metadata.called


def test_trainer_with_different_parameters():
    """Test trainer with various parameter combinations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("processing.models.train_mouse.get_timeseries_db"),
            patch("processing.models.train_mouse.get_database"),
        ):
            # Test with different parameters
            trainer1 = MouseModelTrainer(
                user_id="user1", days_back=14, min_samples=100, output_dir=tmpdir
            )

            assert trainer1.user_id == "user1"
            assert trainer1.days_back == 14
            assert trainer1.min_samples == 100

            trainer2 = MouseModelTrainer(
                user_id="user2", days_back=30, min_samples=800, output_dir=tmpdir
            )

            assert trainer2.user_id == "user2"
            assert trainer2.days_back == 30
            assert trainer2.min_samples == 800


def test_decision_function_available(trainer):
    """Test that decision function is available after training"""
    X = np.random.randn(100, 38).astype(np.float64)
    X = np.abs(X) * 50

    trainer.train_model(X)

    # Verify model has decision_function
    assert hasattr(trainer.model, "decision_function")

    # Test prediction
    X_test = np.random.randn(10, 38).astype(np.float64)
    X_test = np.abs(X_test) * 50
    X_test_scaled = trainer.scaler.transform(X_test)

    predictions = trainer.model.predict(X_test_scaled)
    assert len(predictions) == 10
    assert all(p in [-1, 1] for p in predictions)


def test_support_vectors_count(trainer):
    """Test that support vectors are counted correctly"""
    X = np.random.randn(100, 38).astype(np.float64)
    X = np.abs(X) * 50

    metrics = trainer.train_model(X)

    # Verify support vectors exist and count is reasonable
    assert metrics["n_support_vectors"] > 0
    assert metrics["n_support_vectors"] <= len(X)


def test_model_handles_edge_cases(trainer):
    """Test model training with edge case data"""
    # Test with all zeros
    X_zeros = np.zeros((100, 38))
    try:
        trainer.train_model(X_zeros)
        # Should not crash, though results may not be meaningful
        assert trainer.model is not None
    except Exception as e:
        # Some edge cases might fail, which is acceptable
        assert "singular matrix" in str(e).lower() or "constant" in str(e).lower()


def test_anomaly_generation_strategies(trainer):
    """Test both anomaly generation strategies"""
    X_normal = np.random.randn(100, 38).astype(np.float64)
    X_normal = np.abs(X_normal) * 50

    # Generate multiple batches and verify diversity
    X_anomaly1, _ = trainer.generate_anomaly_samples(X_normal, ratio=0.2)
    X_anomaly2, _ = trainer.generate_anomaly_samples(X_normal, ratio=0.2)

    # Different runs should produce different results
    assert not np.allclose(X_anomaly1, X_anomaly2)
