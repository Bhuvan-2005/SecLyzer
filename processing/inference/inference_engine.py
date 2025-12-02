#!/usr/bin/env python3
"""
Inference Engine for SecLyzer
Loads trained models and performs real-time inference on behavioral features
"""

import json
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import redis

from common.developer_mode import get_developer_mode
from common.logger import get_logger

logger = get_logger(__name__)


class InferenceEngine:
    """
    Real-time inference engine for behavioral biometric authentication.

    Loads trained models and scores incoming features from extractors.
    Publishes confidence scores for the decision engine.
    """

    def __init__(
        self,
        models_dir: str = "data/models",
        user_id: str = "default",
    ):
        """
        Initialize inference engine.

        Args:
            models_dir: Directory containing trained models
            user_id: User identifier for model selection
        """
        self.models_dir = Path(models_dir)
        self.user_id = user_id

        # Model storage
        self.keystroke_model = None
        self.keystroke_feature_names: List[str] = []
        self.mouse_model = None
        self.mouse_scaler = None
        self.mouse_feature_names: List[str] = []
        self.app_model: Optional[Dict] = None

        # Score history for smoothing
        self.keystroke_scores: deque = deque(maxlen=10)
        self.mouse_scores: deque = deque(maxlen=10)
        self.app_scores: deque = deque(maxlen=10)

        # Redis connection
        redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=redis_password if redis_password else None,
            decode_responses=True,
        )
        self.pubsub = self.redis_client.pubsub()

        # Developer mode
        self.dev_mode = get_developer_mode()

        # Running state
        self._running = False
        self._lock = threading.Lock()

        # Load models
        self._load_models()

    def _load_models(self):
        """Load all trained models from disk."""
        logger.info("Loading trained models...")

        # Load keystroke model
        self._load_keystroke_model()

        # Load mouse model
        self._load_mouse_model()

        # Load app model
        self._load_app_model()

        logger.info("Model loading complete")

    def _load_keystroke_model(self):
        """Load the latest keystroke model."""
        try:
            # Find latest keystroke model
            pattern = "keystroke_rf_*.pkl"
            models = sorted(self.models_dir.glob(pattern), reverse=True)

            if not models:
                logger.warning("No keystroke model found")
                return

            model_path = models[0]
            logger.info(f"Loading keystroke model: {model_path}")

            model_data = joblib.load(model_path)
            self.keystroke_model = model_data["model"]
            self.keystroke_feature_names = model_data.get("feature_names", [])

            logger.info(
                f"Keystroke model loaded: {len(self.keystroke_feature_names)} features"
            )

        except Exception as e:
            logger.error(f"Failed to load keystroke model: {e}")
            self.keystroke_model = None

    def _load_mouse_model(self):
        """Load the latest mouse model."""
        try:
            # Find latest mouse model
            pattern = "mouse_svm_*.pkl"
            models = sorted(self.models_dir.glob(pattern), reverse=True)

            if not models:
                logger.warning("No mouse model found")
                return

            model_path = models[0]
            logger.info(f"Loading mouse model: {model_path}")

            model_data = joblib.load(model_path)
            self.mouse_model = model_data["model"]
            self.mouse_scaler = model_data.get("scaler")
            self.mouse_feature_names = model_data.get("feature_names", [])

            logger.info(f"Mouse model loaded: {len(self.mouse_feature_names)} features")

        except Exception as e:
            logger.error(f"Failed to load mouse model: {e}")
            self.mouse_model = None

    def _load_app_model(self):
        """Load the latest app usage model."""
        try:
            # Find latest app model
            pattern = "app_markov_*.json"
            models = sorted(self.models_dir.glob(pattern), reverse=True)

            if not models:
                logger.warning("No app model found")
                return

            model_path = models[0]
            logger.info(f"Loading app model: {model_path}")

            with open(model_path, "r") as f:
                self.app_model = json.load(f)

            logger.info("App model loaded")

        except Exception as e:
            logger.error(f"Failed to load app model: {e}")
            self.app_model = None

    def score_keystroke_features(self, features: Dict[str, float]) -> float:
        """
        Score keystroke features using the trained model.

        Args:
            features: Dictionary of feature name -> value

        Returns:
            Confidence score (0-100)
        """
        if self.keystroke_model is None:
            return 50.0  # Neutral score if no model

        try:
            # Build feature vector in correct order
            if self.keystroke_feature_names:
                feature_vector = []
                for name in self.keystroke_feature_names:
                    value = features.get(name, 0.0)
                    feature_vector.append(float(value) if value is not None else 0.0)
            else:
                # Fallback: use all numeric features
                feature_vector = [
                    float(v)
                    for k, v in features.items()
                    if isinstance(v, (int, float))
                    and k not in ["dev_mode", "timestamp", "type"]
                ]

            if not feature_vector:
                return 50.0

            X = np.array([feature_vector])

            # Get prediction probability
            if hasattr(self.keystroke_model, "predict_proba"):
                proba = self.keystroke_model.predict_proba(X)
                # Probability of being genuine (class 1)
                score = proba[0][1] * 100
            else:
                # Fallback to binary prediction
                pred = self.keystroke_model.predict(X)
                score = 100.0 if pred[0] == 1 else 0.0

            # Store for smoothing
            self.keystroke_scores.append(score)

            return float(score)

        except Exception as e:
            logger.error(f"Keystroke scoring error: {e}")
            return 50.0

    def score_mouse_features(self, features: Dict[str, float]) -> float:
        """
        Score mouse features using the trained model.

        Args:
            features: Dictionary of feature name -> value

        Returns:
            Confidence score (0-100)
        """
        if self.mouse_model is None:
            return 50.0  # Neutral score if no model

        try:
            # Build feature vector in correct order
            if self.mouse_feature_names:
                feature_vector = []
                for name in self.mouse_feature_names:
                    value = features.get(name, 0.0)
                    feature_vector.append(float(value) if value is not None else 0.0)
            else:
                # Fallback: use all numeric features
                feature_vector = [
                    float(v)
                    for k, v in features.items()
                    if isinstance(v, (int, float))
                    and k not in ["dev_mode", "timestamp", "type"]
                ]

            if not feature_vector:
                return 50.0

            X = np.array([feature_vector])

            # Scale features if scaler available
            if self.mouse_scaler is not None:
                X = self.mouse_scaler.transform(X)

            # One-Class SVM: +1 = normal, -1 = anomaly
            prediction = self.mouse_model.predict(X)

            # Get decision function for confidence
            if hasattr(self.mouse_model, "decision_function"):
                decision = self.mouse_model.decision_function(X)[0]
                # Convert decision to 0-100 score
                # Positive decision = normal, negative = anomaly
                # Use sigmoid-like transformation
                score = 100 / (1 + np.exp(-decision))
            else:
                score = 100.0 if prediction[0] == 1 else 0.0

            # Store for smoothing
            self.mouse_scores.append(score)

            return float(score)

        except Exception as e:
            logger.error(f"Mouse scoring error: {e}")
            return 50.0

    def score_app_transition(
        self, from_app: str, to_app: str, current_hour: int
    ) -> float:
        """
        Score an app transition using the Markov chain model.

        Args:
            from_app: Previous application
            to_app: Current application
            current_hour: Current hour (0-23)

        Returns:
            Confidence score (0-100)
        """
        if self.app_model is None:
            return 50.0  # Neutral score if no model

        try:
            transitions = self.app_model.get("markov_chain", {}).get("transitions", {})
            time_patterns = self.app_model.get("time_patterns", {})

            # Get transition probability
            transition_key = f"{from_app}->{to_app}"
            transition_data = transitions.get(transition_key, {})
            transition_prob = transition_data.get("probability", 0.01)  # Small default

            # Get time-of-day probability
            app_time_pattern = time_patterns.get(to_app, {})
            hourly_dist = app_time_pattern.get("hourly_distribution", {})
            time_prob = hourly_dist.get(str(current_hour), {}).get("probability", 0.01)

            # Combine probabilities (geometric mean)
            combined_prob = np.sqrt(transition_prob * time_prob)

            # Convert to 0-100 score
            # Higher probability = higher score
            # Use log scale for better distribution
            score = min(100, max(0, 50 + 50 * np.log10(combined_prob + 0.001) / 2))

            # Store for smoothing
            self.app_scores.append(score)

            return float(score)

        except Exception as e:
            logger.error(f"App scoring error: {e}")
            return 50.0

    def get_smoothed_scores(self) -> Dict[str, float]:
        """
        Get exponentially smoothed scores for all modalities.

        Returns:
            Dictionary with smoothed scores
        """

        def smooth(scores: deque, alpha: float = 0.3) -> float:
            if not scores:
                return 50.0
            # Exponential moving average
            result = scores[0]
            for score in list(scores)[1:]:
                result = alpha * score + (1 - alpha) * result
            return result

        return {
            "keystroke": smooth(self.keystroke_scores),
            "mouse": smooth(self.mouse_scores),
            "app": smooth(self.app_scores),
        }

    def get_fused_score(
        self,
        keystroke_weight: float = 0.4,
        mouse_weight: float = 0.35,
        app_weight: float = 0.25,
    ) -> float:
        """
        Get weighted fusion of all modality scores.

        Args:
            keystroke_weight: Weight for keystroke score
            mouse_weight: Weight for mouse score
            app_weight: Weight for app score

        Returns:
            Fused confidence score (0-100)
        """
        smoothed = self.get_smoothed_scores()

        # Normalize weights
        total_weight = keystroke_weight + mouse_weight + app_weight
        keystroke_weight /= total_weight
        mouse_weight /= total_weight
        app_weight /= total_weight

        fused = (
            smoothed["keystroke"] * keystroke_weight
            + smoothed["mouse"] * mouse_weight
            + smoothed["app"] * app_weight
        )

        return float(fused)

    def process_features(self):
        """Main loop to process incoming features from Redis."""
        logger.info("Inference Engine starting...")

        # Subscribe to feature channels
        self.pubsub.subscribe(
            "seclyzer:features:keystroke",
            "seclyzer:features:mouse",
            "seclyzer:features:app",
        )

        self._running = True
        last_app = None

        logger.info("Listening for features...")

        for message in self.pubsub.listen():
            if not self._running:
                break

            if message["type"] != "message":
                continue

            try:
                channel = message["channel"]
                data = json.loads(message["data"])

                # Check developer mode
                is_dev_mode = self.dev_mode.is_active() if self.dev_mode else False

                if channel == "seclyzer:features:keystroke":
                    score = self.score_keystroke_features(data)
                    self._publish_score("keystroke", score, is_dev_mode)

                elif channel == "seclyzer:features:mouse":
                    score = self.score_mouse_features(data)
                    self._publish_score("mouse", score, is_dev_mode)

                elif channel == "seclyzer:features:app":
                    from_app = data.get("from_app", "")
                    to_app = data.get("to_app", "")
                    current_hour = datetime.now().hour

                    if from_app and to_app:
                        score = self.score_app_transition(
                            from_app, to_app, current_hour
                        )
                        self._publish_score("app", score, is_dev_mode)
                        last_app = to_app

                # Publish fused score
                fused = self.get_fused_score()
                self._publish_fused_score(fused, is_dev_mode)

            except json.JSONDecodeError:
                logger.warning("Invalid JSON in feature message")
            except Exception as e:
                logger.error(f"Error processing features: {e}")

    def _publish_score(self, modality: str, score: float, dev_mode: bool):
        """Publish individual modality score to Redis."""
        score_data = {
            "modality": modality,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dev_mode": dev_mode,
        }
        self.redis_client.publish(
            f"seclyzer:scores:{modality}",
            json.dumps(score_data),
        )

    def _publish_fused_score(self, score: float, dev_mode: bool):
        """Publish fused score to Redis for decision engine."""
        smoothed = self.get_smoothed_scores()
        score_data = {
            "fused_score": score,
            "keystroke_score": smoothed["keystroke"],
            "mouse_score": smoothed["mouse"],
            "app_score": smoothed["app"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dev_mode": dev_mode,
        }
        self.redis_client.publish(
            "seclyzer:scores:fused",
            json.dumps(score_data),
        )

    def stop(self):
        """Stop the inference engine."""
        self._running = False
        self.pubsub.unsubscribe()
        logger.info("Inference Engine stopped")

    def reload_models(self):
        """Reload models from disk (for hot-reloading after training)."""
        with self._lock:
            self._load_models()
        logger.info("Models reloaded")


# Global instance
_inference_engine: Optional[InferenceEngine] = None


def get_inference_engine(
    models_dir: str = "data/models",
    user_id: str = "default",
) -> InferenceEngine:
    """Get or create the global inference engine instance."""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = InferenceEngine(models_dir=models_dir, user_id=user_id)
    return _inference_engine


if __name__ == "__main__":
    engine = InferenceEngine()
    try:
        engine.process_features()
    except KeyboardInterrupt:
        engine.stop()
