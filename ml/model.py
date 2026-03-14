"""
ML model for predicting user level (novice / basic / advanced).
Loads a trained scikit-learn model from disk; falls back to rule-based logic
if the model file does not exist.
"""

import pickle
from pathlib import Path

from ml.features import FEATURE_COLUMNS

MODEL_PATH = Path(__file__).parent / "models" / "level_predictor.pkl"
LEVELS = ["novice", "basic", "advanced"]


class LevelPredictor:
    def __init__(self):
        self.model = None
        self.load()

    def load(self):
        if MODEL_PATH.exists():
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)

    def predict(self, features: dict) -> dict:
        """
        Predict user level from feature dict.

        Returns:
            {
                "level": "novice" | "basic" | "advanced",
                "confidence": float,          # max class probability
                "probabilities": {level: float, ...},
                "method": "ml" | "rule-based"
            }
        """
        if self.model is not None:
            try:
                import numpy as np
                X = self._features_to_array(features)
                pred = self.model.predict(X)[0]
                proba = self.model.predict_proba(X)[0]
                level = LEVELS[int(pred)]
                return {
                    "level": level,
                    "confidence": float(max(proba)),
                    "probabilities": {
                        LEVELS[i]: float(proba[i]) for i in range(len(LEVELS))
                    },
                    "method": "ml",
                }
            except Exception:
                pass

        return self._rule_based(features)

    def _features_to_array(self, features: dict):
        import numpy as np
        return np.array([[features.get(col, 0.0) for col in FEATURE_COLUMNS]])

    def _rule_based(self, features: dict) -> dict:
        score = features.get("onboarding_score", 0.0)
        if score >= 0.7:
            level = "advanced"
        elif score >= 0.4:
            level = "basic"
        else:
            level = "novice"
        return {
            "level": level,
            "confidence": 0.5,
            "probabilities": {
                "novice": 1.0 if level == "novice" else 0.0,
                "basic": 1.0 if level == "basic" else 0.0,
                "advanced": 1.0 if level == "advanced" else 0.0,
            },
            "method": "rule-based",
        }
