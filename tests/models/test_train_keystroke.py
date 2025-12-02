"""
Tests for keystroke model training
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from processing.models.train_keystroke import KeystrokeModelTrainer


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
            "processing.models.train_keystroke.get_timeseries_db",
            return_value=mock_ts_db,
        ),
        patch("processing.models.train_keystroke.get_database", return_value=mock_db),
    ):
        trainer = KeystrokeModelTrainer(
            user_id="test_user", days_back=7, min_samples=10, output_dir=temp_output_dir
        )
        trainer.ts_db = mock_ts_db
        trainer.db = mock_db
        return trainer


def test_trainer_initialization(trainer, temp_output_dir):
    """Test trainer initialization"""
    assert trainer.user_id == "test_user"
    assert trainer.days_back == 7
    assert trainer.min_samples == 10
    assert str(trainer.output_dir) == temp_output_dir
    assert trainer.n_features == 140
    assert trainer.model is None


def test_generate_negative_samples(trainer):
    """Test synthetic negative sample generation"""
    # Create positive samples
    X_positive = np.random.randn(100, 140).astype(np.float64)
    X_positive = np.abs(X_positive)

    # Generate negative samples
    X_negative, y_negative = trainer.generate_negative_samples(X_positive, ratio=0.3)

    # Verify shape and labels
    assert len(X_negative) == 30  # 30% of 100
    assert X_negative.shape[1] == 140
    assert len(y_negative) == 30
    assert np.all(y_negative == 0)

    # Verify all values are non-negative
    assert np.all(X_negative >= 0)


def test_train_model_with_synthetic_data(trainer):
    """Test model training with synthetic data"""
    # Create synthetic data
    n_samples = 100
    X = np.random.randn(n_samples, 140).astype(np.float64)
    X = np.abs(X) * 100  # Scale to realistic timing values

    # Half positive, half negative
    y = np.hstack([np.ones(50), np.zeros(50)])

    # Train model
    metrics = trainer.train_model(X, y)

    # Verify model was created
    assert trainer.model is not None

    # Verify metrics
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "training_time_seconds" in metrics
    assert "n_samples" in metrics
    assert "n_features" in metrics

    # Verify metric values are reasonable
    assert 0 <= metrics["accuracy"] <= 1
    assert 0 <= metrics["precision"] <= 1
    assert 0 <= metrics["recall"] <= 1
    assert 0 <= metrics["f1_score"] <= 1
    assert metrics["training_time_seconds"] > 0
    assert metrics["n_samples"] == n_samples
    assert metrics["n_features"] == 140


def test_save_model(trainer, temp_output_dir):
    """Test model saving"""
    # Train a simple model first
    X = np.random.randn(100, 140).astype(np.float64)
    X = np.abs(X) * 100
    y = np.hstack([np.ones(50), np.zeros(50)])

    trainer.feature_names = [f"feature_{i}" for i in range(140)]
    metrics = trainer.train_model(X, y)

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


def test_fetch_training_data_insufficient_samples(trainer, mock_ts_db):
    """Test error handling when insufficient data"""
    # Mock query that returns too few samples
    mock_record = MagicMock()
    mock_record.get_time.return_value = datetime.now(timezone.utc)
    mock_record.get_field.return_value = "dwell_mean"
    mock_record.get_value.return_value = 100.0

    mock_table = MagicMock()
    mock_table.records = [mock_record]

    mock_ts_db.query_api.query.return_value = [mock_table]

    # Should raise error due to insufficient samples (only 1, need 10)
    with pytest.raises(ValueError, match="Insufficient data"):
        trainer.fetch_training_data()


def test_fetch_training_data_success(trainer, mock_ts_db):
    """Test successful data fetching"""
    # Mock query with sufficient samples
    mock_records = []

    # Create 20 timestamped feature vectors
    for i in range(20):
        timestamp = datetime.now(timezone.utc)

        # Each timestamp has multiple fields
        for feature in ["dwell_mean", "dwell_std", "flight_mean", "flight_std"]:
            mock_record = MagicMock()
            mock_record.get_time.return_value = timestamp
            mock_record.get_field.return_value = feature
            mock_record.get_value.return_value = float(100 + i)
            mock_records.append(mock_record)

    mock_table = MagicMock()
    mock_table.records = mock_records

    mock_ts_db.query_api.query.return_value = [mock_table]

    # Fetch data
    X, y = trainer.fetch_training_data()

    # Verify results
    assert len(X) == 20
    assert len(y) == 20
    assert np.all(y == 1)  # All positive samples
    assert trainer.feature_names is not None
    assert trainer.n_features > 0


def test_model_config_optimized_for_laptops(trainer):
    """Test that model configuration is laptop-friendly"""
    config = trainer.model_config

    # Verify reduced tree count for speed
    assert config["n_estimators"] <= 100

    # Verify depth limit
    assert "max_depth" in config
    assert config["max_depth"] <= 20

    # Verify parallel processing enabled
    assert config["n_jobs"] == -1

    # Verify balanced class weights
    assert config["class_weight"] == "balanced"


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


def test_feature_names_preserved(trainer):
    """Test that feature names are properly stored"""
    trainer.feature_names = ["feat_1", "feat_2", "feat_3"]

    assert trainer.feature_names == ["feat_1", "feat_2", "feat_3"]
    assert len(trainer.feature_names) == 3


def test_negative_sample_generation_diversity(trainer):
    """Test that negative samples are diverse"""
    X_positive = np.random.randn(100, 140).astype(np.float64)
    X_positive = np.abs(X_positive) * 100

    X_negative, y_negative = trainer.generate_negative_samples(X_positive, ratio=0.5)

    # Check that negative samples are different from positive
    # (This is probabilistic but should hold)
    distances = []
    for neg_sample in X_negative[:10]:
        min_dist = min(np.linalg.norm(neg_sample - pos) for pos in X_positive[:10])
        distances.append(min_dist)

    # Most negative samples should be reasonably different
    assert np.mean(distances) > 0.1


def test_trainer_with_different_parameters():
    """Test trainer with various parameter combinations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("processing.models.train_keystroke.get_timeseries_db"),
            patch("processing.models.train_keystroke.get_database"),
        ):
            # Test with different parameters
            trainer1 = KeystrokeModelTrainer(
                user_id="user1", days_back=14, min_samples=100, output_dir=tmpdir
            )

            assert trainer1.user_id == "user1"
            assert trainer1.days_back == 14
            assert trainer1.min_samples == 100

            trainer2 = KeystrokeModelTrainer(
                user_id="user2", days_back=30, min_samples=500, output_dir=tmpdir
            )

            assert trainer2.user_id == "user2"
            assert trainer2.days_back == 30
            assert trainer2.min_samples == 500
