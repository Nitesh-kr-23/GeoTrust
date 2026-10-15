from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    query: str = Field(..., min_length=2, max_length=100)
    radius_m: int | None = Field(default=None, ge=500, le=15000)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query cannot be blank")
        return v


class ShopResult(BaseModel):
    place_id: str
    name: str
    category: str
    address: str | None = None
    phone_number: str | None = None  
    latitude: float
    longitude: float
    rating: float
    user_ratings_total: int
    price_level: int | None = None
    distance_km: float
    trust_score: float
    avg_sentiment: float | None = None
    rank_score: float
    predicted_price_min: float
    predicted_price_max: float
    predicted_eta_minutes: float

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    place_id: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    customer_lat: float = Field(..., ge=-90, le=90)
    customer_lng: float = Field(..., ge=-180, le=180)
    predicted_price_min: float | None = Field(default=None, ge=0)
    predicted_price_max: float | None = Field(default=None, ge=0)
    predicted_eta_minutes: float | None = Field(default=None, ge=0)


class BookingOut(BaseModel):
    id: int
    shop_id: int
    category: str
    status: str
    predicted_price_min: float | None = None
    predicted_price_max: float | None = None
    predicted_eta_minutes: float | None = None
    created_at: datetime
    accepted_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    text: str | None = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    id: int
    booking_id: int
    shop_id: int
    rating: int
    text: str | None = None

    class Config:
        from_attributes = True
