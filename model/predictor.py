"""
Random Forest inference predictor module for SmartCompress AI.
Provides class confidence estimation, ranked probabilities, and graceful failure handling.
"""

import sys
import types
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows WDAC compatibility: stub unused _libsvm_sparse if blocked by policy
if "sklearn.svm._libsvm_sparse" not in sys.modules:
    sys.modules["sklearn.svm._libsvm_sparse"] = types.ModuleType("sklearn.svm._libsvm_sparse")

import joblib
import pandas as pd

from config import Config


class MLPredictor:
    """Random Forest compression recommendation predictor."""

    def __init__(self, model_path: Path = Config.MODEL_PATH):
        self.model_path = Path(model_path)
        self.pipeline = None
        self.metadata = None
        self._load_model()

    def _load_model(self):
        """Safely load serialized pipeline if available."""
        if self.model_path.exists():
            try:
                data = joblib.load(self.model_path)
                self.pipeline = data.get("pipeline")
                self.metadata = data.get("metadata", {})
            except Exception as e:
                print(f"[MLPredictor] Warning: Error loading model from {self.model_path}: {e}")
                self.pipeline = None
                self.metadata = None

    def is_available(self) -> bool:
        """Check if trained model pipeline is currently loaded and ready."""
        return self.pipeline is not None

    def predict(
        self,
        file_size: int,
        entropy: float,
        category: str,
        extension: str,
        preference: str = "balanced"
    ) -> Optional[Dict[str, Any]]:
        """
        Predict the optimal compression algorithm using the trained Random Forest classifier.

        Returns:
            Dict containing recommended algorithm, confidence score (0-1), and class probabilities,
            or None if the model is unavailable.
        """
        if not self.is_available():
            self._load_model()
            if not self.is_available():
                return None

        # Build feature dataframe
        input_df = pd.DataFrame([{
            "file_size": file_size,
            "entropy": entropy,
            "category": category,
            "extension": extension.lower() if extension else "none",
            "preference": preference.lower()
        }])

        try:
            # Predict class
            prediction = self.pipeline.predict(input_df)[0]
            
            # Predict class probabilities (confidence)
            classes = self.pipeline.named_steps["classifier"].classes_
            probabilities = self.pipeline.predict_proba(input_df)[0]

            prob_dict = {cls: round(float(prob), 4) for cls, prob in zip(classes, probabilities)}
            confidence = float(max(probabilities))

            return {
                "recommended_algorithm": prediction,
                "confidence": round(confidence, 4),
                "confidence_pct": round(confidence * 100, 1),
                "probabilities": prob_dict,
                "model_accuracy": self.metadata.get("test_accuracy") if self.metadata else None
            }
        except Exception as e:
            print(f"[MLPredictor] Prediction failure: {e}")
            return None


# Global predictor instance
ml_predictor = MLPredictor()
