from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.rate_limit import limiter
from app.services import (
    geospatial,
    google_places,
    pricing,
    ranking,
    sentiment,
    trust_score,
)

router = APIRouter(prefix="/api/search", tags=["search"])

_details_cache: dict[str, dict] = {}

CACHE_FRESHNESS = timedelta(hours=6)


def _get_or_cache_shop(db: Session, place: dict, category: str) -> models.Shop:
    """Upserts a shop into the local DB cache, fetching + scoring details if new."""
    place_id = place["place_id"]
    shop = db.query(models.Shop).filter(models.Shop.place_id == place_id).first()
    if shop:
        return shop

    # New shop: fetch details (reviews) once, score sentiment + trust, persist.
    details = _details_cache.get(place_id)
    if details is None:
        details = google_places.place_details(place_id)
        _details_cache[place_id] = details

    reviews = details.get("reviews", [])
    review_texts = [r.get("text", "") for r in reviews]
    avg_sent = sentiment.average_sentiment(review_texts)

    rating = place.get("rating", 0.0) or 0.0
    ratings_total = place.get("user_ratings_total", 0) or 0
    price_level = place.get("price_level")

    trust = trust_score.predict_trust_score(rating, ratings_total, avg_sent, price_level)

    geom = place["geometry"]["location"]
    shop = models.Shop(
        place_id=place_id,
        name=place.get("name", "Unknown"),
        category=category,
        address=place.get("vicinity") or details.get("formatted_address"),
        phone_number=details.get("phone_number"),
        latitude=geom["lat"],
        longitude=geom["lng"],
        h3_index=geospatial.latlng_to_h3(geom["lat"], geom["lng"]),
        rating=rating,
        user_ratings_total=ratings_total,
        price_level=price_level,
        business_status=place.get("business_status", "OPERATIONAL"),
        trust_score=trust,
        avg_sentiment=avg_sent,
        last_synced_at=datetime.now(timezone.utc),
    )
    db.add(shop)
    db.flush()  

    for r in reviews:
        db.add(models.Review(
            shop_id=shop.id,
            author_name=r.get("author_name"),
            rating=r.get("rating"),
            text=r.get("text"),
            relative_time_description=r.get("relative_time_description"),
        ))

    return shop


def _cached_candidates(db: Session, lat: float, lng: float, category: str) -> list[models.Shop]:
    cells = geospatial.nearby_h3_cells(lat, lng)
    cutoff = datetime.now(timezone.utc) - CACHE_FRESHNESS
    return (
        db.query(models.Shop)
        .filter(
            models.Shop.h3_index.in_(cells),
            models.Shop.category == category,
            models.Shop.last_synced_at >= cutoff,
            models.Shop.business_status == "OPERATIONAL",
        )
        .all()
    )


def _demand_density(db: Session, lat: float, lng: float, category: str) -> float:
    cells = geospatial.nearby_h3_cells(lat, lng)
    window_start = datetime.now(timezone.utc) - timedelta(hours=1)
    count = (
        db.query(models.SearchLog)
        .filter(
            models.SearchLog.h3_index.in_(cells),
            models.SearchLog.category == category,
            models.SearchLog.created_at >= window_start,
        )
        .count()
    )
    return float(count)


@router.post("", response_model=list[schemas.ShopResult])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def search_shops(request: Request, req: schemas.SearchRequest, db: Session = Depends(get_db)):
    radius = req.radius_m or settings.default_search_radius_m
    
    category = req.query.lower()
    user_h3 = geospatial.latlng_to_h3(req.latitude, req.longitude)

    cache_hit_shops = _cached_candidates(db, req.latitude, req.longitude, category)

    if cache_hit_shops:
        shops = cache_hit_shops
    else:
        try:
            places = google_places.text_search(req.query, req.latitude, req.longitude, radius)
        except google_places.GooglePlacesError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

        shops = []
        for place in places:
            if place.get("business_status") not in (None, "OPERATIONAL"):
                continue  
            shops.append(_get_or_cache_shop(db, place, category))

    db.add(models.SearchLog(
        category=category, latitude=req.latitude, longitude=req.longitude,
        h3_index=user_h3, results_count=len(shops),
    ))
    db.commit()

    if not shops:
        return []

    demand_density = _demand_density(db, req.latitude, req.longitude, category)
    nearby_shop_count = len(shops)

    results = []
    for shop in shops:
        dist_km = geospatial.haversine_km(req.latitude, req.longitude, shop.latitude, shop.longitude)
        score = ranking.rank_score(shop.trust_score or 0.0, dist_km, shop.rating or 0.0)
        price_eta = pricing.predict_price_and_eta(
            category=category, distance_km=dist_km,
            demand_density=demand_density, nearby_shop_count=nearby_shop_count,
        )

        results.append(schemas.ShopResult(
            place_id=shop.place_id,
            name=shop.name,
            category=shop.category,
            address=shop.address,
            phone_number=shop.phone_number,
            latitude=shop.latitude,
            longitude=shop.longitude,
            rating=shop.rating,
            user_ratings_total=shop.user_ratings_total,
            price_level=shop.price_level,
            distance_km=round(dist_km, 2),
            trust_score=round(shop.trust_score or 0.0, 3),
            avg_sentiment=round(shop.avg_sentiment or 0.0, 3),
            rank_score=round(score, 3),
            predicted_price_min=price_eta["price_min"],
            predicted_price_max=price_eta["price_max"],
            predicted_eta_minutes=price_eta["eta_minutes"],
        ))

    results.sort(key=lambda r: r.rank_score, reverse=True)
    return results[: settings.max_results_returned]
