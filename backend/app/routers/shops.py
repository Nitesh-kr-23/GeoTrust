from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

router = APIRouter(prefix="/api/shops", tags=["shops"])


@router.get("")
def list_shops(db: Session = Depends(get_db), category: str | None = None):
    q = db.query(models.Shop)
    if category:
        q = q.filter(models.Shop.category == category)
    shops = q.all()
    return [
        {
            "place_id": s.place_id,
            "name": s.name,
            "category": s.category,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "rating": s.rating,
            "trust_score": s.trust_score,
            "user_ratings_total": s.user_ratings_total,
        }
        for s in shops
    ]
