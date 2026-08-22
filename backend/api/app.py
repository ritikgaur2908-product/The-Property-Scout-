import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.db.connection import init_db
from backend.api.routes import session, properties, bookings, notifications
from backend.api.middleware.rate_limiter import RateLimitMiddleware
from backend.voice.streaming import router as voice_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("property-scout-api")

app = FastAPI(
    title=settings.APP_NAME,
    description="Conversational Real Estate Voice Bot API for Bengaluru properties",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — locked to frontend origin in production ─────────────────────────
_raw_origins = os.getenv("FRONTEND_URL", "http://localhost:5173,https://the-property-scout-two.vercel.app")
ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]
if "https://the-property-scout-two.vercel.app" not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append("https://the-property-scout-two.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-IP-Limit", "X-RateLimit-Ses-Limit", "Retry-After"],
    max_age=600,
)

# ── Rate limiting ───────────────────────────────────────────────────────────
app.add_middleware(RateLimitMiddleware)


@app.on_event("startup")
async def startup_event():
    """Initialize the relational database tables on API startup."""
    logger.info("Starting up The Property Scout API...")
    logger.info("CORS allowed origins: %s", ALLOWED_ORIGINS)
    try:
        init_db()
        logger.info("Database tables initialized.")
    except Exception as e:
        logger.error("Relational database table setup failed: %s", e)


# ── Route registration ──────────────────────────────────────────────────────
app.include_router(session.router,        prefix="/api/session")
app.include_router(properties.router,     prefix="/api/properties")
app.include_router(bookings.router,       prefix="/api/bookings")
app.include_router(notifications.router,  prefix="/api/notify")
app.include_router(voice_router,          prefix="/api/voice")


@app.get("/api/health", tags=["System"])
async def health_check():
    """Liveness probe — returns 200 when the API is running."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "debug_mode": settings.DEBUG,
        "cors_origins": ALLOWED_ORIGINS,
    }
