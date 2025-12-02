"""
Inference Engine Package
Handles real-time model inference for behavioral biometrics
"""

from .inference_engine import InferenceEngine, get_inference_engine

__all__ = ["InferenceEngine", "get_inference_engine"]
