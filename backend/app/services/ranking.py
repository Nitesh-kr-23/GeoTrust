W_TRUST = 0.45
W_PROXIMITY = 0.35
W_RATING = 0.20

MAX_RELEVANT_DISTANCE_KM = 5.0  


def proximity_score(distance_km: float) -> float:
    """1.0 at 0km, linearly down to 0.0 at MAX_RELEVANT_DISTANCE_KM."""
    if distance_km <= 0:
        return 1.0
    if distance_km >= MAX_RELEVANT_DISTANCE_KM:
        return 0.0
    return 1.0 - (distance_km / MAX_RELEVANT_DISTANCE_KM)


def rank_score(trust_score: float, distance_km: float, rating: float) -> float:
    """Combines signals into a single 0.0-1.0 rank score. Higher = shown first."""
    prox = proximity_score(distance_km)
    rating_norm = max(0.0, min(1.0, rating / 5.0))
    return (W_TRUST * trust_score) + (W_PROXIMITY * prox) + (W_RATING * rating_norm)
