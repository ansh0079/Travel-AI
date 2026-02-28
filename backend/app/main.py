from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

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

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass

settings = get_settings()

app = FastAPI(
    title="TravelAI API",
    description="AI-enhanced travel recommendation platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - origins driven by ALLOWED_ORIGINS env var
# Default allows common development and production origins
import os
_default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://travel-ai-frontend-utj9.onrender.com",
    "https://travel-ai-frontend.onrender.com",
]

# Parse from environment or use defaults
if settings.allowed_origins:
    allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
else:
    allowed_origins = _default_origins

print(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
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