import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.logging_config import configure_logging
from app.rate_limit import limiter
from app.routers import bookings, search, shops

configure_logging()
logger = logging.getLogger("geotrust")

if settings.environment == "development":
    Base.metadata.create_all(bind=engine)
else:
    logger.info("environment=production — skipping auto-create; run `alembic upgrade head` before deploy.")

app = FastAPI(
    title="GeoTrust API",
    description="ML-powered hyperlocal shop aggregator",
    version="0.2.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if settings.is_production and not settings.cors_origins_list:
    logger.warning(
        "environment=production but CORS_ALLOWED_ORIGINS is empty — "
        "no browser origin will be able to call this API. Set it in your "
        "hosting provider's environment variables."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

MAX_BODY_BYTES = 20_000  


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info("validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"detail": "Invalid request."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled error on %s", request.url.path)
    if settings.is_production:
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})
    raise exc  


app.include_router(search.router)
app.include_router(bookings.router)
app.include_router(shops.router)


@app.get("/api/health")
def health():
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        logger.exception("health check: database is unreachable")
        db_ok = False

    status = "ok" if db_ok else "degraded"
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={"status": status, "database": "ok" if db_ok else "unreachable"},
    )
