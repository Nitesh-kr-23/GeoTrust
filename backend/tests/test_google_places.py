import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import google_places

google_places.settings.google_places_api_key = "test_key_for_ci"


def test_text_search_builds_correct_request_and_parses_response():
    fake_response = {
        "places": [
            {
                "id": "ChIJ_mock_electrician",
                "displayName": {"text": "Mock Electrical Works"},
                "formattedAddress": "Mock Street, Lucknow",
                "location": {"latitude": 26.85, "longitude": 80.95},
                "rating": 4.4,
                "userRatingCount": 30,
                "priceLevel": "PRICE_LEVEL_MODERATE",
                "businessStatus": "OPERATIONAL",
            }
        ]
    }

    with patch("app.services.google_places.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_response
        mock_post.return_value = mock_resp

        results = google_places.text_search("electrician", 26.85, 80.95, 4000)

    assert len(results) == 1
    place = results[0]
    assert place["place_id"] == "ChIJ_mock_electrician"
    assert place["geometry"]["location"] == {"lat": 26.85, "lng": 80.95}
    assert place["price_level"] == 2  

    call = mock_post.call_args
    assert call.args[0] == "https://places.googleapis.com/v1/places:searchText"
    assert call.kwargs["json"]["textQuery"] == "electrician"
    assert "locationBias" in call.kwargs["json"]
    assert "locationRestriction" not in call.kwargs["json"]


def test_text_search_handles_zero_results():
    with patch("app.services.google_places.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}  # no "places" key
        mock_post.return_value = mock_resp

        results = google_places.text_search("extremely obscure trade", 26.85, 80.95, 4000)

    assert results == []


def test_search_endpoint_uses_text_search_for_electrician_plumber_locksmith(client):
    from app.services import google_places
    google_places.settings.google_places_api_key = "test_key_for_ci"

    test_client, _ = client

    for i, query in enumerate(["electrician", "plumber", "locksmith"]):
        fake_response = {
            "places": [
                {
                    "id": f"ChIJ_mock_{query}_{i}",
                    "displayName": {"text": f"Mock {query.title()} Shop"},
                    "formattedAddress": "Mock Street, Lucknow",
                    "location": {"latitude": 26.85, "longitude": 80.95},
                    "rating": 4.0,
                    "userRatingCount": 25,
                    "priceLevel": "PRICE_LEVEL_MODERATE",
                    "businessStatus": "OPERATIONAL",
                }
            ]
        }
        fake_details = {"formattedAddress": "Mock Street", "reviews": []}

        with patch("app.services.google_places.requests.post") as mock_post, \
             patch("app.services.google_places.requests.get") as mock_get:
            mock_post_resp = MagicMock()
            mock_post_resp.status_code = 200
            mock_post_resp.json.return_value = fake_response
            mock_post.return_value = mock_post_resp

            mock_get_resp = MagicMock()
            mock_get_resp.status_code = 200
            mock_get_resp.json.return_value = fake_details
            mock_get.return_value = mock_get_resp

            resp = test_client.post("/api/search", json={
                "latitude": 26.85, "longitude": 80.95, "query": query,
            })

        assert resp.status_code == 200, f"{query} search failed: {resp.text}"
        results = resp.json()
        assert len(results) == 1
        assert results[0]["name"] == f"Mock {query.title()} Shop"
        # Confirms Text Search was called with the raw query, not forced
        # through Nearby Search's includedTypes.
        assert mock_post.call_args.kwargs["json"]["textQuery"] == query
        assert "searchText" in mock_post.call_args.args[0]



    fake_response = {
        "places": [
            {
                "id": "ChIJ_mock_1",
                "displayName": {"text": "Mock Auto Garage"},
                "formattedAddress": "Mock Street, Lucknow",
                "location": {"latitude": 26.85, "longitude": 80.95},
                "rating": 4.1,
                "userRatingCount": 42,
                "priceLevel": "PRICE_LEVEL_INEXPENSIVE",
                "businessStatus": "OPERATIONAL",
            }
        ]
    }

    with patch("app.services.google_places.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_response
        mock_post.return_value = mock_resp

        results = google_places.nearby_search(26.85, 80.95, "car_repair", 4000)

    assert len(results) == 1
    place = results[0]
    assert place["place_id"] == "ChIJ_mock_1"
    assert place["geometry"]["location"] == {"lat": 26.85, "lng": 80.95}
    assert place["price_level"] == 1  # PRICE_LEVEL_INEXPENSIVE -> 1
    assert place["user_ratings_total"] == 42
    assert place["business_status"] == "OPERATIONAL"

    call = mock_post.call_args
    assert call.args[0] == "https://places.googleapis.com/v1/places:searchNearby"
    assert call.kwargs["json"]["includedTypes"] == ["car_repair"]
    assert "X-Goog-Api-Key" in call.kwargs["headers"]
    assert "X-Goog-FieldMask" in call.kwargs["headers"]


def test_place_details_parses_reviews():
    fake_response = {
        "formattedAddress": "123 Test Road",
        "reviews": [
            {
                "authorAttribution": {"displayName": "Rohit K."},
                "rating": 5,
                "text": {"text": "Great and honest service."},
                "relativePublishTimeDescription": "2 weeks ago",
            }
        ],
    }

    with patch("app.services.google_places.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_response
        mock_get.return_value = mock_resp

        details = google_places.place_details("ChIJ_mock_1")

    assert details["formatted_address"] == "123 Test Road"
    assert len(details["reviews"]) == 1
    assert details["reviews"][0]["text"] == "Great and honest service."
    assert details["reviews"][0]["author_name"] == "Rohit K."


def test_request_denied_raises_google_places_error():
    with patch("app.services.google_places.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {
            "error": {"message": "You're calling a legacy API, which is not enabled for your project."}
        }
        mock_post.return_value = mock_resp

        try:
            google_places.nearby_search(26.85, 80.95, "car_repair", 4000)
            raise AssertionError("Expected GooglePlacesError to be raised")
        except google_places.GooglePlacesError as e:
            assert "legacy API" in str(e)

    # A permanent denial should NOT be retried — only 1 attempt.
    assert mock_post.call_count == 1


def test_transient_5xx_is_retried_then_succeeds():
    fail_resp = MagicMock()
    fail_resp.status_code = 503
    fail_resp.json.return_value = {"error": {"message": "backend unavailable"}}

    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.json.return_value = {"places": []}

    with patch("app.services.google_places.requests.post") as mock_post:
        mock_post.side_effect = [fail_resp, fail_resp, success_resp]
        results = google_places.nearby_search(26.85, 80.95, "car_repair", 4000)

    assert results == []
    assert mock_post.call_count == 3


def test_transient_error_exhausts_retries_and_raises():
    fail_resp = MagicMock()
    fail_resp.status_code = 429
    fail_resp.json.return_value = {"error": {"message": "quota exceeded"}}

    with patch("app.services.google_places.requests.post") as mock_post:
        mock_post.return_value = fail_resp
        try:
            google_places.nearby_search(26.85, 80.95, "car_repair", 4000)
            raise AssertionError("Expected GooglePlacesTransientError to be raised")
        except google_places.GooglePlacesTransientError:
            pass

    assert mock_post.call_count == 3 
