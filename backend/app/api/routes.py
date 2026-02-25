from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session

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

router = APIRouter(prefix="/api/v1", tags=["recommendations"])

@router.post("/recommendations", response_model=List[Destination])
async def get_recommendations(
    request: TravelRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get AI-powered travel recommendations"""
    try:
        # Initialize services
        ai_service = AIRecommendationService()
        weather_service = WeatherService()
        visa_service = VisaService()
        attractions_service = AttractionsService()
        affordability_service = AffordabilityService()
        events_service = EventsService()
        
        # Get candidate destinations
        candidates = await _get_candidate_destinations(request)
        
        # Enrich each destination with real-time data
        enriched_destinations = []
        for dest_data in candidates:
            dest = Destination(
                id=dest_data["id"],
                name=dest_data["name"],
                country=dest_data["country"],
                city=dest_data["city"],
                country_code=dest_data["country_code"],
                coordinates=dest_data["coordinates"]
            )
            
            # Fetch weather data
            dest.weather = await weather_service.get_weather(
                dest.coordinates["lat"],
                dest.coordinates["lng"],
                request.travel_start
            )
            
            # Fetch visa requirements
            dest.visa = await visa_service.get_visa_requirements(
                request.user_preferences.passport_country,
                dest.country_code
            )
            
            # Fetch affordability data
            dest.affordability = await affordability_service.get_affordability(
                dest.country_code,
                request.user_preferences.travel_style.value
            )
            
            # Fetch attractions
            dest.attractions = await attractions_service.get_natural_attractions(
                dest.coordinates["lat"],
                dest.coordinates["lng"],
                limit=8
            )
            
            # Fetch events
            dest.events = await events_service.get_events(
                dest.city,
                request.travel_start,
                request.travel_end,
                dest.country_code
            )
            
            enriched_destinations.append(dest)
        
        # Generate AI recommendations
        recommendations = await ai_service.generate_recommendations(
            request, 
            enriched_destinations
        )
        
        # Save search to history if user is logged in
        if current_user:
            await _save_search_history(current_user.id, request, len(recommendations))
        
        return recommendations
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/destinations")
async def list_destinations(
    query: Optional[str] = Query(None, description="Search query"),
    country: Optional[str] = Query(None, description="Filter by country code"),
    max_results: int = Query(20, ge=1, le=50)
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
    destination_id: str,
    travel_start: Optional[date] = None,
    travel_end: Optional[date] = None,
    passport_country: str = "US"
):
    """Get detailed information about a specific destination"""
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
    
    # Fetch all data
    dest.weather = await weather_service.get_weather(
        dest.coordinates["lat"],
        dest.coordinates["lng"],
        travel_start or date.today()
    )
    
    dest.visa = await visa_service.get_visa_requirements(
        passport_country,
        dest.country_code
    )
    
    dest.affordability = await affordability_service.get_affordability(
        dest.country_code
    )
    
    dest.attractions = await attractions_service.get_all_attractions(
        dest.coordinates["lat"],
        dest.coordinates["lng"],
        limit=15
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
        print(f"Error saving search history: {e}")
    finally:
        db.close()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}