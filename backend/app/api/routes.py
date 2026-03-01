from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Request
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
import traceback
import asyncio

from app.database.connection import get_db
from app.database.models import User, SearchHistory
from app.models.destination import Destination
from app.models.user import TravelRequest, UserPreferences, Interest, TravelStyle
from app.services.ai_recommendation_service import AIRecommendationService
from app.services.weather_service import WeatherService
from app.services.visa_service import VisaService
from app.services.attractions_service import AttractionsService
from app.services.affordability_service import AffordabilityService
from app.services.events_service import EventsService
from app.config import POPULAR_DESTINATIONS
from app.utils.security import get_current_user, get_current_user_optional
from app.utils.logging_config import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = get_logger(__name__)

# Create limiter for this module
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1", tags=["recommendations"])

@router.post("/recommendations", response_model=List[Destination])
@limiter.limit("30/minute")
async def get_recommendations(
    request: Request,
    request_data: TravelRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get AI-powered travel recommendations"""
    try:
        logger.info("Generating recommendations",
                   origin=request_data.origin,
                   travel_start=str(request_data.travel_start),
                   num_travelers=request_data.num_travelers)

        # Initialize services
        ai_service = AIRecommendationService()
        weather_service = WeatherService()
        visa_service = VisaService()
        attractions_service = AttractionsService()
        affordability_service = AffordabilityService()
        events_service = EventsService()

        # Get candidate destinations
        candidates = await _get_candidate_destinations(request_data)
        logger.info(f"Got {len(candidates)} candidate destinations")

        # Enrich each destination with real-time data IN PARALLEL
        async def enrich_destination(dest_data: dict) -> Optional[Destination]:
            """Enrich a single destination with all data"""
            try:
                dest = Destination(
                    id=dest_data["id"],
                    name=dest_data["name"],
                    country=dest_data["country"],
                    city=dest_data["city"],
                    country_code=dest_data["country_code"],
                    coordinates=dest_data["coordinates"]
                )

                # Fetch all data in parallel for this destination
                dest.weather, dest.visa, dest.affordability, dest.attractions, dest.events = await asyncio.gather(
                    weather_service.get_weather(
                        dest.coordinates["lat"],
                        dest.coordinates["lng"],
                        request_data.travel_start
                    ),
                    visa_service.get_visa_requirements(
                        request_data.user_preferences.passport_country,
                        dest.country_code
                    ),
                    affordability_service.get_affordability(
                        dest.country_code,
                        request_data.user_preferences.travel_style.value
                    ),
                    attractions_service.get_natural_attractions(
                        dest.coordinates["lat"],
                        dest.coordinates["lng"],
                        limit=8
                    ),
                    events_service.get_events(
                        dest.city,
                        request_data.travel_start,
                        request_data.travel_end,
                        dest.country_code
                    ),
                    return_exceptions=True
                )

                # Log any errors but continue
                for field, value in [("weather", dest.weather), ("visa", dest.visa),
                                     ("affordability", dest.affordability), ("attractions", dest.attractions),
                                     ("events", dest.events)]:
                    if isinstance(value, Exception):
                        logger.warning(f"Failed to fetch {field} for {dest.name}", error=str(value))
                        setattr(dest, field, None)

                return dest
            except Exception as dest_err:
                logger.error(f"Error enriching {dest_data.get('name', '?')}", error=str(dest_err))
                return None

        # Process all destinations in parallel
        enriched_results = await asyncio.gather(
            *[enrich_destination(d) for d in candidates]
        )
        enriched_destinations = [d for d in enriched_results if d is not None]

        logger.info(f"Enriched {len(enriched_destinations)} destinations, generating AI recommendations")

        # Generate AI recommendations
        recommendations = await ai_service.generate_recommendations(
            request_data,
            enriched_destinations
        )

        logger.info(f"Generated {len(recommendations)} recommendations")

        # Save search to history if user is logged in
        if current_user:
            await _save_search_history(current_user.id, request_data, len(recommendations))

        return recommendations

    except Exception as e:
        logger.exception("Error generating recommendations")
        raise HTTPException(status_code=500, detail="Internal server error while generating recommendations")

@router.get("/destinations")
async def list_destinations(
    query: Optional[str] = Query(None, min_length=1, max_length=100, description="Search query"),
    country: Optional[str] = Query(None, min_length=2, max_length=2, description="Filter by country code"),
    max_results: int = Query(20, ge=1, le=100, description="Maximum results to return")
):
    """List available destinations"""
    destinations = POPULAR_DESTINATIONS

    if query:
        query_lower = query.lower()
        destinations = [
            d for d in destinations
            if query_lower in d["name"].lower()
            or query_lower in d["country"].lower()
            or query_lower in d["city"].lower()
        ]

    if country:
        destinations = [d for d in destinations if d["country_code"] == country.upper()]

    return destinations[:max_results]

@router.get("/destinations/{destination_id}")
async def get_destination_details(
    destination_id: str = Path(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_-]+$"),
    travel_start: Optional[date] = None,
    travel_end: Optional[date] = None,
    passport_country: str = "US"
):
    """Get detailed information about a specific destination"""
    logger.info("Fetching destination details", destination_id=destination_id)
    
    # Find destination
    dest_data = next(
        (d for d in POPULAR_DESTINATIONS if d["id"] == destination_id),
        None
    )

    if not dest_data:
        raise HTTPException(status_code=404, detail="Destination not found")

    # Initialize services
    weather_service = WeatherService()
    visa_service = VisaService()
    attractions_service = AttractionsService()
    affordability_service = AffordabilityService()
    events_service = EventsService()

    # Create destination object
    dest = Destination(
        id=dest_data["id"],
        name=dest_data["name"],
        country=dest_data["country"],
        city=dest_data["city"],
        country_code=dest_data["country_code"],
        coordinates=dest_data["coordinates"]
    )

    # Fetch all data in parallel
    dest.weather, dest.visa, dest.affordability, dest.attractions = await asyncio.gather(
        weather_service.get_weather(
            dest.coordinates["lat"],
            dest.coordinates["lng"],
            travel_start or date.today()
        ),
        visa_service.get_visa_requirements(
            passport_country,
            dest.country_code
        ),
        affordability_service.get_affordability(
            dest.country_code
        ),
        attractions_service.get_all_attractions(
            dest.coordinates["lat"],
            dest.coordinates["lng"],
            limit=15
        ),
        return_exceptions=True
    )

    if travel_start and travel_end:
        dest.events = await events_service.get_events(
            dest.city,
            travel_start,
            travel_end,
            dest.country_code
        )

    return dest

@router.get("/visa-requirements/{passport_country}/{destination_country}")
async def check_visa_requirements(
    passport_country: str,
    destination_country: str
):
    """Check visa requirements between countries"""
    visa_service = VisaService()
    visa = await visa_service.get_visa_requirements(
        passport_country.upper(),
        destination_country.upper()
    )
    return {
        "visa": visa,
        "summary": visa_service.get_visa_summary(visa)
    }

@router.get("/weather/{lat},{lon}")
async def get_weather(
    lat: float,
    lon: float,
    date: Optional[date] = None
):
    """Get weather for a location"""
    weather_service = WeatherService()
    weather = await weather_service.get_weather(lat, lon, date)
    if not weather:
        raise HTTPException(status_code=404, detail="Weather data not available")
    return weather

@router.get("/attractions/{lat},{lon}")
async def get_attractions(
    lat: float,
    lon: float,
    natural_only: bool = False,
    limit: int = Query(10, ge=1, le=20)
):
    """Get attractions near a location"""
    attractions_service = AttractionsService()
    
    if natural_only:
        attractions = await attractions_service.get_natural_attractions(lat, lon, limit=limit)
    else:
        attractions = await attractions_service.get_all_attractions(lat, lon, limit=limit)
    
    return attractions

async def _get_candidate_destinations(request: TravelRequest) -> List[dict]:
    """Get candidate destinations based on search criteria"""
    # In a full implementation, this would use more sophisticated filtering
    # For now, return popular destinations that aren't the origin
    
    origin_lower = request.origin.lower()
    
    candidates = [
        d for d in POPULAR_DESTINATIONS
        if origin_lower not in d["city"].lower()
        and origin_lower not in d["country"].lower()
    ]
    
    # Limit to reasonable number for scoring
    return candidates[:15]

async def _save_search_history(user_id: str, request: TravelRequest, results_count: int):
    """Save search to user history"""
    from app.database.connection import SessionLocal
    
    db = SessionLocal()
    try:
        search = SearchHistory(
            user_id=user_id,
            origin=request.origin,
            travel_start=datetime.combine(request.travel_start, datetime.min.time()),
            travel_end=datetime.combine(request.travel_end, datetime.min.time()),
            search_query=f"From {request.origin}, {request.num_travelers} travelers, {request.travel_start} to {request.travel_end}",
            results_count=results_count
        )
        db.add(search)
        db.commit()
    except Exception as e:
        logger.warning("Error saving search history", error=str(e))
    finally:
        db.close()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}