#!/usr/bin/env python3
"""
Mouse Model Training Script
Trains a One-Class SVM for mouse behavior anomaly detection
Optimized for laptop performance with efficient data handling
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import onnx
import polars as pl
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score,
                             precision_recall_curve, precision_score,
                             recall_score, roc_auc_score)
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from common.config import get_config
from common.logger import get_logger
from storage.database import get_database
from storage.timeseries import get_timeseries_db

logger = get_logger(__name__)


class MouseModelTrainer:
    """Trains One-Class SVM model for mouse behavior anomaly detection"""

    def __init__(
        self,
        user_id: str = "default",
        days_back: int = 30,
        min_samples: int = 800,
        output_dir: str = "data/models",
    ):
        """
        Initialize trainer

        Args:
            user_id: User identifier
            days_back: How many days of data to use
            min_samples: Minimum samples required for training
            output_dir: Directory to save models
        """
        self.user_id = user_id
        self.days_back = days_back
        self.min_samples = min_samples
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Connect to databases
        self.ts_db = get_timeseries_db()
        self.db = get_database()

        # Model configuration (optimized for laptops)
        # One-Class SVM learns the boundary of normal behavior
        self.model_config = {
            "kernel": "rbf",  # Radial basis function kernel
            "gamma": "scale",  # Auto-scale gamma
            "nu": 0.1,  # Upper bound on fraction of outliers (10%)
            "shrinking": True,  # Use shrinking heuristic
            "cache_size": 500,  # MB cache for kernel computations (laptop-friendly)
            "max_iter": 1000,  # Limit iterations for speed
        }

        self.model = None
        self.scaler = StandardScaler()  # SVM requires feature scaling
        self.feature_names = None
        self.n_features = 38  # Expected mouse feature count

    def fetch_training_data(
        self, exclude_dev_mode: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fetch training data from InfluxDB

        Args:
            exclude_dev_mode: Whether to exclude data collected in developer mode

        Returns:
            X (features), y (labels) arrays
        """
        logger.info(
            f"Fetching mouse data for user '{self.user_id}' (last {self.days_back} days)"
        )

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=self.days_back)

        # Build Flux query
        query = f"""
        from(bucket: "{self.ts_db.bucket}")
          |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
          |> filter(fn: (r) => r["_measurement"] == "mouse_features")
          |> filter(fn: (r) => r["user_id"] == "{self.user_id}")
        """

        if exclude_dev_mode:
            query += """
          |> filter(fn: (r) => r["dev_mode"] == "false" or not exists r["dev_mode"])
            """

        print(f"📊 Querying InfluxDB...")
        result = self.ts_db.query_api.query(org=self.ts_db.org, query=query)

        # Parse results into structured format
        data_points = []
        for table in result:
            for record in table.records:
                timestamp = record.get_time()
                field_name = record.get_field()
                value = record.get_value()

                # Find or create data point for this timestamp
                dp = next((d for d in data_points if d["timestamp"] == timestamp), None)
                if dp is None:
                    dp = {"timestamp": timestamp}
                    data_points.append(dp)

                dp[field_name] = value

        print(f"✓ Fetched {len(data_points)} feature vectors")

        if len(data_points) < self.min_samples:
            raise ValueError(
                f"Insufficient data: {len(data_points)} samples "
                f"(minimum {self.min_samples} required)"
            )

        # Convert to DataFrame for easier manipulation
        df = pl.DataFrame(data_points)

        # Remove timestamp and non-feature columns
        feature_cols = [
            col for col in df.columns if col not in ["timestamp", "dev_mode", "type"]
        ]

        # Extract features (all are normal samples for this user)
        X = df.select(feature_cols).to_numpy()
        y = np.ones(len(X))  # All user's samples are labeled as 1 (normal)

        # Store feature names
        self.feature_names = feature_cols
        self.n_features = len(feature_cols)

        logger.info(f"Loaded {len(X)} normal samples with {self.n_features} features")

        return X, y

    def generate_anomaly_samples(
        self, X_normal: np.ndarray, ratio: float = 0.2
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic anomaly samples for evaluation

        Args:
            X_normal: Normal samples
            ratio: Ratio of anomaly to normal samples

        Returns:
            X_anomaly, y_anomaly
        """
        n_anomaly = int(len(X_normal) * ratio)
        logger.info(f"Generating {n_anomaly} synthetic anomaly samples...")

        X_anomaly = []

        for _ in range(n_anomaly):
            # Strategy 1: Extreme value injection (50% of anomalies)
            if np.random.random() < 0.5:
                idx = np.random.randint(0, len(X_normal))
                sample = X_normal[idx].copy()

                # Randomly select features to make extreme
                n_extreme = np.random.randint(3, 8)
                extreme_indices = np.random.choice(
                    len(sample), size=n_extreme, replace=False
                )

                # Make values extreme (very high or very low)
                for idx in extreme_indices:
                    if np.random.random() < 0.5:
                        sample[idx] *= np.random.uniform(3.0, 10.0)  # Very high
                    else:
                        sample[idx] *= np.random.uniform(0.1, 0.3)  # Very low

                X_anomaly.append(sample)

            # Strategy 2: Pattern disruption (50% of anomalies)
            else:
                idx = np.random.randint(0, len(X_normal))
                sample = X_normal[idx].copy()

                # Inject strong noise
                noise = np.random.normal(0, np.std(sample) * 1.5, size=sample.shape)
                sample = sample + noise

                # Randomly shuffle some features
                n_shuffle = np.random.randint(5, 15)
                shuffle_indices = np.random.choice(
                    len(sample), size=n_shuffle, replace=False
                )
                sample[shuffle_indices] = np.random.permutation(sample[shuffle_indices])

                X_anomaly.append(sample)

        X_anomaly = np.array(X_anomaly)
        X_anomaly = np.abs(X_anomaly)  # Ensure non-negative values
        y_anomaly = -np.ones(len(X_anomaly))  # Label -1 for anomaly

        logger.info(f"Generated {len(X_anomaly)} anomaly samples")

        return X_anomaly, y_anomaly

    def train_model(self, X: np.ndarray) -> Dict[str, float]:
        """
        Train One-Class SVM model

        Args:
            X: Feature matrix (normal samples only)

        Returns:
            Metrics dictionary
        """
        logger.info("Starting model training...")
        print(f"\n🤖 Training One-Class SVM...")
        print(f"   Samples: {len(X)}")
        print(f"   Features: {X.shape[1]}")

        # Scale features (critical for SVM)
        print(f"\n⚙️  Scaling features...")
        X_scaled = self.scaler.fit_transform(X)

        # Reserve some normal samples for testing
        n_test = int(len(X) * 0.2)
        X_train = X_scaled[:-n_test]
        X_test_normal = X_scaled[-n_test:]

        # Train One-Class SVM on normal data only
        print(f"⚙️  Training SVM (nu={self.model_config['nu']})...")
        self.model = OneClassSVM(**self.model_config)

        import time

        start_time = time.time()
        self.model.fit(X_train)
        elapsed = time.time() - start_time

        print(f"✓ Training completed in {elapsed:.2f} seconds")

        # Evaluate on test set
        # Generate anomalies for evaluation
        X_test_anomaly, y_test_anomaly = self.generate_anomaly_samples(
            X_test_normal, ratio=0.5
        )

        # Combine test sets
        X_test_combined = np.vstack([X_test_normal, X_test_anomaly])
        y_test_combined = np.hstack(
            [np.ones(len(X_test_normal)), -np.ones(len(X_test_anomaly))]
        )

        # Predict
        y_pred = self.model.predict(X_test_combined)

        # Calculate metrics
        # Convert labels: SVM uses +1/-1, we'll use 1/0 for metrics
        y_test_binary = (y_test_combined == 1).astype(int)
        y_pred_binary = (y_pred == 1).astype(int)

        # Decision scores for ROC
        decision_scores = self.model.decision_function(X_test_combined)

        # Calculate AUC if possible
        try:
            auc_score = roc_auc_score(y_test_binary, decision_scores)
        except (ValueError, TypeError):
            auc_score = 0.0

        metrics = {
            "accuracy": accuracy_score(y_test_binary, y_pred_binary),
            "precision": precision_score(y_test_binary, y_pred_binary, zero_division=0),
            "recall": recall_score(y_test_binary, y_pred_binary, zero_division=0),
            "f1_score": f1_score(y_test_binary, y_pred_binary, zero_division=0),
            "auc": auc_score,
            "training_time_seconds": elapsed,
            "n_samples": len(X),
            "n_features": X.shape[1],
            "n_support_vectors": self.model.n_support_,
        }

        # Print results
        print(f"\n📈 Model Performance:")
        print(f"   Accuracy:         {metrics['accuracy']:.4f}")
        print(f"   Precision:        {metrics['precision']:.4f}")
        print(f"   Recall:           {metrics['recall']:.4f}")
        print(f"   F1 Score:         {metrics['f1_score']:.4f}")
        print(f"   AUC:              {metrics['auc']:.4f}")
        print(f"   Support Vectors:  {metrics['n_support_vectors']}")

        # Confusion matrix
        cm = confusion_matrix(y_test_binary, y_pred_binary)
        print(f"\n📊 Confusion Matrix:")
        print(f"   TN: {cm[0][0]:4d}  FP: {cm[0][1]:4d}")
        print(f"   FN: {cm[1][0]:4d}  TP: {cm[1][1]:4d}")

        # Decision boundary info
        normal_scores = decision_scores[y_test_binary == 1]
        anomaly_scores = decision_scores[y_test_binary == 0]

        print(f"\n📏 Decision Scores:")
        print(
            f"   Normal   - Mean: {np.mean(normal_scores):7.3f}, Std: {np.std(normal_scores):7.3f}"
        )
        print(
            f"   Anomaly  - Mean: {np.mean(anomaly_scores):7.3f}, Std: {np.std(anomaly_scores):7.3f}"
        )

        logger.info("Model training completed", metrics=metrics)

        return metrics

    def save_model(self, metrics: Dict[str, float]) -> Tuple[str, str]:
        """
        Save model in both PKL and ONNX formats

        Args:
            metrics: Training metrics

        Returns:
            (pkl_path, onnx_path)
        """
        version = datetime.now().strftime("v1.0.0_%Y%m%d_%H%M%S")

        # Save as PKL (scikit-learn format)
        pkl_filename = f"mouse_svm_{version}.pkl"
        pkl_path = self.output_dir / pkl_filename

        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "n_features": self.n_features,
            "user_id": self.user_id,
            "version": version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "config": self.model_config,
        }

        joblib.dump(model_data, pkl_path)
        print(f"\n💾 Saved PKL model: {pkl_path}")

        # Convert to ONNX
        onnx_filename = f"mouse_svm_{version}.onnx"
        onnx_path = self.output_dir / onnx_filename

        # For One-Class SVM, we need to wrap model + scaler together
        from sklearn.pipeline import Pipeline

        pipeline = Pipeline([("scaler", self.scaler), ("svm", self.model)])

        initial_type = [("float_input", FloatTensorType([None, self.n_features]))]
        onnx_model = convert_sklearn(
            pipeline,
            initial_types=initial_type,
            target_opset=12,
        )

        with open(onnx_path, "wb") as f:
            f.write(onnx_model.SerializeToString())

        print(f"💾 Saved ONNX model: {onnx_path}")

        # Save metadata to SQLite
        self._save_metadata(version, metrics, str(pkl_path), str(onnx_path))

        return str(pkl_path), str(onnx_path)

    def _save_metadata(
        self, version: str, metrics: Dict, pkl_path: str, onnx_path: str
    ):
        """Save model metadata to database"""
        try:
            self.db.save_model_metadata(
                model_type="mouse",
                version=version,
                accuracy=metrics["accuracy"],
                model_path=pkl_path,
                username=self.user_id,
            )

            # Also save full metrics as config
            self.db.set_config(
                f"mouse_model_{version}_metrics",
                {
                    "version": version,
                    "onnx_path": onnx_path,
                    "pkl_path": pkl_path,
                    **metrics,
                },
            )

            logger.info("Model metadata saved to database")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def run(self) -> bool:
        """
        Run complete training pipeline

        Returns:
            True if successful
        """
        try:
            # 1. Fetch normal data
            X_normal, y_normal = self.fetch_training_data()

            # 2. Train model (only on normal data)
            metrics = self.train_model(X_normal)

            # 3. Save model
            pkl_path, onnx_path = self.save_model(metrics)

            print(f"\n✅ Training completed successfully!")
            print(f"   PKL:  {pkl_path}")
            print(f"   ONNX: {onnx_path}")

            return True

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            print(f"\n❌ Training failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Train mouse behavior anomaly detection model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with last 30 days of data
  python train_mouse.py

  # Train with last 14 days
  python train_mouse.py --days 14

  # Specify user and output directory
  python train_mouse.py --user john --output ./my_models
        """,
    )

    parser.add_argument(
        "--user",
        default="default",
        help="User ID (default: default)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Days of historical data to use (default: 30)",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=800,
        help="Minimum samples required (default: 800)",
    )
    parser.add_argument(
        "--output",
        default="data/models",
        help="Output directory for models (default: data/models)",
    )
    parser.add_argument(
        "--include-dev-mode",
        action="store_true",
        help="Include data collected in developer mode (default: exclude)",
    )

    args = parser.parse_args()

    # Banner
    print("╔════════════════════════════════════════════════════════╗")
    print("║    SecLyzer - Mouse Model Training                     ║")
    print("║    One-Class SVM (Anomaly Detection)                   ║")
    print("╚════════════════════════════════════════════════════════╝")
    print()

    # Create trainer
    trainer = MouseModelTrainer(
        user_id=args.user,
        days_back=args.days,
        min_samples=args.min_samples,
        output_dir=args.output,
    )

    # Run training
    success = trainer.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
