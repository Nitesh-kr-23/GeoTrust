from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.rate_limit import limiter
from app.services import sentiment, trust_score

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def _get_booking_or_404(db: Session, booking_id: int) -> models.Booking:
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return booking


@router.post("", response_model=schemas.BookingOut)
@limiter.limit("10/minute")
def create_booking(request: Request, req: schemas.BookingCreate, db: Session = Depends(get_db)):
    shop = db.query(models.Shop).filter(models.Shop.place_id == req.place_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found. Search for it first.")

    booking = models.Booking(
        shop_id=shop.id,
        category=req.category,
        customer_lat=req.customer_lat,
        customer_lng=req.customer_lng,
        status="REQUESTED",
        predicted_price_min=req.predicted_price_min,
        predicted_price_max=req.predicted_price_max,
        predicted_eta_minutes=req.predicted_eta_minutes,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=list[schemas.BookingOut])
def list_bookings(db: Session = Depends(get_db)):
    return db.query(models.Booking).order_by(models.Booking.id.desc()).limit(50).all()


@router.post("/{booking_id}/accept", response_model=schemas.BookingOut)
def accept_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = _get_booking_or_404(db, booking_id)
    if booking.status != "REQUESTED":
        raise HTTPException(status_code=409, detail=f"Cannot accept a booking in status {booking.status}.")
    booking.status = "ACCEPTED"
    booking.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/reject", response_model=schemas.BookingOut)
def reject_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = _get_booking_or_404(db, booking_id)
    if booking.status != "REQUESTED":
        raise HTTPException(status_code=409, detail=f"Cannot reject a booking in status {booking.status}.")
    booking.status = "REJECTED"
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/complete", response_model=schemas.BookingOut)
def complete_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = _get_booking_or_404(db, booking_id)
    if booking.status != "ACCEPTED":
        raise HTTPException(status_code=409, detail=f"Cannot complete a booking in status {booking.status}.")
    booking.status = "COMPLETED"
    booking.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/review", response_model=schemas.ReviewOut)
def review_booking(booking_id: int, req: schemas.ReviewCreate, db: Session = Depends(get_db)):
    booking = _get_booking_or_404(db, booking_id)
    if booking.status != "COMPLETED":
        raise HTTPException(status_code=409, detail="Can only review a completed booking.")
    if booking.customer_review is not None:
        raise HTTPException(status_code=409, detail="This booking has already been reviewed.")

    shop = db.query(models.Shop).filter(models.Shop.id == booking.shop_id).first()

    review = models.CustomerReview(
        booking_id=booking.id, shop_id=shop.id, rating=req.rating, text=req.text,
    )
    db.add(review)

    db.add(models.Review(
        shop_id=shop.id, author_name="GeoTrust customer", rating=req.rating, text=req.text,
        relative_time_description="just now",
    ))
    db.flush()

    all_review_texts = [r.text for r in shop.reviews if r.text]
    shop.avg_sentiment = sentiment.average_sentiment(all_review_texts)

    total = shop.user_ratings_total or 1
    shop.rating = ((shop.rating * total) + req.rating) / (total + 1)
    shop.user_ratings_total = total + 1

    shop.trust_score = trust_score.predict_trust_score(
        shop.rating, shop.user_ratings_total, shop.avg_sentiment, shop.price_level
    )

    db.commit()
    db.refresh(review)
    return review
