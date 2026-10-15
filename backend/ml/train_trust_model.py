import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

sys.path.append(os.path.dirname(__file__))
from features import FEATURE_NAMES, build_features

RNG = np.random.default_rng(42)
N_SAMPLES = 4000


def generate_synthetic_dataset(n=N_SAMPLES) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        rating = float(np.clip(RNG.normal(4.0, 0.7), 1.0, 5.0))
        review_count = int(np.clip(RNG.exponential(80), 1, 5000))

        base_sentiment = (rating - 3.0) / 2.0  
        sentiment = float(np.clip(base_sentiment + RNG.normal(0, 0.25), -1.0, 1.0))

        price_level = int(RNG.integers(0, 5)) if RNG.random() > 0.3 else None

        is_fake_pattern = RNG.random() < 0.08
        if is_fake_pattern:
            rating = float(np.clip(RNG.normal(4.8, 0.15), 4.3, 5.0))
            review_count = int(RNG.integers(1, 6))          
            sentiment = float(RNG.normal(0.0, 0.3))         

        trust = (
            0.35 * (rating / 5.0)
            + 0.25 * (sentiment + 1) / 2
            + 0.25 * np.tanh(review_count / 100)   
            + 0.15 * (1.0 if price_level is not None else 0.5)
        )
        if is_fake_pattern:
            trust *= 0.4  
        trust = float(np.clip(trust + RNG.normal(0, 0.03), 0.0, 1.0))

        feats = build_features(rating, review_count, sentiment, price_level)
        rows.append(feats + [trust])

    return pd.DataFrame(rows, columns=FEATURE_NAMES + ["trust_label"])


def main():
    df = generate_synthetic_dataset()
    X, y = df[FEATURE_NAMES], df["trust_label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(
        n_estimators=200, max_depth=8, min_samples_leaf=5, random_state=42
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"Validation MAE: {mae:.4f}")
    print(f"Validation R^2: {r2:.4f}")
    print("Feature importances:")
    for name, imp in sorted(zip(FEATURE_NAMES, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {name}: {imp:.3f}")

    out_path = os.path.join(os.path.dirname(__file__), "trust_model.joblib")
    joblib.dump(model, out_path)
    print(f"\nSaved model to {out_path}")


if __name__ == "__main__":
    main()
