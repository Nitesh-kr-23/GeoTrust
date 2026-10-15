import os
import sys

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

sys.path.append(os.path.dirname(__file__))
from features import PRICING_FEATURE_NAMES

RNG = np.random.default_rng(7)
N_SAMPLES = 6000

CATEGORY_BASE_PRICE = {
    "car_repair": 900,
    "electrician": 350,
    "plumber": 400,
    "locksmith": 500,
    "appliance_repair": 600,
}
CATEGORIES = list(CATEGORY_BASE_PRICE.keys())


def generate_synthetic_dataset(n=N_SAMPLES) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        category = RNG.choice(CATEGORIES)
        base_price = CATEGORY_BASE_PRICE[category]

        distance_km = float(np.clip(RNG.exponential(2.0), 0.1, 5.0))
        hour_of_day = int(RNG.integers(0, 24))
        demand_density = float(np.clip(RNG.exponential(3.0), 0, 20))
        nearby_shop_count = int(RNG.integers(1, 15))  

        is_peak_hour = 1.0 if hour_of_day in (8, 9, 18, 19, 20) else 0.0

        # --- price target ---
        price = base_price
        price *= 1 + 0.15 * is_peak_hour
        price *= 1 + 0.03 * demand_density
        price *= 1 - 0.015 * nearby_shop_count  
        price *= 1 + RNG.normal(0, 0.08)  
        price = max(base_price * 0.5, price)

        # --- ETA target (minutes) ---
        eta = 12 + 6 * distance_km
        eta *= 1 + 0.25 * is_peak_hour
        eta *= 1 + 0.04 * demand_density
        eta *= 1 - 0.02 * nearby_shop_count
        eta *= 1 + RNG.normal(0, 0.10)
        eta = max(8.0, eta)

        cat_idx = CATEGORIES.index(category)
        rows.append([cat_idx, distance_km, hour_of_day, is_peak_hour,
                     demand_density, nearby_shop_count, price, eta])

    cols = PRICING_FEATURE_NAMES + ["price_label", "eta_label"]
    return pd.DataFrame(rows, columns=cols)


def main():
    df = generate_synthetic_dataset()
    X = df[PRICING_FEATURE_NAMES]

    X_train, X_test, yprice_train, yprice_test = train_test_split(
        X, df["price_label"], test_size=0.2, random_state=7
    )
    _, _, yeta_train, yeta_test = train_test_split(
        X, df["eta_label"], test_size=0.2, random_state=7
    )

    price_model = LGBMRegressor(n_estimators=150, max_depth=6, verbose=-1, random_state=7)
    price_model.fit(X_train, yprice_train)
    price_preds = price_model.predict(X_test)
    print(f"Price MAE: Rs. {mean_absolute_error(yprice_test, price_preds):.2f}")

    eta_model = LGBMRegressor(n_estimators=150, max_depth=6, verbose=-1, random_state=7)
    eta_model.fit(X_train, yeta_train)
    eta_preds = eta_model.predict(X_test)
    print(f"ETA MAE: {mean_absolute_error(yeta_test, eta_preds):.2f} minutes")

    out_dir = os.path.dirname(__file__)
    joblib.dump(price_model, os.path.join(out_dir, "price_model.joblib"))
    joblib.dump(eta_model, os.path.join(out_dir, "eta_model.joblib"))
    print(f"\nSaved models to {out_dir}/price_model.joblib and eta_model.joblib")


if __name__ == "__main__":
    main()
