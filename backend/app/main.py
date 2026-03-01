from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import SlowAPILimiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import time

from app.api.routes import router as main_router
from app.api.auth_routes import router as auth_router
from app.api.itinerary_routes import router as itinerary_router
from app.api.agent_routes import router as agent_router
from app.api.auto_research_routes import router as auto_research_router
from app.api.websocket_routes import router as websocket_router
from app.api.city_routes import router as city_router
from app.api.travelgenie_routes import router as travelgenie_router
from app.api.travel_chat_routes import router as travel_chat_router
from app.api.suggestions_routes import router as suggestions_router
from app.api.tripadvisor_routes import router as tripadvisor_router
from app.database.connection import engine
from app.database.models import Base
from app.config import get_settings
from app.utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(log_format="console")  # Use "json" for production
logger = get_logger(__name__)

# Rate limiter
limiter = SlowAPILimiter(key_func=get_remote_address)

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting TravelAI API")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield
    # Shutdown
    logger.info("Shutting down TravelAI API")

settings = get_settings()

app = FastAPI(
    title="TravelAI API",
    description="AI-enhanced travel recommendation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global HTTP exception handler — no raw error strings leaked to clients
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning("HTTP error", status=exc.status_code, detail=exc.detail, path=request.url.path)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Catch-all for unexpected exceptions
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Request timing middleware — adds X-Process-Time header to every response
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - start) * 1000:.1f}ms"
    return response

# CORS middleware - origins driven by ALLOWED_ORIGINS env var
_default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://travel-ai-frontend-utj9.onrender.com",
    "https://travel-ai-frontend.onrender.com",
]

if settings.allowed_origins:
    allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
else:
    allowed_origins = _default_origins

logger.info("CORS allowed origins", origins=allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(main_router)
app.include_router(auth_router)
app.include_router(itinerary_router)
app.include_router(agent_router)
app.include_router(auto_research_router)
app.include_router(websocket_router)
app.include_router(city_router)
app.include_router(travelgenie_router)
app.include_router(travel_chat_router)
app.include_router(suggestions_router)
app.include_router(tripadvisor_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "TravelAI API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "recommendations": "/api/v1/recommendations",
            "destinations": "/api/v1/destinations",
            "auth": "/api/v1/auth",
            "itineraries": "/api/v1/itineraries",
            "health": "/api/v1/health",
            "travelgenie_agents": "/api/v1/travelgenie"
        }
    }