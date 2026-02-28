"""
TripAdvisor Content API Routes
Exposes real TripAdvisor attractions, hotels, restaurants, and reviews.
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.tripadvisor_service import TripAdvisorService

router = APIRouter(prefix="/api/v1/tripadvisor", tags=["tripadvisor"])
ta = TripAdvisorService()


@router.get("/city/{city_name}/attractions")
async def city_attractions(
    city_name: str,
    limit: int = Query(8, ge=1, le=20),
):
    """Real TripAdvisor top attractions for a city."""
    if not ta.enabled:
        return {"enabled": False, "attractions": [], "message": "TRIPADVISOR_API_KEY not configured"}
    result = await ta.get_city_attractions(city_name, limit=limit)
    return result


@router.get("/city/{city_name}/hotels")
async def city_hotels(
    city_name: str,
    limit: int = Query(6, ge=1, le=15),
):
    """Real TripAdvisor hotels for a city."""
    if not ta.enabled:
        return {"enabled": False, "hotels": [], "message": "TRIPADVISOR_API_KEY not configured"}
    result = await ta.get_city_hotels(city_name, limit=limit)
    return result


@router.get("/city/{city_name}/restaurants")
async def city_restaurants(
    city_name: str,
    limit: int = Query(8, ge=1, le=20),
):
    """Real TripAdvisor restaurants for a city."""
    if not ta.enabled:
        return {"enabled": False, "restaurants": [], "message": "TRIPADVISOR_API_KEY not configured"}
    result = await ta.get_city_restaurants(city_name, limit=limit)
    return result


@router.get("/location/{location_id}/reviews")
async def location_reviews(location_id: str):
    """Real TripAdvisor reviews for a specific location."""
    if not ta.enabled:
        return {"enabled": False, "reviews": [], "message": "TRIPADVISOR_API_KEY not configured"}
    result = await ta.get_location_reviews(location_id)
    return result


@router.get("/status")
async def tripadvisor_status():
    """Check if TripAdvisor API is configured."""
    return {"enabled": ta.enabled, "message": "API key configured" if ta.enabled else "Set TRIPADVISOR_API_KEY env var"}
