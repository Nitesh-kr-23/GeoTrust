import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.geospatial import latlng_to_h3, nearby_h3_cells
from app.services.pricing import predict_price_and_eta


def test_same_point_same_h3_cell():
    a = latlng_to_h3(26.8467, 80.9462)
    b = latlng_to_h3(26.8467, 80.9462)
    assert a == b


def test_nearby_points_share_or_neighbor_h3_cell():
    center_cell = latlng_to_h3(26.8467, 80.9462)
    nearby_cell = latlng_to_h3(26.8485, 80.9462)
    neighbors = nearby_h3_cells(26.8467, 80.9462)
    assert nearby_cell in neighbors or nearby_cell == center_cell


def test_nearby_h3_cells_includes_self():
    lat, lng = 26.8467, 80.9462
    cells = nearby_h3_cells(lat, lng)
    assert latlng_to_h3(lat, lng) in cells
    assert len(cells) == 7 


def test_price_and_eta_within_sane_bounds():
    result = predict_price_and_eta(
        category="plumber", distance_km=2.0, demand_density=3.0, nearby_shop_count=5
    )
    assert result["price_min"] < result["price_max"]
    assert result["price_min"] > 0
    assert result["eta_minutes"] >= 5.0


def test_higher_demand_density_raises_price():
    low_demand = predict_price_and_eta(
        category="electrician", distance_km=1.5, demand_density=0.0, nearby_shop_count=8
    )
    high_demand = predict_price_and_eta(
        category="electrician", distance_km=1.5, demand_density=15.0, nearby_shop_count=8
    )
    assert high_demand["price_min"] >= low_demand["price_min"]
