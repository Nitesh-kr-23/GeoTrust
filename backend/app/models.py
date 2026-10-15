from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    place_id = Column(String, unique=True, index=True, nullable=False)  
    name = Column(String, nullable=False)
    category = Column(String, index=True, nullable=False)  
    address = Column(String)
    phone_number = Column(String, nullable=True)  
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    h3_index = Column(String, index=True, nullable=True)  
    rating = Column(Float, default=0.0)
    user_ratings_total = Column(Integer, default=0)
    price_level = Column(Integer, nullable=True)  
    business_status = Column(String, default="OPERATIONAL")

    # --- Derived / ML fields ---
    trust_score = Column(Float, nullable=True)       
    avg_sentiment = Column(Float, nullable=True)      
    last_synced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    reviews = relationship("Review", back_populates="shop", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="shop", cascade="all, delete-orphan")


class Review(Base):
    """Cached review text pulled from Google Place Details, used as trust-model input."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    author_name = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)
    text = Column(Text, nullable=True)
    relative_time_description = Column(String, nullable=True)

    shop = relationship("Shop", back_populates="reviews")


class Booking(Base):
    """
    A booked service request, tracked through the full lifecycle shown in
    the product workflow:
        REQUESTED -> ACCEPTED (by shop) -> COMPLETED -> reviewed
                  -> REJECTED (by shop)
                  -> CANCELLED (by customer, only while REQUESTED/ACCEPTED)
    Also doubles as the demand signal for the analytics layer, and — once
    reviewed — as the source of the next trust-score recompute for its shop.
    """
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    category = Column(String, nullable=False)
    customer_lat = Column(Float, nullable=False)
    customer_lng = Column(Float, nullable=False)
    status = Column(String, default="REQUESTED")  

    predicted_price_min = Column(Float, nullable=True)
    predicted_price_max = Column(Float, nullable=True)
    predicted_eta_minutes = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    shop = relationship("Shop", back_populates="bookings")
    customer_review = relationship("CustomerReview", back_populates="booking",
                                    uselist=False, cascade="all, delete-orphan")


class CustomerReview(Base):
    __tablename__ = "customer_reviews"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    booking = relationship("Booking", back_populates="customer_review")


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    h3_index = Column(String, index=True, nullable=True) 
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
