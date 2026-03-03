from datetime import timedelta
import httpx

from app.utils.cache_service import CacheService
from app.utils.logging_config import get_logger
from app.config import get_settings

logger = get_logger(__name__)


class AttractionsServiceError(Exception):
    """Custom exception for attractions service errors"""
    pass


class AttractionsService:
    def __init__(self):
        self.cache = CacheService()
        self.settings = get_settings()
        self.api_key = self.settings.google_places_api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place"

    async def _fetch_attractions_from_api(self, lat: float, lon: float, category: str, radius: int = 5000) -> list:
        """Fetch attractions from Google Places API"""
        if not self.api_key:
            logger.debug("Google Places API key not configured, using mock data")
            return self._get_mock_attractions(lat, lon, category)

        # Map category to Google Places types
        type_mapping = {
            "natural": "natural_feature",
            "landmark": "tourist_attraction",
            "museum": "museum",
            "park": "park",
            "beach": "natural_feature",
        }
        place_type = type_mapping.get(category, "tourist_attraction")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/nearbysearch/json",
                    params={
                        "location": f"{lat},{lon}",
                        "radius": radius,
                        "type": place_type,
                        "key": self.api_key,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "OK":
                    logger.warning("Google Places API error", status=data.get("status"))
                    return self._get_mock_attractions(lat, lon, category)
                
                attractions = []
                for place in data.get("results", [])[:10]:
                    attractions.append({
                        "name": place.get("name", "Unknown"),
                        "type": category,
                        "rating": place.get("rating", 0),
                        "user_ratings_total": place.get("user_ratings_total", 0),
                        "vicinity": place.get("vicinity", ""),
                        "place_id": place.get("place_id", ""),
                        "lat": place.get("geometry", {}).get("location", {}).get("lat", lat),
                        "lon": place.get("geometry", {}).get("location", {}).get("lng", lon),
                    })
                
                return attractions
                
        except httpx.HTTPStatusError as e:
            logger.error("Attractions API HTTP error", status_code=e.response.status_code)
            raise AttractionsServiceError(f"Attractions API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error("Attractions API request error", error=str(e))
            raise AttractionsServiceError(f"Attractions API unavailable: {str(e)}")
        except Exception as e:
            logger.error("Unexpected attractions API error", error=str(e))
            raise AttractionsServiceError(f"Unexpected error: {str(e)}")

    def _get_mock_attractions(self, lat: float, lon: float, category: str) -> list:
        """Fallback mock attractions data"""
        logger.debug("Returning mock attractions data as fallback")
        return [
            {"name": "City Center", "type": category, "rating": 4.5, "lat": lat, "lon": lon},
            {"name": "Historic District", "type": category, "rating": 4.3, "lat": lat + 0.01, "lon": lon + 0.01},
            {"name": "Local Museum", "type": category, "rating": 4.2, "lat": lat - 0.01, "lon": lon - 0.01},
        ]

    async def get_natural_attractions(self, lat: float, lon: float, limit: int = 10) -> list:
        """Get natural attractions with caching"""
        category = "natural"
        cache_key = CacheService.attractions_key(f"{lat},{lon}", category)

        # Try cache first
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info("Attractions cache hit", lat=lat, lon=lon, category=category)
                return cached[:limit]
        except Exception as e:
            logger.warning("Cache read error", error=str(e))

        logger.info("Attractions cache miss", lat=lat, lon=lon, category=category)
        
        try:
            attractions = await self._fetch_attractions_from_api(lat, lon, category)
            # Cache for 6 hours (attractions change rarely)
            try:
                await self.cache.set(cache_key, attractions, timedelta(hours=6))
            except Exception as e:
                logger.warning("Cache write error", error=str(e))
            return attractions[:limit]
        except AttractionsServiceError as e:
            logger.warning("Attractions service error, returning mock data", error=str(e))
            return self._get_mock_attractions(lat, lon, category)[:limit]
        except Exception as e:
            logger.error("Unexpected error in get_natural_attractions", error=str(e))
            return self._get_mock_attractions(lat, lon, category)[:limit]

    async def get_all_attractions(self, lat: float, lon: float, limit: int = 15) -> list:
        """Get all types of attractions with caching"""
        category = "all"
        cache_key = CacheService.attractions_key(f"{lat},{lon}", category)

        # Try cache first
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info("All attractions cache hit", lat=lat, lon=lon)
                return cached[:limit]
        except Exception as e:
            logger.warning("Cache read error", error=str(e))

        logger.info("All attractions cache miss", lat=lat, lon=lon)
        
        try:
            # Fetch from multiple categories
            all_attractions = []
            for cat in ["landmark", "museum", "park", "natural"]:
                try:
                    attrs = await self._fetch_attractions_from_api(lat, lon, cat, radius=3000)
                    all_attractions.extend(attrs)
                except Exception as e:
                    logger.warning(f"Failed to fetch {cat} attractions", error=str(e))
            
            # Deduplicate by name
            seen = set()
            unique = []
            for attr in all_attractions:
                if attr["name"] not in seen:
                    seen.add(attr["name"])
                    unique.append(attr)
            
            # Cache for 6 hours
            try:
                await self.cache.set(cache_key, unique, timedelta(hours=6))
            except Exception as e:
                logger.warning("Cache write error", error=str(e))
            return unique[:limit]
        except Exception as e:
            logger.error("Unexpected error in get_all_attractions", error=str(e))
            return self._get_mock_attractions(lat, lon, "landmark")[:limit]