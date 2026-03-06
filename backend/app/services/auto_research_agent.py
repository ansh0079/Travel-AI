"""
Auto Research Agent - Autonomous travel information gathering
Triggered when users complete questionnaire/answer questions
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from time import perf_counter
from enum import Enum
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

from app.config import get_settings
from app.services.weather_service import WeatherService
from app.services.visa_service import VisaService
from app.services.attractions_service import AttractionsService
from app.services.events_service import EventsService
from app.services.affordability_service import AffordabilityService
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService
from app.services.restaurants_service import RestaurantsService
from app.services.transport_service import TransportService
from app.services.nightlife_service import NightlifeService
from app.services.agent_service import TravelResearchAgent

# Import web scrapers for enhanced research
from app.utils.api_scrapers import (
    search_flights,
    search_hotels,
    get_restaurants,
    get_events,
)
from app.utils.web_scrapers_enhanced import (
    TravelBlogScraper,
    SafetyScraper,
)

# Import analysis engines for Phase 2
from app.utils.analysis_engines import PricePredictor, SentimentAnalyzer

# Import caching for Phase 4
from app.utils.cache import get_cache, cached

# Import learning agent for Phase 4
from app.utils.learning_agent import improve_recommendations, learn_from_interaction

# Try to import WebSocket emitters, but don't fail if not available
try:
    from app.api.websocket_routes import (
        emit_research_progress,
        emit_research_completed,
        emit_research_error,
        emit_research_started
    )
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    # Define dummy functions if WebSocket module not available
    async def emit_research_progress(*args, **kwargs): pass
    async def emit_research_completed(*args, **kwargs): pass
    async def emit_research_error(*args, **kwargs): pass
    async def emit_research_started(*args, **kwargs): pass


class ResearchStep(str, Enum):
    INITIALIZING = "initializing"
    ANALYZING_PREFERENCES = "analyzing_preferences"
    RESEARCHING_WEATHER = "researching_weather"
    RESEARCHING_VISA = "researching_visa"
    RESEARCHING_ATTRACTIONS = "researching_attractions"
    RESEARCHING_EVENTS = "researching_events"
    RESEARCHING_AFFORDABILITY = "researching_affordability"
    RESEARCHING_FLIGHTS = "researching_flights"
    RESEARCHING_HOTELS = "researching_hotels"
    RESEARCHING_RESTAURANTS = "researching_restaurants"
    RESEARCHING_TRANSPORT = "researching_transport"
    RESEARCHING_NIGHTLIFE = "researching_nightlife"
    RESEARCHING_WEB = "researching_web"
    COMPILING_RESULTS = "compiling_results"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchDepth(str, Enum):
    """Research depth levels for autonomous agent."""
    QUICK = "quick"        # 1-2 sources, cached data, ~30 sec
    STANDARD = "standard"  # 3-5 sources, some real-time, ~2 min
    DEEP = "deep"          # All sources, real-time + scrapers, ~5 min


class AutoResearchAgent:
    """
    Autonomous agent that automatically gathers travel information
    once user submits their preferences/answers.
    """

    def __init__(self, job_id: Optional[str] = None, depth: ResearchDepth = ResearchDepth.STANDARD):
        self.settings = get_settings()
        self.job_id = job_id
        self.depth = depth

        # Initialize all services
        self.weather_service = WeatherService()
        self.visa_service = VisaService()
        self.attractions_service = AttractionsService()
        self.events_service = EventsService()
        self.affordability_service = AffordabilityService()
        self.flight_service = FlightService()
        self.hotel_service = HotelService()
        self.restaurants_service = RestaurantsService()
        self.transport_service = TransportService()
        self.nightlife_service = NightlifeService()
        self.web_agent = TravelResearchAgent()
        
        # Initialize scrapers for enhanced research
        # Note: API scrapers are called via functions, no instance needed
        self.blog_scraper = TravelBlogScraper()
        self.safety_scraper = SafetyScraper()
        
        # Initialize analysis engines (Phase 2)
        self.price_predictor = PricePredictor()
        self.sentiment_analyzer = SentimentAnalyzer()

        # Progress tracking - adjust steps based on depth
        self._progress_callback = None
        self._current_step = None
        self._completed_steps = 0
        self._total_steps = self._get_total_steps_for_depth(depth)
    
    def _get_total_steps_for_depth(self, depth: ResearchDepth) -> int:
        """Get total number of research steps based on depth."""
        if depth == ResearchDepth.QUICK:
            return 9  # Core services only
        elif depth == ResearchDepth.STANDARD:
            return 14  # Core + scrapers/web research
        else:  # DEEP
            return 18  # All services + scrapers + safety/analysis

    def _estimate_total_steps(
        self,
        destination_count: int,
        has_origin: bool,
        needs_suggestion: bool,
    ) -> int:
        """
        Estimate total progress steps for this run.
        Uses a conservative approximation to prevent early 100% progress.
        """
        base_steps = 1 + 2  # initializing + compiling + completed
        if needs_suggestion:
            base_steps += 1  # analyzing_preferences

        if self.depth == ResearchDepth.QUICK:
            per_destination = 4 + (1 if has_origin else 0)  # weather, visa, attractions, affordability, flights?
        else:
            per_destination = 6 + (1 if has_origin else 0)  # + restaurants + transport
            # scraper-backed updates
            per_destination += 2 + (1 if has_origin else 0)  # hotels + blogs + flight deals?
            if self.settings.brave_search_api_key:
                per_destination += 1  # web research progress

        total = base_steps + (max(1, destination_count) * per_destination)
        return max(total, base_steps + max(1, destination_count))
    
    @staticmethod
    def suggest_depth(preferences: Dict[str, Any]) -> ResearchDepth:
        """
        Suggest appropriate research depth based on user preferences.
        
        Args:
            preferences: User travel preferences
        
        Returns:
            Recommended ResearchDepth
        """
        # Check for luxury/high-budget trips → DEEP
        if preferences.get("budget_level") in ["luxury", "high"]:
            return ResearchDepth.DEEP
        
        # Check for special occasions → DEEP
        if preferences.get("trip_type") in ["romantic", "honeymoon", "anniversary"]:
            return ResearchDepth.DEEP
        
        # Check for family trips with kids → STANDARD or DEEP
        if preferences.get("has_kids") or preferences.get("traveling_with") == "family":
            return ResearchDepth.STANDARD
        
        # Check for adventure/cultural trips → STANDARD
        if preferences.get("trip_type") in ["adventure", "cultural", "exploration"]:
            return ResearchDepth.STANDARD
        
        # Check trip duration - longer trips benefit from more research
        try:
            if preferences.get("travel_start") and preferences.get("travel_end"):
                start = datetime.strptime(preferences["travel_start"], "%Y-%m-%d")
                end = datetime.strptime(preferences["travel_end"], "%Y-%m-%d")
                duration = (end - start).days
                if duration > 20:
                    return ResearchDepth.DEEP
                elif duration > 10:
                    return ResearchDepth.STANDARD
        except (ValueError, TypeError):
            pass
        
        # Check distance (international vs domestic)
        origin = preferences.get("origin", "")
        destinations = preferences.get("destinations", [])
        if origin and destinations:
            # Simple heuristic: if origin has country code or is far
            if len(origin.split()) > 2 or "," in origin:
                return ResearchDepth.STANDARD
        
        # Default to STANDARD for most cases
        return ResearchDepth.STANDARD
        
    def set_progress_callback(self, callback):
        """Set callback function for progress updates"""
        self._progress_callback = callback
        
    async def _update_progress(self, step: ResearchStep, message: str = ""):
        """Update progress and notify via callback and WebSocket"""
        self._current_step = step
        self._completed_steps += 1
        
        percentage = min(100, int((self._completed_steps / self._total_steps) * 100))
        
        progress_data = {
            "job_id": self.job_id,
            "step": step.value,
            "message": message or step.value,
            "completed_steps": self._completed_steps,
            "total_steps": self._total_steps,
            "percentage": percentage
        }
        
        # Notify via callback (database update)
        if self._progress_callback:
            await self._progress_callback(progress_data)
        
        # Emit WebSocket event for real-time updates
        if self.job_id and WEBSOCKET_AVAILABLE:
            try:
                await emit_research_progress(
                    job_id=self.job_id,
                    step=step.value,
                    percentage=percentage,
                    message=message or step.value
                )
            except Exception as e:
                # Don't let WebSocket errors break the research
                logger.warning("WebSocket emit error", error=str(e))

        return progress_data

    async def research_from_preferences(
        self,
        preferences: Dict[str, Any],
        depth: Optional[ResearchDepth] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Automatically research based on user preferences.

        Reads all questionnaire fields including:
            origin, destinations, travel_start, travel_end,
            budget_level, interests, traveling_with, visa_preference,
            weather_preference, max_flight_duration,
            has_kids, kids_ages, dietary_restrictions, accessibility_needs,
            pace_preference, trip_type
        
        Args:
            preferences: User travel preferences
            depth: Research depth (QUICK, STANDARD, or DEEP). Defaults to agent's initialized depth.
        """
        # Use provided depth or default
        if depth is not None:
            self.depth = depth
            self._total_steps = self._get_total_steps_for_depth(depth)

        # Pre-calibrate progress denominator before first emitted update to
        # avoid early percentages overshooting and then dropping.
        initial_destinations = preferences.get("destinations", []) or []
        self._total_steps = self._estimate_total_steps(
            destination_count=min(3, len(initial_destinations)) if initial_destinations else 3,
            has_origin=bool(preferences.get("origin")),
            needs_suggestion=not bool(initial_destinations),
        )
        
        await self._update_progress(ResearchStep.INITIALIZING, "Starting research...")

        # Emit started event via WebSocket
        if self.job_id and WEBSOCKET_AVAILABLE:
            try:
                await emit_research_started(self.job_id, preferences)
            except Exception as e:
                logger.warning("WebSocket emit error (started)", error=str(e))
        
        try:
            # ── Parse all preferences (including questionnaire branching fields) ──
            origin             = preferences.get("origin", "")
            destinations       = preferences.get("destinations", [])
            had_destinations   = bool(destinations)
            travel_start       = preferences.get("travel_start")
            travel_end         = preferences.get("travel_end")
            budget_level       = preferences.get("budget_level", "moderate")
            interests          = preferences.get("interests", [])
            passport_country   = preferences.get("passport_country", "US")

            # Questionnaire branching fields
            traveling_with        = preferences.get("traveling_with", "solo")
            has_kids              = preferences.get("has_kids", False)
            kids_ages             = preferences.get("kids_ages", [])
            dietary_restrictions  = preferences.get("dietary_restrictions", [])
            accessibility_needs   = preferences.get("accessibility_needs", [])
            pace_preference       = preferences.get("pace_preference", "moderate")
            trip_type             = preferences.get("trip_type", "leisure")

            # Auto-inject nightlife interest for groups if not already present
            if traveling_with == "group" and "nightlife" not in [i.lower() for i in interests]:
                interests = list(interests) + ["nightlife"]

            # Auto-inject relaxation for couples on romantic trips
            if traveling_with == "couple" and trip_type == "romantic" and "relaxation" not in [i.lower() for i in interests]:
                interests = list(interests) + ["relaxation"]

            # Store enriched interests back so suggestion logic also benefits
            preferences = {**preferences, "interests": interests}

            # If no specific destinations, we need to find recommendations first
            if not destinations:
                await self._update_progress(ResearchStep.ANALYZING_PREFERENCES, "Finding best destinations for your preferences...")
                destinations = await self._suggest_destinations(preferences)
            
            # Limit research scope and calibrate progress denominator for this run.
            destinations = destinations[:3]
            self._total_steps = self._estimate_total_steps(
                destination_count=len(destinations),
                has_origin=bool(origin),
                needs_suggestion=not had_destinations,
            )
            
            # Research each destination comprehensively
            results = {
                "preferences": preferences,
                "research_timestamp": datetime.now().isoformat(),
                "destinations": [],
                "comparison": None,
                "recommendations": []
            }
            
            # Research all destinations in parallel (pass full context)
            destination_tasks = [
                self._research_single_destination(
                    dest, origin, travel_start, travel_end,
                    budget_level, interests, passport_country,
                    has_kids=has_kids,
                    kids_ages=kids_ages,
                    dietary_restrictions=dietary_restrictions,
                    accessibility_needs=accessibility_needs,
                    pace_preference=pace_preference,
                    traveling_with=traveling_with,
                )
                for dest in destinations
            ]
            
            destination_results = await asyncio.gather(*destination_tasks, return_exceptions=True)
            
            for dest, result in zip(destinations, destination_results):
                if isinstance(result, Exception):
                    results["destinations"].append({
                        "name": dest,
                        "error": str(result),
                        "status": "failed"
                    })
                else:
                    results["destinations"].append(result)
            
            # Generate comparison and recommendations
            await self._update_progress(ResearchStep.COMPILING_RESULTS, "Compiling final recommendations...")
            results["comparison"] = self._generate_comparison(results["destinations"])
            
            # Generate base recommendations
            base_recommendations = self._generate_recommendations(results["destinations"], preferences)
            
            # Improve recommendations using learning (Phase 4)
            user_id = preferences.get("user_id")  # Assuming user_id is passed in preferences
            if user_id and base_recommendations:
                logger.info(f"Improving recommendations with learning for user {user_id}")
                base_recommendations = improve_recommendations(base_recommendations, user_id)
            
            results["recommendations"] = base_recommendations
            
            # Cache the research results (Phase 4)
            cache = get_cache()
            await cache.set_research(self.job_id or "temp", results)
            
            await self._update_progress(ResearchStep.COMPLETED, "Research completed!")
            
            # Emit completed event via WebSocket
            if self.job_id and WEBSOCKET_AVAILABLE:
                try:
                    summary = {
                        "destinations_count": len(results.get("destinations", [])),
                        "top_destination": results["recommendations"][0]["destination"] if results.get("recommendations") else None,
                        "top_score": results["recommendations"][0]["score"] if results.get("recommendations") else 0
                    }
                    await emit_research_completed(self.job_id, summary)
                except Exception as e:
                    logger.warning("WebSocket emit error (completed)", error=str(e))

            return results

        except Exception as e:
            await self._update_progress(ResearchStep.FAILED, f"Research failed: {str(e)}")

            # Emit error event via WebSocket
            if self.job_id and WEBSOCKET_AVAILABLE:
                try:
                    await emit_research_error(self.job_id, str(e))
                except Exception as ws_e:
                    logger.warning("WebSocket emit error (error)", error=str(ws_e))

            raise
    
    async def _suggest_destinations(self, preferences: Dict[str, Any]) -> List[str]:
        """Suggest destinations based on preferences"""
        interests = preferences.get("interests", [])
        budget_level = preferences.get("budget_level", "moderate")
        weather_pref = preferences.get("weather_preference", "warm")
        
        # Base suggestions by interest
        destination_map = {
            "beach": ["Bali, Indonesia", "Maldives", "Phuket, Thailand", "Santorini, Greece", "Maui, Hawaii"],
            "mountain": ["Swiss Alps, Switzerland", "Banff, Canada", "Queenstown, New Zealand", "Chamonix, France", "Kathmandu, Nepal"],
            "city": ["Tokyo, Japan", "Paris, France", "New York, USA", "Barcelona, Spain", "Singapore"],
            "history": ["Rome, Italy", "Athens, Greece", "Cairo, Egypt", "Kyoto, Japan", "Machu Picchu, Peru"],
            "nature": ["Costa Rica", "Iceland", "Patagonia, Chile", "Kenya", "Norway"],
            "adventure": ["Queenstown, New Zealand", "Interlaken, Switzerland", "Moab, USA", "Cape Town, South Africa", "Reykjavik, Iceland"],
            "food": ["Tokyo, Japan", "Bangkok, Thailand", "Barcelona, Spain", "Mexico City, Mexico", "Lyon, France"],
            "culture": ["Marrakech, Morocco", "Istanbul, Turkey", "Varanasi, India", "Havana, Cuba", "Prague, Czech Republic"],
            "relaxation": ["Bali, Indonesia", "Tulum, Mexico", "Seychelles", "Fiji", "Santorini, Greece"],
            "nightlife": ["Berlin, Germany", "Amsterdam, Netherlands", "Las Vegas, USA", "Rio de Janeiro, Brazil", "Bangkok, Thailand"],
        }
        
        suggestions = set()
        for interest in interests:
            if interest.lower() in destination_map:
                suggestions.update(destination_map[interest.lower()])
        
        # Add budget-appropriate destinations
        budget_destinations = {
            "low": ["Vietnam", "Thailand", "Mexico", "Portugal", "Colombia", "Indonesia", "India"],
            "moderate": ["Spain", "Greece", "Turkey", "Malaysia", "Czech Republic", "Poland", "Argentina"],
            "high": ["Japan", "France", "Italy", "Australia", "UAE", "Singapore", "South Korea"],
            "luxury": ["Switzerland", "Maldives", "Monaco", "Bora Bora", "Seychelles", "Dubai, UAE"]
        }
        
        if budget_level in budget_destinations:
            suggestions.update(budget_destinations[budget_level])
        
        return list(suggestions)[:8] if suggestions else ["Paris, France", "Tokyo, Japan", "Barcelona, Spain"]
    
    async def _research_single_destination(
        self,
        destination: str,
        origin: str,
        travel_start: Optional[str],
        travel_end: Optional[str],
        budget_level: str,
        interests: List[str],
        passport_country: str,
        *,
        has_kids: bool = False,
        kids_ages: List[str] = None,
        dietary_restrictions: List[str] = None,
        accessibility_needs: List[str] = None,
        pace_preference: str = "moderate",
        traveling_with: str = "solo",
    ) -> Dict[str, Any]:
        """Research a single destination comprehensively"""
        
        result = {
            "name": destination,
            "status": "researching",
            "data": {}
        }

        external_metrics: Dict[str, Any] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_latency_ms": 0,
            "sources": {},
        }

        async def _call_external(source: str, awaitable):
            started = perf_counter()
            ok = False
            try:
                output = await awaitable
                ok = True
                return output
            finally:
                elapsed_ms = int((perf_counter() - started) * 1000)
                external_metrics["total_calls"] += 1
                external_metrics["total_latency_ms"] += elapsed_ms
                if ok:
                    external_metrics["successful_calls"] += 1
                else:
                    external_metrics["failed_calls"] += 1

                source_stats = external_metrics["sources"].setdefault(
                    source,
                    {"calls": 0, "success": 0, "failed": 0, "latency_ms": 0},
                )
                source_stats["calls"] += 1
                source_stats["latency_ms"] += elapsed_ms
                if ok:
                    source_stats["success"] += 1
                else:
                    source_stats["failed"] += 1
        
        dietary_restrictions  = dietary_restrictions or []
        accessibility_needs   = accessibility_needs or []
        kids_ages             = kids_ages or []

        try:
            # 1. Weather Research
            await self._update_progress(ResearchStep.RESEARCHING_WEATHER, f"Checking weather for {destination}...")
            weather = await _call_external(
                "weather_service",
                self._get_weather_for_destination(destination, travel_start),
            )
            result["data"]["weather"] = weather

            # 2. Visa Requirements
            await self._update_progress(ResearchStep.RESEARCHING_VISA, f"Checking visa requirements for {destination}...")
            visa_info = await _call_external(
                "visa_service",
                self._get_visa_info(destination, passport_country),
            )
            result["data"]["visa"] = visa_info

            # 3. Attractions & Events (run in parallel)
            #    Filter attractions label for family trips
            attraction_label = "family-friendly " if has_kids else ""
            await self._update_progress(
                ResearchStep.RESEARCHING_ATTRACTIONS,
                f"Finding {attraction_label}attractions in {destination}..."
            )
            attractions_task = _call_external(
                "attractions_service",
                self._get_attractions_fast(destination, interests),
            )
            events_task = _call_external(
                "events_service",
                self._get_events_fast(destination, travel_start, travel_end),
            )
            attractions, events = await asyncio.gather(attractions_task, events_task)

            # Tag kid-friendly flag on each attraction when traveling with family
            if has_kids:
                for a in attractions:
                    category = str(a.get("category", "") or a.get("type", "")).lower()
                    a["kid_friendly"] = any(
                        kw in category for kw in
                        ["park", "museum", "zoo", "beach", "attraction", "theme", "nature", "garden"]
                    )
                result["data"]["kids_ages"] = kids_ages

            result["data"]["attractions"] = attractions
            result["data"]["events"] = events

            # 4. Affordability
            await self._update_progress(ResearchStep.RESEARCHING_AFFORDABILITY, f"Analyzing costs for {destination}...")
            affordability = await _call_external(
                "affordability_service",
                self._get_affordability(destination, budget_level),
            )
            result["data"]["affordability"] = affordability

            # 5. Flights & Hotels (parallel) - Using API-first approach
            if origin:
                flights_task = _call_external(
                    "flight_search",
                    search_flights(origin, destination, travel_start),
                )
                await self._update_progress(ResearchStep.RESEARCHING_FLIGHTS, f"Searching flights to {destination} (API + scraping)...")
            else:
                flights_task = asyncio.sleep(0)
            
            hotels_task = _call_external(
                "hotel_search",
                search_hotels(destination, travel_start, travel_end, budget_level),
            )
            
            flights, hotels = await asyncio.gather(flights_task, hotels_task)

            if origin:
                result["data"]["flights"] = flights

            # Filter hotels: accessibility flag if needed
            if accessibility_needs and "none" not in [a.lower() for a in accessibility_needs]:
                for h in hotels:
                    h["accessibility_note"] = "Confirm accessibility features directly with hotel"
            result["data"]["hotels"] = hotels

            # 6-8. Optional enrichment (skip in QUICK mode for speed)
            if self.depth != ResearchDepth.QUICK:
                # Restaurants - Using API-first approach
                await self._update_progress(ResearchStep.RESEARCHING_RESTAURANTS, f"Finding restaurants in {destination} (API + scraping)...")
                restaurants = await _call_external(
                    "restaurant_search",
                    get_restaurants(destination, dietary_restrictions),
                )
                
                # Annotate dietary suitability
                if dietary_restrictions and "none" not in [d.lower() for d in dietary_restrictions]:
                    for r in restaurants:
                        r["dietary_info"] = dietary_restrictions
                    result["data"]["dietary_restrictions"] = dietary_restrictions
                result["data"]["restaurants"] = {"restaurants": restaurants, "top_picks": restaurants[:3]}

                # 7. Local Transport
                await self._update_progress(ResearchStep.RESEARCHING_TRANSPORT, f"Researching transport options for {destination}...")
                transport = await _call_external(
                    "transport_service",
                    self._get_transport_info(destination),
                )
                # Add accessibility note to transport if needed
                if accessibility_needs and "wheelchair" in [a.lower() for a in accessibility_needs]:
                    transport["accessibility_note"] = "Check wheelchair accessibility for public transport before travel"
                result["data"]["transport"] = transport

                # 8. Nightlife - trigger for: nightlife interest OR group travelers
                nightlife_interests = [i.lower() for i in interests]
                if "nightlife" in nightlife_interests or traveling_with == "group":
                    await self._update_progress(ResearchStep.RESEARCHING_NIGHTLIFE, f"Finding nightlife in {destination}...")
                    nightlife = await _call_external(
                        "nightlife_service",
                        self._get_nightlife_info(destination),
                    )
                    result["data"]["nightlife"] = nightlife
            else:
                result["data"]["restaurants"] = {"restaurants": [], "top_picks": []}

            # 9. Enhanced Research with Scrapers (depth-based)
            if self.depth in [ResearchDepth.STANDARD, ResearchDepth.DEEP]:
                # Flight/hotel deals are derived from API-first search results.
                if origin and result["data"].get("flights"):
                    sorted_flights = sorted(
                        result["data"]["flights"],
                        key=lambda f: f.get("price", float("inf")),
                    )
                    result["data"]["flight_deals"] = sorted_flights[:3]

                await self._update_progress(ResearchStep.RESEARCHING_HOTELS, f"Searching hotel deals for {destination}...")
                if result["data"].get("hotels"):
                    result["data"]["hotel_deals"] = result["data"]["hotels"][:5]
                
                # Travel blog insights
                await self._update_progress(ResearchStep.RESEARCHING_WEB, f"Finding travel tips for {destination}...")
                try:
                    blog_insights = await _call_external(
                        "travel_blog_scraper",
                        self.blog_scraper.get_destination_insights(destination),
                    )
                    if blog_insights:
                        result["data"]["blog_insights"] = blog_insights
                except Exception as e:
                    logger.warning(f"Blog scraper failed: {str(e)}")

            # 10. Deep Research (DEEP depth only)
            if self.depth == ResearchDepth.DEEP:
                # Safety information
                try:
                    safety_info = await _call_external(
                        "safety_scraper",
                        self.safety_scraper.get_safety_info(destination),
                    )
                    result["data"]["safety"] = safety_info
                except Exception as e:
                    logger.warning(f"Safety scraper failed: {str(e)}")
                
                # Local events from API-first source
                try:
                    deep_events = await _call_external(
                        "event_search",
                        get_events(destination, travel_start, travel_end),
                    )
                    if deep_events:
                        existing_events = result["data"].get("events", [])
                        result["data"]["events"] = existing_events + deep_events
                except Exception as e:
                    logger.warning(f"Event search failed: {str(e)}")
                
                # Restaurant recommendations from already fetched list (or a deep refresh fallback).
                try:
                    existing_restaurants = result["data"].get("restaurants", {}).get("restaurants", [])
                    if existing_restaurants:
                        result["data"]["restaurant_recommendations"] = existing_restaurants[:8]
                    else:
                        deep_restaurants = await _call_external(
                            "restaurant_search",
                            get_restaurants(destination, dietary_restrictions),
                        )
                        if deep_restaurants:
                            result["data"]["restaurant_recommendations"] = deep_restaurants[:8]
                except Exception as e:
                    logger.warning(f"Restaurant search failed: {str(e)}")

            # Store contextual metadata for recommendation text generation
            result["data"]["context"] = {
                "traveling_with": traveling_with,
                "has_kids": has_kids,
                "pace_preference": pace_preference,
                "accessibility_needs": accessibility_needs,
                "dietary_restrictions": dietary_restrictions,
                "research_depth": self.depth.value,
            }

            # 11. Web Research — runs when Brave Search API key is configured
            from app.config import get_settings
            if self.depth != ResearchDepth.QUICK and get_settings().brave_search_api_key:
                await self._update_progress(ResearchStep.RESEARCHING_WEB, f"Researching {destination} online...")
                try:
                    web_info = await asyncio.wait_for(
                        self.web_agent.research_destination(
                            destination=destination,
                            travel_dates=(travel_start, travel_end) if travel_start and travel_end else None,
                            interests=interests,
                            budget=budget_level
                        ),
                        timeout=20.0
                    )
                    result["data"]["web_research"] = web_info
                except asyncio.TimeoutError:
                    logger.warning("AutoResearch web research timed out", destination=destination)
                except Exception as web_err:
                    logger.warning("AutoResearch web research failed", destination=destination, error=str(web_err))

            # 12. Phase 2 Analysis — Price Prediction & Sentiment Analysis (STANDARD and DEEP only)
            if self.depth in [ResearchDepth.STANDARD, ResearchDepth.DEEP]:
                # Price prediction for flights
                if origin and travel_start:
                    try:
                        flight_data = result["data"].get("flights", [])
                        if flight_data:
                            # Extract prices from flight data
                            price_history = [
                                {"price": f.get("price", 0), "date": f.get("found_at", "")}
                                for f in flight_data if f.get("price")
                            ]
                            
                            price_prediction = await self.price_predictor.predict_best_booking_time(
                                destination=destination,
                                travel_dates={"start": travel_start, "end": travel_end or travel_start},
                                price_history=price_history if len(price_history) >= 2 else None,
                                trip_type="international" if len(origin.split()) > 1 else "domestic"
                            )
                            result["data"]["price_prediction"] = price_prediction
                    except Exception as e:
                        logger.warning(f"Price prediction failed: {str(e)}")
                
                # Sentiment analysis from blog insights
                blog_insights = result["data"].get("blog_insights", [])
                if blog_insights and self.depth == ResearchDepth.DEEP:
                    try:
                        # Extract text from blog insights
                        texts = [
                            insight.get("summary", "") + " " + " ".join(insight.get("tips", []))
                            for insight in blog_insights
                        ]
                        
                        sentiment_analysis = await self.sentiment_analyzer.analyze_destination_sentiment(
                            texts=texts,
                            destination=destination
                        )
                        result["data"]["sentiment_analysis"] = sentiment_analysis
                    except Exception as e:
                        logger.warning(f"Sentiment analysis failed: {str(e)}")

            result["data"]["external_metrics"] = external_metrics
            logger.info(
                "Auto research destination metrics",
                destination=destination,
                external_calls=external_metrics["total_calls"],
                successful_calls=external_metrics["successful_calls"],
                failed_calls=external_metrics["failed_calls"],
                total_latency_ms=external_metrics["total_latency_ms"],
            )

            # Calculate overall score
            result["overall_score"] = self._calculate_destination_score(result, interests)
            result["status"] = "completed"
            
        except Exception as e:
            result["status"] = "partial"
            result["error"] = str(e)
        
        return result
    
    async def _get_weather_for_destination(
        self, 
        destination: str, 
        travel_date: Optional[str]
    ) -> Dict[str, Any]:
        """Get weather forecast for destination"""
        # Mock implementation - in real app, geocode destination first
        month = 6  # Default June
        if travel_date:
            try:
                month = datetime.strptime(travel_date, "%Y-%m-%d").month
            except ValueError as e:
                logger.warning("Failed to parse travel date", date=travel_date, error=str(e))
                pass
        
        # Mock weather based on destination name patterns
        if any(word in destination.lower() for word in ["bali", "thailand", "maldives", "phuket", "caribbean"]):
            return {
                "temperature_c": 28,
                "condition": "Sunny",
                "humidity": 75,
                "best_time": "April to October",
                "notes": "Tropical climate, occasional rain showers"
            }
        elif any(word in destination.lower() for word in ["iceland", "norway", "alaska", "switzerland", "canada"]):
            return {
                "temperature_c": 5 if month in [12, 1, 2] else 15,
                "condition": "Cool" if month in [6, 7, 8] else "Cold",
                "humidity": 60,
                "best_time": "June to August for mild weather",
                "notes": "Pack layers, weather can change quickly"
            }
        else:
            return {
                "temperature_c": 20,
                "condition": "Pleasant",
                "humidity": 60,
                "best_time": "Spring or Fall",
                "notes": "Mediterranean-like climate"
            }
    
    async def _get_visa_info(self, destination: str, passport_country: str) -> Dict[str, Any]:
        """Get visa requirements"""
        # Extract country from destination string
        country = destination.split(",")[-1].strip() if "," in destination else destination
        return self.visa_service.check_visa_requirements(passport_country, country)
    
    async def _get_attractions_fast(self, destination: str, interests: List[str]) -> List[Dict[str, Any]]:
        """Get attractions - uses mock data for speed"""
        # Use mock data directly for fast response
        return self.attractions_service._get_mock_all_attractions(0, 0, limit=8)
    
    async def _get_events_fast(
        self, 
        destination: str, 
        start_date: Optional[str], 
        end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Get events - uses mock data for speed"""
        from datetime import datetime, timedelta
        # Parse dates or use defaults
        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError as e:
                logger.warning("Failed to parse start date", date=start_date, error=str(e))
                start = datetime.now().date()
        else:
            start = datetime.now().date()
        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError as e:
                logger.warning("Failed to parse end date", date=end_date, error=str(e))
                end = start + timedelta(days=7)
        else:
            end = start + timedelta(days=7)
        return self.events_service._get_mock_events(destination, start, end)
    
    async def _get_affordability(self, destination: str, budget_level: str) -> Dict[str, Any]:
        """Get affordability analysis"""
        country = destination.split(",")[-1].strip() if "," in destination else destination
        return self.affordability_service.analyze_affordability(
            destination_country=country,
            user_budget_level=budget_level,
            duration_days=7
        )
    
    async def _get_flights_fast(
        self, 
        origin: str, 
        destination: str, 
        departure_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Search for flights - uses mock data for speed"""
        from datetime import datetime
        date_obj = datetime.strptime(departure_date, "%Y-%m-%d").date() if departure_date else datetime.now().date()
        return self.flight_service._get_mock_flights(origin, destination, date_obj)
    
    async def _get_hotels_fast(
        self, 
        destination: str, 
        check_in: Optional[str], 
        check_out: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Search for hotels - uses mock data for speed"""
        from datetime import datetime
        check_in_obj = datetime.strptime(check_in, "%Y-%m-%d").date() if check_in else datetime.now().date()
        check_out_obj = datetime.strptime(check_out, "%Y-%m-%d").date() if check_out else check_in_obj
        return self.hotel_service._get_mock_hotels(destination, check_in_obj, check_out_obj)
    
    async def _get_restaurants(
        self,
        destination: str,
        interests: List[str],
        budget_level: str
    ) -> Dict[str, Any]:
        """Get restaurant and dining information"""
        # Extract cuisine interests
        cuisine_interests = []
        if "food" in [i.lower() for i in interests]:
            cuisine_interests = ["local"]
        
        return {
            "restaurants": self.restaurants_service.get_restaurants(
                destination=destination,
                cuisine_types=cuisine_interests,
                budget_level=budget_level
            ),
            "food_scene": self.restaurants_service.get_food_scene(destination),
            "top_picks": self.restaurants_service.get_restaurants(
                destination=destination,
                budget_level=budget_level,
                dining_style="any"
            )[:3]
        }
    
    async def _get_transport_info(self, destination: str) -> Dict[str, Any]:
        """Get local transport information"""
        return self.transport_service.get_transport_guide(destination, duration_days=7)
    
    async def _get_nightlife_info(self, destination: str) -> Dict[str, Any]:
        """Get nightlife and entertainment information"""
        return self.nightlife_service.get_nightlife_guide(destination)
    
    def _calculate_destination_score(self, result: Dict[str, Any], interests: List[str]) -> float:
        """Calculate an overall score for the destination"""
        score = 50.0  # Base score
        data = result.get("data", {})
        
        # Weather score (0-20)
        if "weather" in data:
            weather = data["weather"]
            temp = weather.get("temperature_c", 20)
            if 18 <= temp <= 28:  # Ideal temperature
                score += 20
            elif 10 <= temp <= 35:
                score += 10
        
        # Visa score (0-15)
        if "visa" in data:
            visa = data["visa"]
            if visa.get("visa_required") == False:
                score += 15
            elif visa.get("evisa_available"):
                score += 10
            elif visa.get("visa_on_arrival"):
                score += 8
        
        # Attractions score (0-20)
        if "attractions" in data:
            attractions = data["attractions"]
            score += min(20, len(attractions) * 2)
        
        # Affordability score (0-15)
        if "affordability" in data:
            affordability = data["affordability"]
            if affordability.get("budget_fit") == "within_budget":
                score += 15
            elif affordability.get("budget_fit") == "slightly_over":
                score += 8
        
        # Events score (0-10)
        if "events" in data:
            events = data["events"]
            score += min(10, len(events) * 2)
        
        # Flights score (0-10) - based on price
        if "flights" in data and data["flights"]:
            flights = data["flights"]
            cheapest = min(f.get("price", 1000) for f in flights)
            if cheapest < 300:
                score += 10
            elif cheapest < 600:
                score += 5
        
        return min(100, score)
    
    def _generate_comparison(self, destinations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comparison table for destinations"""
        comparison = {
            "categories": ["Overall Score", "Weather", "Visa", "Attractions", "Affordability", "Events"],
            "destinations": []
        }
        
        for dest in destinations:
            if dest.get("status") == "completed":
                data = dest.get("data", {})
                dest_comparison = {
                    "name": dest["name"],
                    "overall_score": dest.get("overall_score", 0),
                    "weather": data.get("weather", {}).get("temperature_c", "N/A"),
                    "visa_required": data.get("visa", {}).get("visa_required", True),
                    "attractions_count": len(data.get("attractions", [])),
                    "budget_fit": data.get("affordability", {}).get("budget_fit", "unknown"),
                    "events_count": len(data.get("events", []))
                }
                comparison["destinations"].append(dest_comparison)
        
        # Sort by overall score
        comparison["destinations"].sort(key=lambda x: x["overall_score"], reverse=True)
        
        return comparison
    
    def _generate_recommendations(
        self, 
        destinations: List[Dict[str, Any]], 
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Sort by score
        sorted_dests = sorted(
            [d for d in destinations if d.get("status") == "completed"],
            key=lambda x: x.get("overall_score", 0),
            reverse=True
        )
        
        for i, dest in enumerate(sorted_dests[:3]):
            data = dest.get("data", {})
            ctx  = data.get("context", {})

            # Generate personalised reasons using full questionnaire context
            reasons = []
            if dest.get("overall_score", 0) > 80:
                reasons.append("Excellent overall match for your preferences")
            if "visa" in data and not data["visa"].get("visa_required"):
                reasons.append("No visa required")
            if "weather" in data:
                temp = data["weather"].get("temperature_c", 20)
                if 20 <= temp <= 30:
                    reasons.append(f"Great weather ({temp}°C)")
            if "affordability" in data and data["affordability"].get("budget_fit") == "within_budget":
                reasons.append("Fits your budget")
            if "events" in data and len(data["events"]) > 0:
                reasons.append(f"{len(data['events'])} events during your stay")

            # Questionnaire-aware reasons
            traveling_with = ctx.get("traveling_with", "solo")
            if traveling_with == "family" and ctx.get("has_kids"):
                kid_friendly = [a for a in data.get("attractions", []) if a.get("kid_friendly")]
                if kid_friendly:
                    reasons.append(f"{len(kid_friendly)} kid-friendly attractions found")
            if traveling_with == "couple":
                reasons.append("Great romantic getaway destination")
            if traveling_with == "group" and "nightlife" in data:
                reasons.append("Excellent nightlife scene for groups")
            dietary = ctx.get("dietary_restrictions", [])
            if dietary and "none" not in [d.lower() for d in dietary]:
                reasons.append(f"Accommodates {', '.join(dietary)} dietary needs")
            accessibility = ctx.get("accessibility_needs", [])
            if accessibility and "none" not in [a.lower() for a in accessibility]:
                reasons.append("Accessibility information included")
            pace = ctx.get("pace_preference", "moderate")
            if pace == "relaxed":
                reasons.append("Ideal for a relaxed, unhurried pace")
            elif pace == "busy":
                reasons.append("Packed with activities to keep you busy")
            
            recommendations.append({
                "rank": i + 1,
                "destination": dest["name"],
                "score": dest.get("overall_score", 0),
                "reasons": reasons,
                "highlights": self._extract_highlights(data),
                "estimated_cost": data.get("affordability", {}).get("estimated_total_cost", {})
            })
        
        return recommendations
    
    def _extract_highlights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key highlights from research data"""
        highlights = {}
        
        if "attractions" in data and data["attractions"]:
            highlights["top_attractions"] = [
                a.get("name", "") for a in data["attractions"][:3]
            ]
        
        if "events" in data and data["events"]:
            highlights["top_events"] = [
                e.get("name", "") for e in data["events"][:2]
            ]
        
        if "hotels" in data and data["hotels"]:
            cheapest = min(data["hotels"], key=lambda x: x.get("price_per_night", 9999))
            highlights["hotel_from"] = cheapest.get("price_per_night", 0)
        
        if "flights" in data and data["flights"]:
            cheapest = min(data["flights"], key=lambda x: x.get("price", 9999))
            highlights["flight_from"] = cheapest.get("price", 0)
        
        # New data sources
        if "restaurants" in data and data["restaurants"]:
            restaurants_data = data["restaurants"]
            if "top_picks" in restaurants_data and restaurants_data["top_picks"]:
                highlights["dining_highlight"] = restaurants_data["top_picks"][0].get("name", "")
            if "food_scene" in restaurants_data and restaurants_data["food_scene"]:
                food_scene = restaurants_data["food_scene"].get("food_scene", {})
                if "signature_dishes" in food_scene:
                    highlights["signature_dish"] = food_scene["signature_dishes"][0] if food_scene["signature_dishes"] else ""
        
        if "transport" in data and data["transport"]:
            transport_data = data["transport"]
            if "transport_options" in transport_data:
                options = transport_data["transport_options"]
                if "overview" in options:
                    highlights["transport_tip"] = options["overview"][:50] + "..."
        
        if "nightlife" in data and data["nightlife"]:
            nightlife_data = data["nightlife"]
            if "scene_overview" in nightlife_data:
                scene = nightlife_data["scene_overview"]
                if "famous_for" in scene.get("nightlife", {}):
                    highlights["nightlife_highlight"] = scene["nightlife"]["famous_for"]
        
        return highlights


# Convenience function
async def run_auto_research(
    preferences: Dict[str, Any],
    job_id: Optional[str] = None,
    progress_callback = None,
    depth: Optional[ResearchDepth] = None
) -> Dict[str, Any]:
    """Run auto research with optional progress tracking"""
    agent = AutoResearchAgent(job_id=job_id, depth=depth or ResearchDepth.STANDARD)
    if progress_callback:
        agent.set_progress_callback(progress_callback)
    return await agent.research_from_preferences(preferences, depth=depth)
