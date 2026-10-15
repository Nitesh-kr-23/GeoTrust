from app import models


def _seed_shop(session_local, **overrides):
    db = session_local()
    shop = models.Shop(
        place_id="test_place_001",
        name="Sharma Auto Works",
        category="car_repair",
        address="Test Road, Lucknow",
        phone_number="+91 98765 43210",
        latitude=26.8467,
        longitude=80.9462,
        h3_index="test_h3_cell",
        rating=4.2,
        user_ratings_total=50,
        price_level=2,
        business_status="OPERATIONAL",
        trust_score=0.7,
        avg_sentiment=0.4,
        **overrides,
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    db.close()
    return shop.id


def test_shop_search_result_via_shops_endpoint_includes_phone_number(client):
    test_client, session_local = client
    _seed_shop(session_local)

    resp = test_client.get("/api/shops", params={"category": "car_repair"})
    assert resp.status_code == 200
    shops = resp.json()
    assert len(shops) == 1
    assert shops[0]["name"] == "Sharma Auto Works"


def test_full_call_complete_review_lifecycle_updates_trust_score(client):
    test_client, session_local = client
    _seed_shop(session_local)

    # 1. "Call Shop" tapped: create the booking record.
    resp = test_client.post("/api/bookings", json={
        "place_id": "test_place_001",
        "category": "car_repair",
        "customer_lat": 26.85,
        "customer_lng": 80.95,
        "predicted_price_min": 765,
        "predicted_price_max": 1035,
        "predicted_eta_minutes": 25,
    })
    assert resp.status_code == 200
    booking = resp.json()
    assert booking["status"] == "REQUESTED"
    booking_id = booking["id"]

    # 2. Frontend immediately auto-accepts right after opening the tel: link.
    resp = test_client.post(f"/api/bookings/{booking_id}/accept")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"

    # 3. Customer taps "Simulate: job completed".
    resp = test_client.post(f"/api/bookings/{booking_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

    # 4. Customer submits a review.
    resp = test_client.post(f"/api/bookings/{booking_id}/review", json={
        "rating": 5,
        "text": "Fixed my brakes fast, very professional and honest about pricing.",
    })
    assert resp.status_code == 200

    # 5. Trust score for future users should now be different from the seed value.
    resp = test_client.get("/api/shops", params={"category": "car_repair"})
    shops = resp.json()
    assert shops[0]["trust_score"] != 0.7


def test_cannot_review_before_job_completed(client):
    test_client, session_local = client
    _seed_shop(session_local)

    resp = test_client.post("/api/bookings", json={
        "place_id": "test_place_001",
        "category": "car_repair",
        "customer_lat": 26.85,
        "customer_lng": 80.95,
    })
    booking_id = resp.json()["id"]

    # Skip accept/complete entirely — review should be rejected.
    resp = test_client.post(f"/api/bookings/{booking_id}/review", json={"rating": 5})
    assert resp.status_code == 409
