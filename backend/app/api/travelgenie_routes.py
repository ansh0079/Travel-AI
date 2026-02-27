"""
TravelGenie Agent Routes - 6-Agent System Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

from app.services.travelgenie_service import travelgenie_service

router = APIRouter(prefix="/api/v1/travelgenie", tags=["TravelGenie Agents"])


# Request/Response Models
class WeatherRequest(BaseModel):
    location: str
    travel_date: str  # YYYY-MM-DD


class RouteRequest(BaseModel):
    source: str
    destination: str


class FlightRequest(BaseModel):
    origin_city: str
    destination_city: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    max_results: int = 10


class LocationRequest(BaseModel):
    location: str


class EventsRequest(BaseModel):
    location: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class CompleteTravelRequest(BaseModel):
    source: str
    destination: str
    travel_date: str
    return_date: Optional[str] = None


# Weather Agent Endpoint
@router.post("/weather", summary="Get weather forecast")
async def get_weather(
    request: WeatherRequest,
):
    """
    Get weather forecast for a location on a specific date.
    Uses OpenWeatherMap API.
    """
    result = travelgenie_service.get_weather(request.location, request.travel_date)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


# Route Agent Endpoint
@router.post("/route", summary="Get route information")
async def get_route(
    request: RouteRequest,
):
    """
    Get route information including distance, duration, and fuel estimate.
    Uses Google Maps Routes API.
    """
    result = travelgenie_service.get_route(request.source, request.destination)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


# Flight Agent Endpoint
@router.post("/flights", summary="Search flights")
async def search_flights(
    request: FlightRequest,
):
    """
    Search flights using Amadeus API.
    Requires AMADEUS_API_KEY and AMADEUS_SECRET_KEY.
    """
    result = travelgenie_service.get_flights(
        origin_city=request.origin_city,
        destination_city=request.destination_city,
        departure_date=request.departure_date,
        return_date=request.return_date,
        adults=request.adults,
        max_results=request.max_results
    )
    if result and "error" in result[0]:
        raise HTTPException(status_code=503, detail=result[0]["error"])
    return {"flights": result}


# Food/Restaurant Agent Endpoint
@router.post("/restaurants", summary="Get restaurant recommendations")
async def get_restaurants(
    request: LocationRequest,
):
    """
    Get top restaurants in a location.
    Uses Google Places API.
    """
    result = travelgenie_service.get_restaurants(request.location)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


# Explorer/Attractions Agent Endpoint
@router.post("/attractions", summary="Get attractions and places")
async def get_attractions(
    request: LocationRequest,
):
    """
    Get top attractions and places to visit in a location.
    Uses Google Places API.
    """
    result = travelgenie_service.get_attractions(request.location)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


# Events Agent Endpoint
@router.post("/events", summary="Get events and festivals")
async def get_events(
    request: EventsRequest,
):
    """
    Get events from Ticketmaster for a location and date range.
    Requires TICKETMASTER_API_KEY.
    """
    result = travelgenie_service.get_events(
        request.location,
        request.start_date,
        request.end_date
    )
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


# Complete Travel Info Endpoint
@router.post("/complete-info", summary="Get all travel information")
async def get_complete_info(
    request: CompleteTravelRequest,
):
    """
    Get comprehensive travel information from all available agents:
    - Weather forecast
    - Route information
    - Flight options
    - Attractions
    - Restaurants
    - Events
    """
    result = travelgenie_service.get_complete_travel_info(
        source=request.source,
        destination=request.destination,
        travel_date=request.travel_date,
        return_date=request.return_date
    )
    return result


# Agent Status Endpoint
@router.get("/status", summary="Check TravelGenie agent status")
async def get_agent_status():
    """
    Check which TravelGenie agents are configured and available.
    """
    available_agents = list(travelgenie_service.agents.keys())
    
    # Determine which provider is used
    route_provider = "Google Maps" if travelgenie_service.api_keys['google_maps'] else "OpenStreetMap (FREE)"
    food_provider = "Google Maps" if travelgenie_service.api_keys['google_maps'] else "OpenStreetMap (FREE)"
    explorer_provider = "Google Maps" if travelgenie_service.api_keys['google_maps'] else "OpenStreetMap (FREE)"
    
    providers = {
        "weather": "OpenWeather (FREE)" if 'weather' in available_agents else "Not configured - needs OPEN_WEATHER_API_KEY",
        "route": route_provider,
        "flights": "Amadeus (FREE test tier)" if 'flights' in available_agents else "Not configured - needs AMADEUS_API_KEY + SECRET",
        "food": food_provider,
        "explorer": explorer_provider,
        "events": "Ticketmaster (FREE)" if 'events' in available_agents else "Not configured - needs TICKETMASTER_API_KEY"
    }
    
    required_keys = {
        "weather": "OPEN_WEATHER_API_KEY (FREE)",
        "route": "GOOGLE_MAPS_API_KEY (optional - falls back to FREE OpenStreetMap)",
        "flights": "AMADEUS_API_KEY + AMADEUS_SECRET_KEY (FREE test tier)",
        "food": "GOOGLE_MAPS_API_KEY (optional - falls back to FREE OpenStreetMap)",
        "explorer": "GOOGLE_MAPS_API_KEY (optional - falls back to FREE OpenStreetMap)",
        "events": "TICKETMASTER_API_KEY (FREE)"
    }
    
    return {
        "available_agents": available_agents,
        "total_agents": 6,
        "configured": len(available_agents),
        "providers": providers,
        "required_api_keys": required_keys,
        "free_alternatives": {
            "route": "OpenStreetMap (no key needed)",
            "food": "OpenStreetMap (no key needed)",
            "explorer": "OpenStreetMap (no key needed)"
        },
        "status": "ready" if len(available_agents) > 0 else "not_configured"
    }
