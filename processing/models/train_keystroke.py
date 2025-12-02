#!/usr/bin/env python3
"""
Keystroke Model Training Script
Trains a Random Forest classifier on keystroke dynamics features
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score,
                             recall_score)
from sklearn.model_selection import train_test_split

from common.config import get_config
from common.logger import get_logger
from storage.database import get_database
from storage.timeseries import get_timeseries_db

logger = get_logger(__name__)


class KeystrokeModelTrainer:
    """Trains Random Forest model for keystroke dynamics"""

    def __init__(
        self,
        user_id: str = "default",
        days_back: int = 30,
        min_samples: int = 500,
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
        self.model_config = {
            "n_estimators": 50,  # Reduced for speed (was 100)
            "max_depth": 15,  # Limit depth for speed
            "min_samples_split": 10,  # Prevent overfitting
            "min_samples_leaf": 5,
            "max_features": "sqrt",  # Faster than 'auto'
            "n_jobs": -1,  # Use all CPU cores
            "random_state": 42,
            "warm_start": False,
            "class_weight": "balanced",  # Handle imbalanced data
            "bootstrap": True,
        }

        self.model = None
        self.feature_names = None
        self.n_features = 140  # Expected keystroke feature count

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
            f"Fetching keystroke data for user '{self.user_id}' (last {self.days_back} days)"
        )

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=self.days_back)

        # Build Flux query
        query = f"""
        from(bucket: "{self.ts_db.bucket}")
          |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
          |> filter(fn: (r) => r["_measurement"] == "keystroke_features")
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

        # Extract features and create labels (all are positive samples for this user)
        X = df.select(feature_cols).to_numpy()
        y = np.ones(len(X))  # All user's samples are labeled as 1 (genuine)

        # Store feature names
        self.feature_names = feature_cols
        self.n_features = len(feature_cols)

        logger.info(f"Loaded {len(X)} positive samples with {self.n_features} features")

        return X, y

    def generate_negative_samples(
        self, X_positive: np.ndarray, ratio: float = 0.3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic negative samples (impostor attempts)

        Args:
            X_positive: Positive samples
            ratio: Ratio of negative to positive samples

        Returns:
            X_negative, y_negative
        """
        n_negative = int(len(X_positive) * ratio)
        logger.info(f"Generating {n_negative} synthetic negative samples...")

        # Strategy: Add Gaussian noise and permute features
        X_negative = []

        for _ in range(n_negative):
            # Randomly select a base sample
            idx = np.random.randint(0, len(X_positive))
            base_sample = X_positive[idx].copy()

            # Add noise (simulates different typing behavior)
            noise = np.random.normal(
                0, np.std(base_sample) * 0.5, size=base_sample.shape
            )
            synthetic = base_sample + noise

            # Randomly permute some features (simulates different patterns)
            n_permute = np.random.randint(5, 20)
            perm_indices = np.random.choice(
                len(synthetic), size=n_permute, replace=False
            )
            synthetic[perm_indices] = np.random.permutation(synthetic[perm_indices])

            # Ensure non-negative values (timing can't be negative)
            synthetic = np.abs(synthetic)

            X_negative.append(synthetic)

        X_negative = np.array(X_negative)
        y_negative = np.zeros(len(X_negative))  # Label 0 for impostor

        logger.info(f"Generated {len(X_negative)} negative samples")

        return X_negative, y_negative

    def train_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Train Random Forest model

        Args:
            X: Feature matrix
            y: Labels

        Returns:
            Metrics dictionary
        """
        logger.info("Starting model training...")
        print(f"\n🤖 Training Random Forest Classifier...")
        print(f"   Samples: {len(X)}")
        print(f"   Features: {X.shape[1]}")
        print(f"   Positive: {np.sum(y == 1)} | Negative: {np.sum(y == 0)}")

        # Split into train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train model
        print(f"\n⚙️  Training with {self.model_config['n_estimators']} trees...")
        self.model = RandomForestClassifier(**self.model_config)

        import time

        start_time = time.time()
        self.model.fit(X_train, y_train)
        elapsed = time.time() - start_time

        print(f"✓ Training completed in {elapsed:.2f} seconds")

        # Evaluate
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)

        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0),
            "training_time_seconds": elapsed,
            "n_samples": len(X),
            "n_features": X.shape[1],
        }

        # Print results
        print(f"\n📈 Model Performance:")
        print(f"   Accuracy:  {metrics['accuracy']:.4f}")
        print(f"   Precision: {metrics['precision']:.4f}")
        print(f"   Recall:    {metrics['recall']:.4f}")
        print(f"   F1 Score:  {metrics['f1_score']:.4f}")

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\n📊 Confusion Matrix:")
        print(f"   TN: {cm[0][0]:4d}  FP: {cm[0][1]:4d}")
        print(f"   FN: {cm[1][0]:4d}  TP: {cm[1][1]:4d}")

        # Feature importance (top 10)
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            top_indices = np.argsort(importances)[-10:][::-1]
            print(f"\n🔝 Top 10 Important Features:")
            for i, idx in enumerate(top_indices, 1):
                feat_name = (
                    self.feature_names[idx] if self.feature_names else f"feature_{idx}"
                )
                print(f"   {i:2d}. {feat_name:20s} ({importances[idx]:.4f})")

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
        pkl_filename = f"keystroke_rf_{version}.pkl"
        pkl_path = self.output_dir / pkl_filename

        model_data = {
            "model": self.model,
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
        onnx_filename = f"keystroke_rf_{version}.onnx"
        onnx_path = self.output_dir / onnx_filename

        initial_type = [("float_input", FloatTensorType([None, self.n_features]))]
        onnx_model = convert_sklearn(
            self.model,
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
                model_type="keystroke",
                version=version,
                accuracy=metrics["accuracy"],
                model_path=pkl_path,
                username=self.user_id,
            )

            # Also save full metrics as config
            self.db.set_config(
                f"keystroke_model_{version}_metrics",
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
            # 1. Fetch data
            X_positive, y_positive = self.fetch_training_data()

            # 2. Generate negative samples
            X_negative, y_negative = self.generate_negative_samples(X_positive)

            # 3. Combine datasets
            X = np.vstack([X_positive, X_negative])
            y = np.hstack([y_positive, y_negative])

            # 4. Train model
            metrics = self.train_model(X, y)

            # 5. Save model
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
        description="Train keystroke dynamics model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with last 30 days of data
  python train_keystroke.py

  # Train with last 14 days
  python train_keystroke.py --days 14

  # Specify user and output directory
  python train_keystroke.py --user john --output ./my_models
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
        default=500,
        help="Minimum samples required (default: 500)",
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
    print("║    SecLyzer - Keystroke Model Training                ║")
    print("║    Random Forest Classifier                            ║")
    print("╚════════════════════════════════════════════════════════╝")
    print()

    # Create trainer
    trainer = KeystrokeModelTrainer(
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
