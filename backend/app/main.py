from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import time
import json
import uuid

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
from app.api.reddit_routes import router as reddit_router
from app.database.connection import engine
from app.database.models import Base
from app.config import get_settings
from app.utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(log_format="console")  # Use "json" for production
logger = get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Request size limit (10MB max)
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting TravelAI API")
    # Note: Database migrations should be run via Alembic: `alembic upgrade head`
    # Base.metadata.create_all(bind=engine)  # Removed - use Alembic instead
    logger.info("TravelAI API started successfully")
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

# Global HTTP exception handler - no raw error strings leaked to clients
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning("HTTP error", 
                   status=exc.status_code, 
                   detail=exc.detail, 
                   path=request.url.path,
                   method=request.method)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": f"HTTP_{exc.status_code}"}
    )

# Validation error handler
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation error", 
                   path=request.url.path,
                   errors=[{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()])
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

# Catch-all for unexpected exceptions
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", 
                     path=request.url.path, 
                     method=request.method,
                     error_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}
    )

# 404 handler
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        logger.info("404 Not Found", path=request.url.path, method=request.method)
    return await http_exception_handler(request, exc)

# Request timing middleware — adds X-Process-Time header to every response
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - start) * 1000:.1f}ms"
    return response

# Request ID middleware - adds X-Request-ID for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    
    # Add to request state for logging
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Request size limit middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH"]:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE:
            logger.warning("Request too large", size=content_length, path=request.url.path)
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum size is {MAX_REQUEST_SIZE // (1024 * 1024)}MB"}
            )
    return await call_next(request)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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
app.include_router(reddit_router)

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