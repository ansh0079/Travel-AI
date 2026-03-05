from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Request
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import traceback
import asyncio
from pydantic import BaseModel
from collections import deque
from threading import Lock
import json

from app.database.connection import get_db, engine
from app.database.models import User, SearchHistory, AnalyticsEvent
from app.models.destination import Destination
from app.models.user import TravelRequest, UserPreferences, Interest, TravelStyle
from app.services.ai_recommendation_service import AIRecommendationService
from app.services.weather_service import WeatherService
from app.services.visa_service import VisaService
from app.services.attractions_service import AttractionsService
from app.services.affordability_service import AffordabilityService
from app.services.events_service import EventsService
from app.services.flight_service import FlightService
from app.config import POPULAR_DESTINATIONS
from app.utils.datetime_utils import utcnow_naive
from app.utils.security import get_current_user, get_current_user_optional
from app.utils.logging_config import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = get_logger(__name__)

# Create limiter for this module
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1", tags=["recommendations"])
_analytics_events = deque(maxlen=5000)
_analytics_lock = Lock()
_analytics_table_ready = False
_funnel_events = [
    "chat_ready_reached",
    "autonomous_research_started",
    "autonomous_research_completed",
    "recommendation_accepted",
]


class AnalyticsEventRequest(BaseModel):
    event_name: str
    session_id: Optional[str] = None
    metadata: Optional[dict] = None


class ItineraryExportRequest(BaseModel):
    """Request payload for exporting a simple trip summary."""
    destination: str
    score: Optional[float] = None
    reasons: Optional[List[str]] = None
    highlights: Optional[dict] = None


def _ensure_analytics_table():
    """Create analytics table lazily if migrations haven't been applied yet."""
    global _analytics_table_ready
    if _analytics_table_ready:
        return
    AnalyticsEvent.__table__.create(bind=engine, checkfirst=True)
    _analytics_table_ready = True


@router.get("/travel-pulse")
async def get_travel_pulse():
    """Return a lightweight live travel pulse feed for top routes."""
    routes = [
        {"from_city": "New York", "to_city": "Lisbon", "from_code": "JFK", "to_code": "LIS"},
        {"from_city": "London", "to_city": "Tokyo", "from_code": "LHR", "to_code": "NRT"},
        {"from_city": "San Francisco", "to_city": "Bali", "from_code": "SFO", "to_code": "DPS"},
        {"from_city": "Chicago", "to_city": "Rome", "from_code": "ORD", "to_code": "FCO"},
        {"from_city": "Boston", "to_city": "Barcelona", "from_code": "BOS", "to_code": "BCN"},
    ]
    departure_date = date.today() + timedelta(days=30)
    flight_service = FlightService()
    pulse = []

    for route in routes:
        try:
            flights = await flight_service.search_flights(
                origin=route["from_code"],
                destination=route["to_code"],
                departure_date=departure_date,
            )
            cheapest = min((f.price for f in flights), default=0)
            trend_seed = (abs(hash(f'{route["from_code"]}-{route["to_code"]}-{date.today().isocalendar().week}')) % 21) - 10
            pulse.append({
                "from": route["from_city"],
                "to": route["to_city"],
                "fare": f"${int(round(cheapest))}" if cheapest else "N/A",
                "trend": f"{trend_seed:+d}%",
            })
        except Exception as e:
            logger.warning("Travel pulse route failed", route=str(route), error=str(e))
            pulse.append({
                "from": route["from_city"],
                "to": route["to_city"],
                "fare": "N/A",
                "trend": "0%",
            })

    return {
        "updated_at": utcnow_naive().isoformat() + "Z",
        "routes": pulse,
    }


