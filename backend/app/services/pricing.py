import os
import sys
from datetime import datetime, timezone

import joblib
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "ml"))
from features import PRICING_FEATURE_NAMES
from train_pricing_model import CATEGORIES

from app.config import settings

_price_model = None
_eta_model = None

PEAK_HOURS = {8, 9, 18, 19, 20}


def _load_models():
    global _price_model, _eta_model
    if _price_model is None or _eta_model is None:
        base = os.path.join(os.path.dirname(__file__), "..", "..", settings.pricing_model_dir)
        price_path = os.path.join(base, "price_model.joblib")
        eta_path = os.path.join(base, "eta_model.joblib")
        if not (os.path.exists(price_path) and os.path.exists(eta_path)):
            raise FileNotFoundError(
                f"Pricing/ETA models not found in {base}. Run `python ml/train_pricing_model.py` first."
            )
        _price_model = joblib.load(price_path)
        _eta_model = joblib.load(eta_path)
    return _price_model, _eta_model


def predict_price_and_eta(category: str, distance_km: float, demand_density: float,
                           nearby_shop_count: int) -> dict:
    price_model, eta_model = _load_models()

    hour_of_day = datetime.now(timezone.utc).hour
    is_peak_hour = 1.0 if hour_of_day in PEAK_HOURS else 0.0
    category_idx = CATEGORIES.index(category) if category in CATEGORIES else 0

    feats = pd.DataFrame(
        [[category_idx, distance_km, hour_of_day, is_peak_hour, demand_density, nearby_shop_count]],
        columns=PRICING_FEATURE_NAMES,
    )

    price = float(price_model.predict(feats)[0])
    eta = float(eta_model.predict(feats)[0])

    band = 0.15  # +/- 15% uncertainty band around the point estimate
    return {
        "price_min": round(max(0.0, price * (1 - band)), 2),
        "price_max": round(price * (1 + band), 2),
        "eta_minutes": round(max(5.0, eta), 1),
    }
