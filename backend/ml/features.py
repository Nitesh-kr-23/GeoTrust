import math

FEATURE_NAMES = ["rating", "log_review_count", "avg_sentiment", "has_price_level"]

PRICING_FEATURE_NAMES = [
    "category_idx", "distance_km", "hour_of_day", "is_peak_hour",
    "demand_density", "nearby_shop_count",
]



def build_features(rating: float, user_ratings_total: int, avg_sentiment: float,
                    price_level: int | None) -> list[float]:
    log_review_count = math.log1p(max(user_ratings_total, 0))
    has_price_level = 1.0 if price_level is not None else 0.0
    return [rating, log_review_count, avg_sentiment, has_price_level]
