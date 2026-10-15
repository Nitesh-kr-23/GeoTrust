import logging

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger("geotrust.google_places")

_PRICE_LEVEL_MAP = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
    "PRICE_LEVEL_UNSPECIFIED": None,
}


class GooglePlacesError(Exception):
    """Non-retryable failure: bad key, malformed request, permanent denial."""


class GooglePlacesTransientError(GooglePlacesError):
    """Retryable failure: network error, Google 5xx, or 429 rate limit."""


_retry_policy = retry(
    retry=retry_if_exception_type((GooglePlacesTransientError, requests.exceptions.RequestException)),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)


def _headers(field_mask: str) -> dict:
    if not settings.google_places_api_key:
        raise GooglePlacesError(
            "GOOGLE_PLACES_API_KEY is not set. Add it to backend/.env"
        )
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_places_api_key,
        "X-Goog-FieldMask": field_mask,
    }


def _raise_for_status(resp: requests.Response) -> None:
    if resp.status_code == 200:
        return
    try:
        message = resp.json().get("error", {}).get("message", resp.text)
    except ValueError:
        message = resp.text

    if resp.status_code == 429 or resp.status_code >= 500:
        logger.warning("transient Google Places error (%s): %s", resp.status_code, message)
        raise GooglePlacesTransientError(f"Google Places error: {message}")

    logger.error("Google Places error (%s): %s", resp.status_code, message)
    raise GooglePlacesError(f"Google Places error: {message}")


def _normalize_place(p: dict) -> dict:
    location = p.get("location", {})
    return {
        "place_id": p.get("id"),
        "name": (p.get("displayName") or {}).get("text", "Unknown"),
        "vicinity": p.get("formattedAddress"),
        "geometry": {"location": {"lat": location.get("latitude"), "lng": location.get("longitude")}},
        "rating": p.get("rating", 0.0) or 0.0,
        "user_ratings_total": p.get("userRatingCount", 0) or 0,
        "price_level": _PRICE_LEVEL_MAP.get(p.get("priceLevel"), None),
        "business_status": p.get("businessStatus", "OPERATIONAL"),
    }


def _normalize_review(r: dict) -> dict:
    return {
        "author_name": (r.get("authorAttribution") or {}).get("displayName"),
        "rating": r.get("rating"),
        "text": (r.get("text") or {}).get("text", ""),
        "relative_time_description": r.get("relativePublishTimeDescription"),
    }


@_retry_policy
def text_search(query: str, lat: float, lng: float, radius_m: int) -> list[dict]:
    url = f"{settings.google_places_base_url}/places:searchText"
    field_mask = (
        "places.id,places.displayName,places.formattedAddress,places.location,"
        "places.rating,places.userRatingCount,places.priceLevel,places.businessStatus"
    )
    body = {
        "textQuery": query,
        "maxResultCount": 20,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius_m),
            }
        },
    }
    resp = requests.post(url, json=body, headers=_headers(field_mask), timeout=10)
    _raise_for_status(resp)

    data = resp.json()
    return [_normalize_place(p) for p in data.get("places", [])]


@_retry_policy
def nearby_search(lat: float, lng: float, category: str, radius_m: int) -> list[dict]:
    url = f"{settings.google_places_base_url}/places:searchNearby"
    field_mask = (
        "places.id,places.displayName,places.formattedAddress,places.location,"
        "places.rating,places.userRatingCount,places.priceLevel,places.businessStatus"
    )
    body = {
        "includedTypes": [category],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius_m),
            }
        },
    }
    resp = requests.post(url, json=body, headers=_headers(field_mask), timeout=10)
    _raise_for_status(resp)

    data = resp.json()
    return [_normalize_place(p) for p in data.get("places", [])]


@_retry_policy
def place_details(place_id: str) -> dict:
    url = f"{settings.google_places_base_url}/places/{place_id}"
    field_mask = (
        "id,displayName,formattedAddress,location,rating,userRatingCount,"
        "priceLevel,businessStatus,reviews,nationalPhoneNumber,internationalPhoneNumber"
    )
    resp = requests.get(url, headers=_headers(field_mask), timeout=10)
    _raise_for_status(resp)

    data = resp.json()
    return {
        "formatted_address": data.get("formattedAddress"),
        "phone_number": data.get("internationalPhoneNumber") or data.get("nationalPhoneNumber"),
        "reviews": [_normalize_review(r) for r in data.get("reviews", [])],
    }
