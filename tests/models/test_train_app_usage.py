"""
Tests for app usage model training
"""

import json
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from processing.models.train_app_usage import AppUsageModelTrainer


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
            "processing.models.train_app_usage.get_timeseries_db",
            return_value=mock_ts_db,
        ),
        patch("processing.models.train_app_usage.get_database", return_value=mock_db),
    ):
        trainer = AppUsageModelTrainer(
            user_id="test_user",
            days_back=7,
            min_transitions=10,
            output_dir=temp_output_dir,
        )
        trainer.ts_db = mock_ts_db
        trainer.db = mock_db
        return trainer


@pytest.fixture
def sample_transitions():
    """Create sample app transitions"""
    now = datetime.now(timezone.utc)
    transitions = []

    apps = ["firefox", "terminal", "vscode", "chrome"]

    for i in range(50):
        from_app = apps[i % len(apps)]
        to_app = apps[(i + 1) % len(apps)]

        transitions.append(
            {
                "timestamp": now,
                "from_app": from_app,
                "to_app": to_app,
                "duration_ms": 5000 + i * 100,
            }
        )

    return transitions


def test_trainer_initialization(trainer, temp_output_dir):
    """Test trainer initialization"""
    assert trainer.user_id == "test_user"
    assert trainer.days_back == 7
    assert trainer.min_transitions == 10
    assert str(trainer.output_dir) == temp_output_dir
    assert isinstance(trainer.transitions, defaultdict)
    assert isinstance(trainer.app_durations, defaultdict)
    assert isinstance(trainer.time_patterns, defaultdict)


def test_build_markov_chain(trainer, sample_transitions):
    """Test Markov Chain building"""
    transition_probs = trainer.build_markov_chain(sample_transitions)

    # Verify structure
    assert isinstance(transition_probs, dict)
    assert len(transition_probs) > 0

    # Verify probability format
    for key, value in transition_probs.items():
        assert "->" in key
        assert "probability" in value
        assert "count" in value
        assert "from_app" in value
        assert "to_app" in value
        assert 0 <= value["probability"] <= 1


def test_markov_chain_probabilities_sum_to_one(trainer, sample_transitions):
    """Test that transition probabilities sum to ~1 for each source app"""
    transition_probs = trainer.build_markov_chain(sample_transitions)

    # Group by source app
    app_probs = defaultdict(list)
    for key, value in transition_probs.items():
        from_app = value["from_app"]
        app_probs[from_app].append(value["probability"])

    # Check that probabilities sum to approximately 1
    for app, probs in app_probs.items():
        total = sum(probs)
        assert 0.99 <= total <= 1.01  # Allow small floating point error


def test_build_time_patterns(trainer, sample_transitions):
    """Test time-of-day pattern building"""
    # First build Markov chain to populate data structures
    trainer.build_markov_chain(sample_transitions)

    # Build time patterns
    time_patterns = trainer.build_time_patterns()

    # Verify structure
    assert isinstance(time_patterns, dict)

    for app, pattern in time_patterns.items():
        assert "hourly_distribution" in pattern
        assert "total_occurrences" in pattern
        assert "peak_hour" in pattern
        assert isinstance(pattern["hourly_distribution"], dict)
        assert pattern["total_occurrences"] > 0
        assert 0 <= pattern["peak_hour"] <= 23


def test_build_duration_stats(trainer, sample_transitions):
    """Test duration statistics calculation"""
    # Build Markov chain first
    trainer.build_markov_chain(sample_transitions)

    # Build duration stats
    duration_stats = trainer.build_duration_stats()

    # Verify structure
    assert isinstance(duration_stats, dict)

    for app, stats in duration_stats.items():
        assert "mean_duration_ms" in stats
        assert "std_duration_ms" in stats
        assert "median_duration_ms" in stats
        assert "min_duration_ms" in stats
        assert "max_duration_ms" in stats
        assert "sample_count" in stats

        # Verify values are reasonable
        assert stats["mean_duration_ms"] > 0
        assert stats["std_duration_ms"] >= 0
        assert stats["median_duration_ms"] > 0
        assert stats["min_duration_ms"] <= stats["mean_duration_ms"]
        assert stats["max_duration_ms"] >= stats["mean_duration_ms"]
        assert stats["sample_count"] > 0


def test_build_app_rankings(trainer, sample_transitions):
    """Test app usage ranking"""
    # Build Markov chain first
    trainer.build_markov_chain(sample_transitions)

    # Build rankings
    rankings = trainer.build_app_rankings()

    # Verify structure
    assert isinstance(rankings, list)
    assert len(rankings) > 0

    # Verify ranking order
    for i, item in enumerate(rankings):
        assert "rank" in item
        assert "app" in item
        assert "occurrences" in item
        assert item["rank"] == i + 1
        assert item["occurrences"] > 0

    # Verify descending order
    occurrences = [item["occurrences"] for item in rankings]
    assert occurrences == sorted(occurrences, reverse=True)


