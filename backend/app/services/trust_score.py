import os
import sys

import joblib
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "ml"))
from features import FEATURE_NAMES, build_features

from app.config import settings

_model = None


def _load_model():
    global _model
    if _model is None:
        path = os.path.join(os.path.dirname(__file__), "..", "..", settings.trust_model_path)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Trust model not found at {path}. Run `python ml/train_trust_model.py` first."
            )
        _model = joblib.load(path)
    return _model


def predict_trust_score(rating: float, user_ratings_total: int,
                         avg_sentiment: float, price_level: int | None) -> float:
    model = _load_model()
    feats = build_features(rating, user_ratings_total, avg_sentiment, price_level)
    feats_df = pd.DataFrame([feats], columns=FEATURE_NAMES)
    score = float(model.predict(feats_df)[0])
    return max(0.0, min(1.0, score))
