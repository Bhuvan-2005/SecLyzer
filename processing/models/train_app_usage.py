#!/usr/bin/env python3
"""
App Usage Model Training Script
Trains a Markov Chain model for application usage patterns
Optimized for laptop performance with efficient data handling
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from common.config import get_config
from common.logger import get_logger
from storage.database import get_database
from storage.timeseries import get_timeseries_db

logger = get_logger(__name__)


class AppUsageModelTrainer:
    """Trains Markov Chain model for app usage patterns"""

    def __init__(
        self,
        user_id: str = "default",
        days_back: int = 30,
        min_transitions: int = 50,
        output_dir: str = "data/models",
    ):
        """
        Initialize trainer

        Args:
            user_id: User identifier
            days_back: How many days of data to use
            min_transitions: Minimum app transitions required
            output_dir: Directory to save models
        """
        self.user_id = user_id
        self.days_back = days_back
        self.min_transitions = min_transitions
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Connect to databases
        self.ts_db = get_timeseries_db()
        self.db = get_database()

        # Model data structures
        self.transitions = defaultdict(int)  # (from_app, to_app) -> count
        self.app_durations = defaultdict(list)  # app -> [durations in ms]
        self.time_patterns = defaultdict(
            lambda: defaultdict(int)
        )  # app -> {hour: count}
        self.app_counts = defaultdict(int)  # app -> total occurrences

    def fetch_training_data(
        self, exclude_dev_mode: bool = True
    ) -> Tuple[List[Dict], int]:
        """
        Fetch app transition data from InfluxDB

        Args:
            exclude_dev_mode: Whether to exclude data collected in developer mode

        Returns:
            (list of transitions, total count)
        """
        logger.info(
            f"Fetching app transition data for user '{self.user_id}' (last {self.days_back} days)"
        )

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=self.days_back)

        # Build Flux query
        query = f"""
        from(bucket: "{self.ts_db.bucket}")
          |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
          |> filter(fn: (r) => r["_measurement"] == "app_transitions")
          |> filter(fn: (r) => r["user_id"] == "{self.user_id}")
        """

        if exclude_dev_mode:
            query += """
          |> filter(fn: (r) => r["dev_mode"] == "false" or not exists r["dev_mode"])
            """

        print(f"📊 Querying InfluxDB...")
        result = self.ts_db.query_api.query(org=self.ts_db.org, query=query)

        # Parse results
        transitions = []
        for table in result:
            for record in table.records:
                transition = {
                    "timestamp": record.get_time(),
                    "from_app": record.values.get("from_app", ""),
                    "to_app": record.values.get("to_app", ""),
                    "duration_ms": record.get_value(),
                }
                transitions.append(transition)

        print(f"✓ Fetched {len(transitions)} app transitions")

        if len(transitions) < self.min_transitions:
            raise ValueError(
                f"Insufficient data: {len(transitions)} transitions "
                f"(minimum {self.min_transitions} required)"
            )

        return transitions, len(transitions)

    def build_markov_chain(self, transitions: List[Dict]) -> Dict[str, Dict]:
        """
        Build Markov Chain transition probability matrix

        Args:
            transitions: List of app transitions

        Returns:
            Transition probability matrix
        """
        logger.info("Building Markov Chain transition matrix...")

        # Count transitions
        for t in transitions:
            from_app = t["from_app"]
            to_app = t["to_app"]
            duration = t["duration_ms"]
            timestamp = t["timestamp"]

            # Record transition
            key = (from_app, to_app)
            self.transitions[key] += 1

            # Record duration
            self.app_durations[from_app].append(duration)

            # Record time pattern (hour of day)
            hour = timestamp.hour
            self.time_patterns[from_app][hour] += 1

            # Count app occurrences
            self.app_counts[from_app] += 1
            self.app_counts[to_app] += 1

        # Calculate transition probabilities
        transition_probs = {}

        # Get all unique apps
        all_apps = set()
        for from_app, to_app in self.transitions.keys():
            all_apps.add(from_app)
            all_apps.add(to_app)

        print(f"\n🔗 Markov Chain Statistics:")
        print(f"   Unique apps:     {len(all_apps)}")
        print(f"   Total transitions: {len(transitions)}")

        # Calculate probability for each transition
        for from_app in all_apps:
            # Get total transitions from this app
            total_from = sum(
                count for (f, t), count in self.transitions.items() if f == from_app
            )

            if total_from == 0:
                continue

            for to_app in all_apps:
                count = self.transitions.get((from_app, to_app), 0)
                prob = count / total_from if total_from > 0 else 0

                if prob > 0:  # Only store non-zero probabilities
                    key = f"{from_app}->{to_app}"
                    transition_probs[key] = {
                        "probability": prob,
                        "count": count,
                        "from_app": from_app,
                        "to_app": to_app,
                    }

        print(f"   Stored probabilities: {len(transition_probs)}")

        return transition_probs

    def build_time_patterns(self) -> Dict[str, Dict]:
        """
        Build time-of-day usage patterns

        Returns:
            Time patterns for each app
        """
        logger.info("Building time-of-day patterns...")

        patterns = {}

        for app, hour_counts in self.time_patterns.items():
            total_occurrences = sum(hour_counts.values())

            if total_occurrences == 0:
                continue

            # Calculate probability for each hour
            hour_probs = {}
            for hour in range(24):
                count = hour_counts.get(hour, 0)
                prob = count / total_occurrences
                if prob > 0:
                    hour_probs[str(hour)] = {
                        "probability": prob,
                        "count": count,
                    }

            patterns[app] = {
                "hourly_distribution": hour_probs,
                "total_occurrences": total_occurrences,
                "peak_hour": (
                    max(hour_counts, key=hour_counts.get) if hour_counts else 0
                ),
            }

        print(f"\n⏰ Time Pattern Statistics:")
        print(f"   Apps with patterns: {len(patterns)}")

        return patterns

    def build_duration_stats(self) -> Dict[str, Dict]:
        """
        Calculate duration statistics for each app

        Returns:
            Duration statistics
        """
        logger.info("Calculating duration statistics...")

        stats = {}

        for app, durations in self.app_durations.items():
            if not durations:
                continue

            durations_array = np.array(durations)

            stats[app] = {
                "mean_duration_ms": float(np.mean(durations_array)),
                "std_duration_ms": float(np.std(durations_array)),
                "median_duration_ms": float(np.median(durations_array)),
                "min_duration_ms": float(np.min(durations_array)),
                "max_duration_ms": float(np.max(durations_array)),
                "sample_count": len(durations),
            }

        print(f"\n📊 Duration Statistics:")
        print(f"   Apps tracked: {len(stats)}")

        return stats

    def build_app_rankings(self) -> List[Dict]:
        """
        Build app usage rankings

        Returns:
            List of apps sorted by usage
        """
        sorted_apps = sorted(self.app_counts.items(), key=lambda x: x[1], reverse=True)

        rankings = []
        for rank, (app, count) in enumerate(sorted_apps[:20], 1):  # Top 20
            rankings.append(
                {
                    "rank": rank,
                    "app": app,
                    "occurrences": count,
                }
            )

        print(f"\n🏆 Top 10 Most Used Apps:")
        for item in rankings[:10]:
            print(
                f"   {item['rank']:2d}. {item['app']:30s} ({item['occurrences']} times)"
            )

        return rankings

    def calculate_entropy(self) -> float:
        """
        Calculate entropy of app usage (measure of predictability)

        Returns:
            Entropy value (higher = more random/unpredictable)
        """
        # Calculate app usage distribution
        total = sum(self.app_counts.values())
        if total == 0:
            return 0.0

        probs = [count / total for count in self.app_counts.values()]

        # Calculate Shannon entropy
        entropy = -sum(p * np.log2(p) if p > 0 else 0 for p in probs)

        return float(entropy)

    def evaluate_model(
        self, transition_probs: Dict, time_patterns: Dict
    ) -> Dict[str, float]:
        """
        Evaluate model quality

        Args:
            transition_probs: Transition probabilities
            time_patterns: Time patterns

        Returns:
            Evaluation metrics
        """
        logger.info("Evaluating model...")

        # Calculate coverage metrics
        n_apps = len(self.app_counts)
        n_transitions = len(transition_probs)
        n_time_patterns = len(time_patterns)

        # Calculate predictability score (inverse of entropy)
        entropy = self.calculate_entropy()
        max_entropy = np.log2(n_apps) if n_apps > 0 else 1
        predictability = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0

        # Calculate transition density (how many possible transitions are observed)
        possible_transitions = n_apps * n_apps
        transition_density = (
            n_transitions / possible_transitions if possible_transitions > 0 else 0
        )

        # Average transition probability
        avg_prob = (
            np.mean([p["probability"] for p in transition_probs.values()])
            if transition_probs
            else 0
        )

        metrics = {
            "n_unique_apps": n_apps,
            "n_transitions": n_transitions,
            "n_apps_with_time_patterns": n_time_patterns,
            "entropy": entropy,
            "predictability_score": predictability,
            "transition_density": transition_density,
            "avg_transition_probability": float(avg_prob),
        }

        print(f"\n📈 Model Evaluation:")
        print(f"   Unique apps:           {metrics['n_unique_apps']}")
        print(f"   Transitions:           {metrics['n_transitions']}")
        print(f"   Entropy:               {metrics['entropy']:.4f}")
        print(f"   Predictability:        {metrics['predictability_score']:.4f}")
        print(f"   Transition density:    {metrics['transition_density']:.4f}")

        return metrics

    def save_model(
        self,
        transition_probs: Dict,
        time_patterns: Dict,
        duration_stats: Dict,
        rankings: List[Dict],
        metrics: Dict,
    ) -> str:
        """
        Save model as JSON

        Args:
            transition_probs: Transition probabilities
            time_patterns: Time patterns
            duration_stats: Duration statistics
            rankings: App rankings
            metrics: Evaluation metrics

        Returns:
            Path to saved model
        """
        version = datetime.now().strftime("v1.0.0_%Y%m%d_%H%M%S")
        filename = f"app_markov_{version}.json"
        model_path = self.output_dir / filename

        model_data = {
            "metadata": {
                "model_type": "app_usage",
                "version": version,
                "user_id": self.user_id,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "days_back": self.days_back,
            },
            "markov_chain": {
                "transitions": transition_probs,
            },
            "time_patterns": time_patterns,
            "duration_stats": duration_stats,
            "app_rankings": rankings,
            "metrics": metrics,
        }

        # Save as JSON
        with open(model_path, "w") as f:
            json.dump(model_data, f, indent=2)

        print(f"\n💾 Saved model: {model_path}")

        # Save metadata to database
        self._save_metadata(version, metrics, str(model_path))

        return str(model_path)

    def _save_metadata(self, version: str, metrics: Dict, model_path: str):
        """Save model metadata to database"""
        try:
            # Use predictability as "accuracy" metric
            self.db.save_model_metadata(
                model_type="app_usage",
                version=version,
                accuracy=metrics["predictability_score"],
                model_path=model_path,
                username=self.user_id,
            )

            # Save full metrics as config
            self.db.set_config(
                f"app_model_{version}_metrics",
                {
                    "version": version,
                    "model_path": model_path,
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
            transitions, n_transitions = self.fetch_training_data()

            # 2. Build Markov Chain
            transition_probs = self.build_markov_chain(transitions)

            # 3. Build time patterns
            time_patterns = self.build_time_patterns()

            # 4. Calculate duration stats
            duration_stats = self.build_duration_stats()

            # 5. Build rankings
            rankings = self.build_app_rankings()

            # 6. Evaluate model
            metrics = self.evaluate_model(transition_probs, time_patterns)

            # 7. Save model
            model_path = self.save_model(
                transition_probs, time_patterns, duration_stats, rankings, metrics
            )

            print(f"\n✅ Training completed successfully!")
            print(f"   Model: {model_path}")

            return True

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            print(f"\n❌ Training failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Train app usage model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with last 30 days of data
  python train_app_usage.py

  # Train with last 14 days
  python train_app_usage.py --days 14

  # Specify user and output directory
  python train_app_usage.py --user john --output ./my_models
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
        "--min-transitions",
        type=int,
        default=50,
        help="Minimum transitions required (default: 50)",
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
    print("║    SecLyzer - App Usage Model Training                 ║")
    print("║    Markov Chain + Time Patterns                        ║")
    print("╚════════════════════════════════════════════════════════╝")
    print()

    # Create trainer
    trainer = AppUsageModelTrainer(
        user_id=args.user,
        days_back=args.days,
        min_transitions=args.min_transitions,
        output_dir=args.output,
    )

    # Run training
    success = trainer.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