@router.post("/analytics/events")
async def ingest_analytics_event(
    event: AnalyticsEventRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Lightweight analytics event ingestion for product funnel telemetry."""
    logger.info(
        "Analytics event",
        event_name=event.event_name,
        session_id=event.session_id,
        metadata=event.metadata or {},
        request_id=getattr(request.state, "request_id", None),
    )
    persisted = False
    try:
        _ensure_analytics_table()
        db_event = AnalyticsEvent(
            event_name=event.event_name,
            session_id=event.session_id,
            metadata_json=json.dumps(event.metadata or {}),
            created_at=utcnow_naive(),
        )
        db.add(db_event)
        db.commit()
        persisted = True
    except Exception as e:
        db.rollback()
        logger.warning("Analytics DB persist failed; using memory fallback", error=str(e))

    if not persisted:
        with _analytics_lock:
            _analytics_events.append({
                "event_name": event.event_name,
                "session_id": event.session_id,
                "metadata": event.metadata or {},
                "timestamp": utcnow_naive(),
            })
    return {"status": "ok"}


@router.get("/analytics/funnel-summary")
async def get_funnel_summary(
    db: Session = Depends(get_db)
):
    """Return lightweight conversion metrics for autonomous funnel events."""
    now = utcnow_naive()
    day_ago = now - timedelta(hours=24)
    totals = {name: 0 for name in _funnel_events}
    last_24h = {name: 0 for name in _funnel_events}

    try:
        _ensure_analytics_table()
        total_rows = (
            db.query(AnalyticsEvent.event_name, func.count(AnalyticsEvent.id))
            .filter(AnalyticsEvent.event_name.in_(_funnel_events))
            .group_by(AnalyticsEvent.event_name)
            .all()
        )
        for event_name, count in total_rows:
            totals[event_name] = int(count)

        day_rows = (
            db.query(AnalyticsEvent.event_name, func.count(AnalyticsEvent.id))
            .filter(AnalyticsEvent.event_name.in_(_funnel_events))
            .filter(AnalyticsEvent.created_at >= day_ago)
            .group_by(AnalyticsEvent.event_name)
            .all()
        )
        for event_name, count in day_rows:
            last_24h[event_name] = int(count)
    except Exception as e:
        logger.warning("Analytics DB summary failed; using memory fallback", error=str(e))
        with _analytics_lock:
            events = list(_analytics_events)
        for e in events:
            name = e.get("event_name")
            if name not in totals:
                continue
            totals[name] += 1
            if e.get("timestamp") and e["timestamp"] >= day_ago:
                last_24h[name] += 1

    ready = totals["chat_ready_reached"] or 1
    started = totals["autonomous_research_started"]
    completed = totals["autonomous_research_completed"]
    accepted = totals["recommendation_accepted"]

    conversion = {
        "ready_to_started_pct": round((started / ready) * 100, 1) if ready else 0.0,
        "started_to_completed_pct": round((completed / started) * 100, 1) if started else 0.0,
        "completed_to_accepted_pct": round((accepted / completed) * 100, 1) if completed else 0.0,
    }

    return {
        "generated_at": now.isoformat() + "Z",
        "totals": totals,
        "last_24h": last_24h,
        "conversion": conversion,
    }


@router.post("/itinerary/export")
async def export_itinerary(request: ItineraryExportRequest):
    """
    Export a simple markdown summary for a chosen destination recommendation.

    This is intentionally lightweight – the frontend can trigger this when a user
    clicks "Export trip" and download the returned markdown as a .md/.txt file.
    """
    lines = []
    lines.append(f"# Trip plan for {request.destination}")
    if request.score is not None:
        lines.append(f"\nOverall match score: **{round(request.score)}%**")

    if request.reasons:
        lines.append("\n## Why this destination")
        for r in request.reasons:
            lines.append(f"- {r}")

    if request.highlights:
        lines.append("\n## Highlights")
        for key, value in request.highlights.items():
            pretty_key = key.replace("_", " ").title()
            lines.append(f"- **{pretty_key}**: {value}")

    lines.append(
        "\n_Always double-check visa rules, prices, and local regulations with official sources before booking._"
    )

    markdown = "\n".join(lines)
    return {"markdown": markdown}

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

    # Fetch all data in parallel
    weather, visa, affordability, attractions = await asyncio.gather(
        weather_service.get_weather(
            dest_data["coordinates"]["lat"],
            dest_data["coordinates"]["lng"],
            travel_start or date.today()
        ),
        visa_service.get_visa_requirements(
            passport_country,
            dest_data["country_code"]
        ),
        affordability_service.get_affordability(
            dest_data["country_code"]
        ),
        attractions_service.get_all_attractions(
            dest_data["coordinates"]["lat"],
            dest_data["coordinates"]["lng"],
            limit=15
        ),
        return_exceptions=True
    )

    if isinstance(weather, Exception):
        weather = None
    if isinstance(visa, Exception):
        visa = None
    if isinstance(affordability, Exception):
        affordability = None
    if isinstance(attractions, Exception):
        attractions = []

    events = []
    if travel_start and travel_end:
        maybe_events = await events_service.get_events(
            dest_data["city"],
            travel_start,
            travel_end,
            dest_data["country_code"]
        )
        events = maybe_events if not isinstance(maybe_events, Exception) else []

    return {
        "id": dest_data["id"],
        "name": dest_data["name"],
        "country": dest_data["country"],
        "city": dest_data["city"],
        "country_code": dest_data["country_code"],
        "coordinates": dest_data["coordinates"],
        "weather": weather,
        "visa": visa,
        "affordability": affordability,
        "attractions": attractions,
        "events": events,
    }

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
    from app.config import COUNTRY_TO_CONTINENT
    
    origin_lower = request.origin.lower()
    prefs = request.user_preferences
    
    candidates = [
        d for d in POPULAR_DESTINATIONS
        if origin_lower not in d["city"].lower()
        and origin_lower not in d["country"].lower()
    ]
    
    # Filter by preferred continent
    if prefs.preferred_continent:
        candidates = [
            d for d in candidates 
            if d.get("continent") == prefs.preferred_continent
            or COUNTRY_TO_CONTINENT.get(d["country"]) == prefs.preferred_continent
        ]
    
    # Filter by preferred countries
    if prefs.preferred_countries:
        candidates = [
            d for d in candidates 
            if d["country"] in prefs.preferred_countries
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
    return {"status": "healthy", "timestamp": utcnow_naive().isoformat()}


@router.get("/config")
async def get_config():
    """Get API configuration status (without exposing keys)"""
    from app.config import get_settings, ENV_FILE, POSSIBLE_ENV_PATHS
    import os
    settings = get_settings()
    
    return {
        "env_file_loaded": ENV_FILE,
        "env_file_exists": os.path.exists(ENV_FILE) if ENV_FILE else False,
        "checked_paths": [os.path.abspath(p) for p in POSSIBLE_ENV_PATHS],
        "apis": {
            "openweather": {"configured": bool(settings.openweather_api_key)},
            "amadeus": {"configured": bool(settings.amadeus_api_key and settings.amadeus_api_secret)},
            "google_places": {"configured": bool(settings.google_places_api_key)},
            "tripadvisor": {"configured": bool(settings.tripadvisor_api_key)},
            "openai": {"configured": bool(settings.openai_api_key)},
            "ticketmaster": {"configured": bool(settings.ticketmaster_api_key)},
            "predicthq": {"configured": bool(settings.predicthq_api_key)},
            "booking": {"configured": bool(settings.booking_api_key)},
        },
        "database_url_configured": bool(settings.database_url),
        "debug_mode": settings.debug,
    }
