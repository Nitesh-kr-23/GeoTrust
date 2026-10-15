import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import ranking
from app.services.geospatial import haversine_km
from app.services.trust_score import predict_trust_score


def test_haversine_zero_distance():
    assert haversine_km(26.85, 80.95, 26.85, 80.95) == 0.0


def test_haversine_known_distance():
    d = haversine_km(26.8467, 80.9462, 26.4499, 80.3319)
    assert 60 < d < 100


def test_proximity_score_bounds():
    assert ranking.proximity_score(0) == 1.0
    assert ranking.proximity_score(ranking.MAX_RELEVANT_DISTANCE_KM) == 0.0
    assert ranking.proximity_score(999) == 0.0


def test_rank_score_prefers_closer_and_more_trusted():
    close_trusted = ranking.rank_score(trust_score=0.9, distance_km=0.5, rating=4.5)
    far_untrusted = ranking.rank_score(trust_score=0.2, distance_km=4.5, rating=3.0)
    assert close_trusted > far_untrusted


def test_trust_score_within_bounds():
    score = predict_trust_score(rating=4.5, user_ratings_total=200, avg_sentiment=0.6, price_level=2)
    assert 0.0 <= score <= 1.0


def test_trust_score_penalizes_suspicious_pattern():
    suspicious = predict_trust_score(rating=5.0, user_ratings_total=2, avg_sentiment=-0.1, price_level=None)
    established = predict_trust_score(rating=4.3, user_ratings_total=300, avg_sentiment=0.5, price_level=2)
    assert established > suspicious