def test_calculate_entropy(trainer, sample_transitions):
    """Test entropy calculation"""
    # Build Markov chain first
    trainer.build_markov_chain(sample_transitions)

    # Calculate entropy
    entropy = trainer.calculate_entropy()

    # Verify value is reasonable
    assert entropy >= 0
    assert isinstance(entropy, float)

    # For uniform distribution over N apps, entropy should be log2(N)
    # For our test data with 4 apps, max entropy is log2(4) = 2
    assert entropy <= np.log2(4) + 0.1  # Small tolerance


def test_evaluate_model(trainer, sample_transitions):
    """Test model evaluation"""
    # Build necessary components
    transition_probs = trainer.build_markov_chain(sample_transitions)
    time_patterns = trainer.build_time_patterns()

    # Evaluate
    metrics = trainer.evaluate_model(transition_probs, time_patterns)

    # Verify metrics structure
    assert "n_unique_apps" in metrics
    assert "n_transitions" in metrics
    assert "n_apps_with_time_patterns" in metrics
    assert "entropy" in metrics
    assert "predictability_score" in metrics
    assert "transition_density" in metrics
    assert "avg_transition_probability" in metrics

    # Verify metric values
    assert metrics["n_unique_apps"] > 0
    assert metrics["n_transitions"] > 0
    assert metrics["entropy"] >= 0
    assert 0 <= metrics["predictability_score"] <= 1
    assert 0 <= metrics["transition_density"] <= 1
    assert 0 <= metrics["avg_transition_probability"] <= 1


def test_save_model(trainer, sample_transitions, temp_output_dir):
    """Test model saving"""
    # Build all components
    transition_probs = trainer.build_markov_chain(sample_transitions)
    time_patterns = trainer.build_time_patterns()
    duration_stats = trainer.build_duration_stats()
    rankings = trainer.build_app_rankings()
    metrics = trainer.evaluate_model(transition_probs, time_patterns)

    # Save model
    model_path = trainer.save_model(
        transition_probs, time_patterns, duration_stats, rankings, metrics
    )

    # Verify file was created
    assert Path(model_path).exists()
    assert model_path.endswith(".json")

    # Load and verify content
    with open(model_path, "r") as f:
        model_data = json.load(f)

    assert "metadata" in model_data
    assert "markov_chain" in model_data
    assert "time_patterns" in model_data
    assert "duration_stats" in model_data
    assert "app_rankings" in model_data
    assert "metrics" in model_data

    # Verify metadata
    assert model_data["metadata"]["model_type"] == "app_usage"
    assert model_data["metadata"]["user_id"] == "test_user"

    # Verify database calls
    assert trainer.db.save_model_metadata.called
    assert trainer.db.set_config.called


def test_fetch_training_data_insufficient_transitions(trainer, mock_ts_db):
    """Test error handling when insufficient data"""
    # Mock query that returns too few transitions
    mock_record = MagicMock()
    mock_record.get_time.return_value = datetime.now(timezone.utc)
    mock_record.values = {"from_app": "firefox", "to_app": "chrome"}
    mock_record.get_value.return_value = 5000

    mock_table = MagicMock()
    mock_table.records = [mock_record]

    mock_ts_db.query_api.query.return_value = [mock_table]

    # Should raise error due to insufficient transitions
    with pytest.raises(ValueError, match="Insufficient data"):
        trainer.fetch_training_data()


def test_fetch_training_data_success(trainer, mock_ts_db):
    """Test successful data fetching"""
    # Mock query with sufficient transitions
    mock_records = []

    apps = [("firefox", "chrome"), ("chrome", "terminal"), ("terminal", "vscode")]

    for i in range(15):  # More than min_transitions (10)
        from_app, to_app = apps[i % len(apps)]

        mock_record = MagicMock()
        mock_record.get_time.return_value = datetime.now(timezone.utc)
        mock_record.values = {"from_app": from_app, "to_app": to_app}
        mock_record.get_value.return_value = 5000 + i * 100
        mock_records.append(mock_record)

    mock_table = MagicMock()
    mock_table.records = mock_records

    mock_ts_db.query_api.query.return_value = [mock_table]

    # Fetch data
    transitions, count = trainer.fetch_training_data()

    # Verify results
    assert len(transitions) == 15
    assert count == 15
    assert all("from_app" in t for t in transitions)
    assert all("to_app" in t for t in transitions)
    assert all("duration_ms" in t for t in transitions)


