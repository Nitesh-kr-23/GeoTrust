# GeoTrust — ML-Powered Hyperlocal Shop Aggregator
An Offline-to-Online (O2O) marketplace that indexes existing shops 
(already listed on Google Maps) instead of onboarding freelancers.

GeoTrust is an ML-powered hyperlocal service discovery platform that helps customers find reliable nearby shops and service providers. It combines Google Places, geospatial search, machine learning, sentiment analysis, and trust-based ranking to recommend suitable local businesses.

## Key Features

- Free-text search for local services
- Location-based nearby shop discovery
- Google Places API (New) integration
- H3-based geospatial caching
- Random Forest trust-score model
- LightGBM price and ETA estimation
- Trust/proximity/rating-based shop ranking
- Direct **Call Shop** action
- Customer review and trust-score update workflow
- Streamlit analytics dashboard

**No in-app booking or shop-side app** — this connects the customer
directly to the shop's real phone number pulled from Google Places, the
same way they'd find and call any listing on Google Maps today. The app's
value is entirely in the ranking/trust/price-estimate step *before* the
call, not in brokering the job itself. "Job completed" and the review
that follows are simulated via a button in the customer UI.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI |
| Database | SQLAlchemy + PostgreSQL |
| Geospatial | H3 |
| Places | Google Places API (New) |
| ML | Scikit-learn, LightGBM |
| Sentiment | VADER |
| Analytics | Streamlit |
| Migrations | Alembic |
| Deployment | Render |
| Containerization | Docker |

## Product workflow (implemented end-to-end)

```
Customer opens app → Types what they need → Location detected
        │
        ▼
Google Places API fetches nearby shops  (cached via H3 grid lookup —
        │                                 falls back to a live API call
        │                                 on a cache miss)
        ▼
ML Trust Score checks shop reliability   (Random Forest)
        │
        ▼
ML Ranking chooses best shops            (weighted formula)
        │
        ▼
ML predicts price and arrival time       (LightGBM)
        │
        ▼
Customer taps "Call Shop"  →  Phone dialer opens with the shop's real
        │                      number (from Google Places)  →  Job completed
        ▼
Customer gives review  →  Trust score updates for future users
```

## Running locally (no Docker)

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your real GOOGLE_PLACES_API_KEY into .env
python ml/train_trust_model.py     # regenerates trust_model.joblib (already included)
python ml/train_pricing_model.py   # regenerates price/eta models (already included)
uvicorn app.main:app --reload      # → http://127.0.0.1:8000

# 2. Frontend (separate terminal)
cd frontend
python -m http.server 5500       # → http://127.0.0.1:5500

# 3. Analytics dashboard (separate terminal, after you've run a few searches)
cd backend && source .venv/bin/activate
pip install -r ../analytics/requirements.txt
streamlit run ../analytics/dashboard.py
```

## Running with Docker Compose

```bash
export GOOGLE_PLACES_API_KEY=your_key_here
docker compose up --build
# backend:   http://localhost:8000
# frontend:  http://localhost:5500
# analytics: http://localhost:8501
```