#!/usr/bin/env python3
"""
SecLyzer Model Training Orchestrator
Manages training of all behavioral biometric models
"""

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure project root is on path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.logger import get_logger
from storage.database import get_database
from storage.timeseries import get_timeseries_db

logger = get_logger(__name__)


class TrainingOrchestrator:
    """Orchestrates training of all models"""

    def __init__(
        self,
        user_id: str = "default",
        days_back: int = 30,
        output_dir: str = "data/models",
    ):
        self.user_id = user_id
        self.days_back = days_back
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.ts_db = get_timeseries_db()
        self.db = get_database()

        # Training requirements
        self.requirements = {
            "keystroke": {
                "min_samples": 500,
                "measurement": "keystroke_features",
                "recommended": 1000,
            },
            "mouse": {
                "min_samples": 800,
                "measurement": "mouse_features",
                "recommended": 1500,
            },
            "app": {
                "min_samples": 50,
                "measurement": "app_transitions",
                "recommended": 100,
            },
        }

    def check_data_availability(self) -> Dict[str, Dict]:
        """
        Check how much training data is available

        Returns:
            Dictionary with data counts per modality
        """
        print("\n📊 Checking Data Availability...\n")

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=self.days_back)

        results = {}

        for modality, req in self.requirements.items():
            measurement = req["measurement"]

            query = f"""
            from(bucket: "{self.ts_db.bucket}")
              |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
              |> filter(fn: (r) => r["_measurement"] == "{measurement}")
              |> filter(fn: (r) => r["user_id"] == "{self.user_id}")
              |> filter(fn: (r) => r["dev_mode"] == "false" or not exists r["dev_mode"])
              |> count()
            """

            try:
                result = self.ts_db.query_api.query(org=self.ts_db.org, query=query)
                count = 0

                for table in result:
                    for record in table.records:
                        count = max(count, int(record.get_value()))

                min_req = req["min_samples"]
                recommended = req["recommended"]
                ready = count >= min_req
                optimal = count >= recommended

                percentage = (count / recommended * 100) if recommended > 0 else 0

                status_icon = "✅" if optimal else ("⚠️" if ready else "❌")
                status_text = (
                    "OPTIMAL" if optimal else ("READY" if ready else "INSUFFICIENT")
                )

                print(f"{status_icon} {modality.capitalize():12s}: {count:5d} samples")
                print(f"   Status: {status_text}")
                print(f"   Progress: {percentage:.1f}% of recommended")
                print(f"   Required: {min_req} | Recommended: {recommended}")
                print()

                results[modality] = {
                    "count": count,
                    "ready": ready,
                    "optimal": optimal,
                    "percentage": percentage,
                    "status": status_text,
                }

            except Exception as e:
                logger.error(f"Error checking {modality} data: {e}")
                print(f"❌ {modality.capitalize():12s}: ERROR - {e}\n")
                results[modality] = {
                    "count": 0,
                    "ready": False,
                    "optimal": False,
                    "percentage": 0,
                    "status": "ERROR",
                }

        return results

    def train_keystroke_model(self) -> Tuple[bool, Optional[str]]:
        """Train keystroke model"""
        print("\n" + "=" * 60)
        print("  TRAINING KEYSTROKE MODEL")
        print("=" * 60 + "\n")

        try:
            from processing.models.train_keystroke import KeystrokeModelTrainer

            trainer = KeystrokeModelTrainer(
                user_id=self.user_id,
                days_back=self.days_back,
                output_dir=str(self.output_dir),
            )

            success = trainer.run()
            model_path = None

            if success:
                # Get latest model
                latest = self.db.get_latest_model("keystroke", self.user_id)
                if latest:
                    model_path = latest.get("model_path")

            return success, model_path

        except Exception as e:
            logger.error(f"Keystroke model training failed: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return False, None

    def train_mouse_model(self) -> Tuple[bool, Optional[str]]:
        """Train mouse model"""
        print("\n" + "=" * 60)
        print("  TRAINING MOUSE MODEL")
        print("=" * 60 + "\n")

        try:
            from processing.models.train_mouse import MouseModelTrainer

            trainer = MouseModelTrainer(
                user_id=self.user_id,
                days_back=self.days_back,
                output_dir=str(self.output_dir),
            )

            success = trainer.run()
            model_path = None

            if success:
                # Get latest model
                latest = self.db.get_latest_model("mouse", self.user_id)
                if latest:
                    model_path = latest.get("model_path")

            return success, model_path

        except Exception as e:
            logger.error(f"Mouse model training failed: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return False, None

    def train_app_model(self) -> Tuple[bool, Optional[str]]:
        """Train app usage model"""
        print("\n" + "=" * 60)
        print("  TRAINING APP USAGE MODEL")
        print("=" * 60 + "\n")

        try:
            from processing.models.train_app_usage import AppUsageModelTrainer

            trainer = AppUsageModelTrainer(
                user_id=self.user_id,
                days_back=self.days_back,
                output_dir=str(self.output_dir),
            )

            success = trainer.run()
            model_path = None

            if success:
                # Get latest model
                latest = self.db.get_latest_model("app_usage", self.user_id)
                if latest:
                    model_path = latest.get("model_path")

            return success, model_path

        except Exception as e:
            logger.error(f"App model training failed: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return False, None

    def print_summary(self, results: Dict[str, Tuple[bool, Optional[str]]]):
        """Print training summary"""
        print("\n" + "=" * 60)
        print("  TRAINING SUMMARY")
        print("=" * 60 + "\n")

        total = len(results)
        successful = sum(1 for success, _ in results.values() if success)
        failed = total - successful

        for model_type, (success, model_path) in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{model_type.upper():15s}: {status}")
            if model_path:
                print(f"                 Path: {model_path}")

        print(f"\n📊 Overall: {successful}/{total} models trained successfully")

        if failed > 0:
            print(f"⚠️  {failed} model(s) failed to train")

    def run(
        self,
        models: List[str],
        force: bool = False,
        check_only: bool = False,
    ) -> bool:
        """
        Run training pipeline

        Args:
            models: List of models to train ('keystroke', 'mouse', 'app', or 'all')
            force: Skip data availability checks
            check_only: Only check data, don't train

        Returns:
            True if all requested models trained successfully
        """
        start_time = time.time()

        # Check data availability
        data_status = self.check_data_availability()

        if check_only:
            return all(status["ready"] for status in data_status.values())

        # Determine which models to train
        if "all" in models:
            models_to_train = ["keystroke", "mouse", "app"]
        else:
            models_to_train = models

        # Validate data availability
        if not force:
            insufficient = [
                m for m in models_to_train if not data_status.get(m, {}).get("ready")
            ]

            if insufficient:
                print("\n❌ Insufficient data for the following models:")
                for m in insufficient:
                    status = data_status.get(m, {})
                    print(
                        f"   - {m.capitalize()}: {status.get('count', 0)} samples "
                        f"(need {self.requirements[m]['min_samples']})"
                    )
                print("\nOptions:")
                print("  1. Collect more data (let system run longer)")
                print("  2. Use --force to train anyway (not recommended)")
                print("  3. Reduce --days to use a shorter time window")
                return False

        # Train models
        results = {}

        if "keystroke" in models_to_train:
            results["keystroke"] = self.train_keystroke_model()

        if "mouse" in models_to_train:
            results["mouse"] = self.train_mouse_model()

        if "app" in models_to_train:
            results["app"] = self.train_app_model()

        # Print summary
        self.print_summary(results)

        elapsed = time.time() - start_time
        print(f"\n⏱️  Total training time: {elapsed:.2f} seconds")

        # Return success if all requested models trained successfully
        return all(success for success, _ in results.values())


def main():
    parser = argparse.ArgumentParser(
        description="Train SecLyzer behavioral biometric models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check data availability
  python scripts/train_models.py --check

  # Train all models
  python scripts/train_models.py --all

  # Train specific models
  python scripts/train_models.py --keystroke --mouse

  # Train with custom settings
  python scripts/train_models.py --all --days 14 --user john

  # Force training (skip data checks)
  python scripts/train_models.py --all --force
        """,
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Train all models (keystroke, mouse, app)",
    )
    parser.add_argument(
        "--keystroke",
        action="store_true",
        help="Train keystroke model",
    )
    parser.add_argument(
        "--mouse",
        action="store_true",
        help="Train mouse model",
    )
    parser.add_argument(
        "--app",
        action="store_true",
        help="Train app usage model",
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
        "--output",
        default="data/models",
        help="Output directory for models (default: data/models)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force training even with insufficient data",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check data availability, don't train",
    )

    args = parser.parse_args()

    # Determine which models to train
    models = []
    if args.all:
        models.append("all")
    else:
        if args.keystroke:
            models.append("keystroke")
        if args.mouse:
            models.append("mouse")
        if args.app:
            models.append("app")

    # If no models specified and not just checking, default to all
    if not models and not args.check:
        models.append("all")

    # Banner
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║      SecLyzer - Model Training Orchestrator            ║")
    print("║                                                        ║")
    print("║  Trains behavioral biometric authentication models    ║")
    print("╚════════════════════════════════════════════════════════╝")

    # Create orchestrator
    orchestrator = TrainingOrchestrator(
        user_id=args.user,
        days_back=args.days,
        output_dir=args.output,
    )

    # Run training
    success = orchestrator.run(
        models=models,
        force=args.force,
        check_only=args.check,
    )

    if args.check:
        sys.exit(0 if success else 1)
    else:
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