def test_full_pipeline_run_success(trainer, mock_ts_db):
    """Test full training pipeline"""
    # Mock sufficient data
    mock_records = []

    apps = [
        ("firefox", "chrome"),
        ("chrome", "terminal"),
        ("terminal", "vscode"),
        ("vscode", "firefox"),
    ]

    for i in range(20):
        from_app, to_app = apps[i % len(apps)]

        mock_record = MagicMock()
        mock_record.get_time.return_value = datetime.now(timezone.utc)
        mock_record.values = {"from_app": from_app, "to_app": to_app}
        mock_record.get_value.return_value = 5000 + i * 100
        mock_records.append(mock_record)

    mock_table = MagicMock()
    mock_table.records = mock_records

    mock_ts_db.query_api.query.return_value = [mock_table]

    # Run pipeline
    success = trainer.run()

    # Verify success
    assert success is True

    # Verify model was saved
    model_files = list(Path(trainer.output_dir).glob("app_markov_*.json"))
    assert len(model_files) == 1


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
    trainer._save_metadata("v1.0.0", {"predictability_score": 0.8}, "/fake/path.json")

    # Verify it tried to save
    assert mock_db.save_model_metadata.called


def test_trainer_with_different_parameters():
    """Test trainer with various parameter combinations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("processing.models.train_app_usage.get_timeseries_db"),
            patch("processing.models.train_app_usage.get_database"),
        ):
            # Test with different parameters
            trainer1 = AppUsageModelTrainer(
                user_id="user1", days_back=14, min_transitions=50, output_dir=tmpdir
            )

            assert trainer1.user_id == "user1"
            assert trainer1.days_back == 14
            assert trainer1.min_transitions == 50

            trainer2 = AppUsageModelTrainer(
                user_id="user2", days_back=30, min_transitions=100, output_dir=tmpdir
            )

            assert trainer2.user_id == "user2"
            assert trainer2.days_back == 30
            assert trainer2.min_transitions == 100


def test_predictability_score_calculation(trainer, sample_transitions):
    """Test predictability score is calculated correctly"""
    # Build components
    transition_probs = trainer.build_markov_chain(sample_transitions)
    time_patterns = trainer.build_time_patterns()

    # Evaluate
    metrics = trainer.evaluate_model(transition_probs, time_patterns)

    # Predictability should be between 0 and 1
    assert 0 <= metrics["predictability_score"] <= 1

    # For highly predictable patterns, score should be high
    # For random patterns, score should be low


def test_transition_density_calculation(trainer):
    """Test transition density metric"""
    # Create simple transitions
    transitions = [
        {
            "timestamp": datetime.now(timezone.utc),
            "from_app": "app1",
            "to_app": "app2",
            "duration_ms": 5000,
        },
        {
            "timestamp": datetime.now(timezone.utc),
            "from_app": "app2",
            "to_app": "app1",
            "duration_ms": 5000,
        },
    ]

    transition_probs = trainer.build_markov_chain(transitions)
    time_patterns = trainer.build_time_patterns()
    metrics = trainer.evaluate_model(transition_probs, time_patterns)

    # With 2 apps, possible transitions = 4 (2x2)
    # Observed transitions = 2
    # Density = 2/4 = 0.5
    assert 0 < metrics["transition_density"] <= 1


def test_empty_time_patterns_handled(trainer):
    """Test handling of apps with no time patterns"""
    # Manually set some transitions but no time patterns
    trainer.transitions[("app1", "app2")] = 5
    trainer.app_counts["app1"] = 5
    trainer.app_counts["app2"] = 5

    # Build patterns (should handle empty gracefully)
    time_patterns = trainer.build_time_patterns()

    # Should return empty or minimal patterns
    assert isinstance(time_patterns, dict)


def test_model_json_serializable(trainer, sample_transitions):
    """Test that saved model is valid JSON"""
    # Build all components
    transition_probs = trainer.build_markov_chain(sample_transitions)
    time_patterns = trainer.build_time_patterns()
    duration_stats = trainer.build_duration_stats()
    rankings = trainer.build_app_rankings()
    metrics = trainer.evaluate_model(transition_probs, time_patterns)

    # Save model
    model_path = trainer.save_model(
        transition_probs, time_patterns, duration_stats, rankings, metrics
    )

    # Load and verify it's valid JSON
    with open(model_path, "r") as f:
        model_data = json.load(f)

    # Verify it can be serialized again
    json_str = json.dumps(model_data)
    assert len(json_str) > 0


def test_rankings_limited_to_top_20(trainer):
    """Test that rankings are limited to top 20 apps"""
    # Create data with many apps
    for i in range(30):
        app_name = f"app_{i}"
        trainer.app_counts[app_name] = 100 - i  # Descending counts

    rankings = trainer.build_app_rankings()

    # Should be limited to top 20
    assert len(rankings) <= 20
