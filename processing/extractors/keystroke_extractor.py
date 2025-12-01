"""
Keystroke Feature Extractor
Processes raw keystroke events into ML-ready feature vectors
"""

import json
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
import polars as pl
import redis

from common import get_developer_mode
from common.logger import get_logger
from common.retry import retry_with_backoff
from common.validators import validate_event
from storage import get_timeseries_db

# Initialize logger
logger = get_logger(__name__)


class KeystrokeExtractor:
    def __init__(self, window_seconds: int = 30, update_interval: int = 5):
        """
        Initialize keystroke feature extractor

        Args:
            window_seconds: Size of sliding window in seconds
            update_interval: How often to calculate features (seconds)
        """
        self.window_seconds = window_seconds
        self.update_interval = update_interval

        # Event buffer (stores recent events)
        self.events = deque(maxlen=10000)

        # Last update time
        self.last_update = datetime.now()

        # Connect to Redis with auth support
        redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=redis_password if redis_password else None,
            decode_responses=True,
        )
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe("seclyzer:events")

        # Connect to database
        self.db = get_timeseries_db()

        # Developer mode
        self.dev_mode = get_developer_mode()

    def process_events(self):
        """Main event processing loop"""
        logger.info("Keystroke Extractor starting", component="keystroke_extractor")

        for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])

                    # Only process keystroke events
                    if event.get("type") == "keystroke":
                        self._add_event(event)

                        # Check if it's time to calculate features
                        if (
                            datetime.now() - self.last_update
                        ).total_seconds() >= self.update_interval:
                            features = self.extract_features()
                            if features:
                                self._save_features(features)
                            self.last_update = datetime.now()

                except Exception as e:
                    logger.error(
                        "Error processing keystroke event",
                        error=str(e),
                        event_type="keystroke",
                    )

    def _add_event(self, event: Dict):
        """Add event to buffer"""
        self.events.append(
            {
                "timestamp": event["ts"] / 1_000_000,  # Convert microseconds to seconds
                "key": event["key"],
                "event_type": event["event"],  # 'press' or 'release'
                "dev_mode": self.dev_mode.is_active() if self.dev_mode else False,
            }
        )

    def extract_features(self) -> Optional[Dict]:
        """
        Extract features from event buffer

        Returns:
            Dict with 140 features, or None if insufficient data
        """
        # Get events from last window
        cutoff_time = datetime.now().timestamp() - self.window_seconds
        recent_events = [e for e in self.events if e["timestamp"] > cutoff_time]

        if len(recent_events) < 10:  # Need minimum events
            return None

        # Convert to polars DataFrame for fast processing
        df = pl.DataFrame(recent_events)

        # Calculate dwell times (time key is held down)
        dwell_times = self._calculate_dwell_times(df)

        # Calculate flight times (time between key releases and next press)
        flight_times = self._calculate_flight_times(df)

        # Calculate digraph timings (common 2-key combinations)
        digraphs = self._calculate_digraphs(df)

        # Calculate error patterns (backspace usage)
        errors = self._calculate_error_patterns(df)

        # Calculate rhythm features
        rhythm = self._calculate_rhythm(df)

        # Combine all features
        features = {}

        # Dwell time features (8)
        if dwell_times:
            features.update(
                {
                    "dwell_mean": np.mean(dwell_times),
                    "dwell_std": np.std(dwell_times),
                    "dwell_min": np.min(dwell_times),
                    "dwell_max": np.max(dwell_times),
                    "dwell_median": np.median(dwell_times),
                    "dwell_q25": np.percentile(dwell_times, 25),
                    "dwell_q75": np.percentile(dwell_times, 75),
                    "dwell_range": np.max(dwell_times) - np.min(dwell_times),
                }
            )

        # Flight time features (8)
        if flight_times:
            features.update(
                {
                    "flight_mean": np.mean(flight_times),
                    "flight_std": np.std(flight_times),
                    "flight_min": np.min(flight_times),
                    "flight_max": np.max(flight_times),
                    "flight_median": np.median(flight_times),
                    "flight_q25": np.percentile(flight_times, 25),
                    "flight_q75": np.percentile(flight_times, 75),
                    "flight_range": np.max(flight_times) - np.min(flight_times),
                }
            )

        # Digraph features (top 20 most common 2-key combinations)
        features.update(digraphs)

        # Error features (4)
        features.update(errors)

        # Rhythm features (8)
        features.update(rhythm)

        # Add developer mode flag
        features["dev_mode"] = any(e["dev_mode"] for e in recent_events)

        # Total keys pressed
        features["total_keys"] = len(recent_events) // 2  # Divide by 2 (press+release)

        return features

    def _calculate_dwell_times(self, df: pl.DataFrame) -> List[float]:
        """Calculate dwell times (how long each key is held)"""
        dwell_times = []

        # Group events by key
        grouped = df.group_by("key").agg([pl.col("timestamp"), pl.col("event_type")])

        for group in grouped.iter_rows(named=True):
            timestamps = group["timestamp"]
            events = group["event_type"]

            # Match press/release pairs
            press_time = None
            for ts, evt in zip(timestamps, events):
                if evt == "press":
                    press_time = ts
                elif evt == "release" and press_time is not None:
                    dwell = (ts - press_time) * 1000  # Convert to ms
                    if 0 < dwell < 1000:  # Sanity check (0-1000ms)
                        dwell_times.append(dwell)
                    press_time = None

        return dwell_times

    def _calculate_flight_times(self, df: pl.DataFrame) -> List[float]:
        """Calculate flight times (time between releasing one key and pressing next)"""
        flight_times = []

        # Sort by timestamp
        df_sorted = df.sort("timestamp")

        last_release_time = None

        for row in df_sorted.iter_rows(named=True):
            if row["event_type"] == "release":
                last_release_time = row["timestamp"]
            elif row["event_type"] == "press" and last_release_time is not None:
                flight = (row["timestamp"] - last_release_time) * 1000  # Convert to ms
                if 0 < flight < 2000:  # Sanity check
                    flight_times.append(flight)

        return flight_times

    def _calculate_digraphs(self, df: pl.DataFrame) -> Dict:
        """Calculate timings for common 2-key combinations"""
        # Get sequence of key presses (ignore releases)
        presses = df.filter(pl.col("event_type") == "press").sort("timestamp")

        digraph_times = defaultdict(list)

        # Convert to list of dicts for easier iteration
        press_list = presses.to_dicts()

        for i in range(len(press_list) - 1):
            row1 = press_list[i]
            row2 = press_list[i + 1]

            key_pair = f"{row1['key']}_{row2['key']}"
            time_diff = (row2["timestamp"] - row1["timestamp"]) * 1000

            if 0 < time_diff < 2000:
                digraph_times[key_pair].append(time_diff)

        # Get top 20 most frequent digraphs
        top_digraphs = sorted(
            digraph_times.items(), key=lambda x: len(x[1]), reverse=True
        )[:20]

        features = {}
        for i, (digraph, times) in enumerate(top_digraphs):
            features[f"digraph_{i}_mean"] = np.mean(times)

        # Pad with zeros if less than 20
        for i in range(len(top_digraphs), 20):
            features[f"digraph_{i}_mean"] = 0.0

        return features

    def _calculate_error_patterns(self, df: pl.DataFrame) -> Dict:
        """Calculate error/correction patterns"""
        total_keys = len(df.filter(pl.col("event_type") == "press"))

        # Count backspace presses
        backspace_count = len(
            df.filter(
                (pl.col("key").str.contains("Backspace|Delete"))
                & (pl.col("event_type") == "press")
            )
        )

        return {
            "backspace_frequency": backspace_count / max(total_keys, 1),
            "backspace_count": backspace_count,
            "correction_rate": backspace_count / max(total_keys - backspace_count, 1),
            "clean_typing_ratio": (total_keys - backspace_count) / max(total_keys, 1),
        }

    def _calculate_rhythm(self, df: pl.DataFrame) -> Dict:
        """Calculate typing rhythm features"""
        presses = df.filter(pl.col("event_type") == "press").sort("timestamp")

        if len(presses) < 2:
            return {f"rhythm_{i}": 0.0 for i in range(8)}

        # Convert to list for easier iteration
        press_list = presses.to_dicts()

        # Inter-key intervals
        intervals = []
        for i in range(len(press_list) - 1):
            interval = (
                press_list[i + 1]["timestamp"] - press_list[i]["timestamp"]
            ) * 1000
            if 0 < interval < 5000:
                intervals.append(interval)

        if not intervals:
            return {f"rhythm_{i}": 0.0 for i in range(8)}

        # Detect bursts (rapid typing) vs pauses
        burst_threshold = np.median(intervals)
        bursts = [i for i in intervals if i < burst_threshold]
        pauses = [i for i in intervals if i >= burst_threshold]

        return {
            "rhythm_consistency": 1.0
            - (np.std(intervals) / max(np.mean(intervals), 1)),
            "burst_frequency": len(bursts) / max(len(intervals), 1),
            "pause_frequency": len(pauses) / max(len(intervals), 1),
            "avg_burst_speed": np.mean(bursts) if bursts else 0,
            "avg_pause_duration": np.mean(pauses) if pauses else 0,
            "rhythm_variation": np.std(intervals),
            "typing_speed_wpm": 60000
            / max(np.mean(intervals), 1)
            / 5,  # Rough WPM estimate
            "rhythm_stability": 1.0 / (1.0 + np.var(intervals)),
        }

    def _save_features(self, features: Dict):
        """Save features to InfluxDB and publish to Redis"""
        try:
            # 1. Write to InfluxDB (Storage)
            self.db.write_keystroke_features(features)

            # 2. Publish to Redis (Real-time Inference)
            # Add timestamp and type metadata
            features["timestamp"] = datetime.now(timezone.utc).isoformat()
            features["type"] = "keystroke"
            self.redis_client.publish(
                "seclyzer:features:keystroke", json.dumps(features)
            )

            print(
                f"[Keystroke Extractor] Saved & Published features | Dev mode: {features.get('dev_mode', False)}"
            )
        except Exception as e:
            print(f"[Keystroke Extractor] Error saving features: {e}")


if __name__ == "__main__":
    extractor = KeystrokeExtractor()
    extractor.process_events()
