"""
TripAdvisor Content API Service
Docs: https://tripadvisor-content-api.readme.io/reference/overview
Free tier: 5,000 calls/month
"""

import httpx
import asyncio
import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)

TA_BASE = "https://api.content.tripadvisor.com/api/v1"

# Simple in-memory cache (city_key → {data, timestamp})
_CACHE: dict = {}
_CACHE_TTL = 3600  # 1 hour — respect the free tier limit


def _cache_get(key: str):
    import time
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data):
    import time
    _CACHE[key] = {"data": data, "ts": time.time()}


class TripAdvisorService:
    def __init__(self):
        self.settings = get_settings()

    @property
    def api_key(self) -> Optional[str]:
        return self.settings.tripadvisor_api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict) -> dict:
        """Make a GET request to the TripAdvisor Content API."""
        if not self.api_key:
            return {}
        params["key"] = self.api_key
        params.setdefault("language", "en")
        url = f"{TA_BASE}{path}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    async def _search_location(self, city: str) -> Optional[dict]:
        """Return the top geo result for a city name."""
        cache_key = f"loc:{city.lower()}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._get("/location/search", {
                "searchQuery": city,
                "category": "geos",
            })
            results = data.get("data", [])
            loc = results[0] if results else None
            _cache_set(cache_key, loc)
            return loc
        except Exception as e:
            logger.warning(f"TripAdvisor location search failed for {city}: {e}")
            return None

    async def _nearby(self, lat: float, lon: float, category: str, limit: int = 10) -> list:
        """Nearby search for a category around lat/lon."""
        try:
            data = await self._get("/location/nearby_search", {
                "latLong": f"{lat},{lon}",
                "category": category,
                "radius": 20,
                "radiusUnit": "km",
            })
            return (data.get("data") or [])[:limit]
        except Exception as e:
            logger.warning(f"TripAdvisor nearby search failed ({category}): {e}")
            return []

    async def _details(self, location_id: str) -> dict:
        """Fetch details for a single location."""
        cache_key = f"det:{location_id}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            data = await self._get(f"/location/{location_id}/details", {
                "currency": "USD",
            })
            _cache_set(cache_key, data)
            return data
        except Exception as e:
            logger.warning(f"TripAdvisor details failed for {location_id}: {e}")
            return {}

    async def _photos(self, location_id: str, limit: int = 5) -> list:
        """Fetch photos for a location."""
        try:
            data = await self._get(f"/location/{location_id}/photos", {"limit": limit})
            return data.get("data", [])[:limit]
        except Exception as e:
            logger.warning(f"TripAdvisor photos failed for {location_id}: {e}")
            return []

    async def _reviews(self, location_id: str, limit: int = 5) -> list:
        """Fetch reviews for a location."""
        try:
            data = await self._get(f"/location/{location_id}/reviews", {"limit": limit})
            return data.get("data", [])[:limit]
        except Exception as e:
            logger.warning(f"TripAdvisor reviews failed for {location_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_city_attractions(self, city: str, limit: int = 8) -> dict:
        """Real TripAdvisor attractions for a city."""
        if not self.enabled:
            return {"enabled": False, "attractions": []}

        cache_key = f"attr:{city.lower()}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        loc = await self._search_location(city)
        if not loc:
            return {"enabled": True, "attractions": [], "error": "City not found"}

        lat = float(loc.get("latitude", 0) or 0)
        lon = float(loc.get("longitude", 0) or 0)

        nearby = await self._nearby(lat, lon, "attractions", limit)

        # Fetch details for each in parallel (max 5 to save quota)
        details_tasks = [self._details(item["location_id"]) for item in nearby[:5]]
        details_list = await asyncio.gather(*details_tasks)

        attractions = []
        for item, det in zip(nearby[:5], details_list):
            photo_url = None
            if det.get("photo", {}).get("images", {}).get("medium", {}).get("url"):
                photo_url = det["photo"]["images"]["medium"]["url"]

            attractions.append({
                "location_id": item["location_id"],
                "name": item.get("name", ""),
                "rating": float(det.get("rating") or 0),
                "num_reviews": int(det.get("num_reviews") or 0),
                "category": (det.get("category", {}) or {}).get("localized_name", "Attraction"),
                "subcategory": [(s.get("localized_name", "")) for s in (det.get("subcategory") or [])],
                "description": (det.get("description") or "")[:300],
                "price_level": det.get("price_level", ""),
                "address": item.get("address_obj", {}).get("address_string", ""),
                "photo_url": photo_url,
                "web_url": det.get("web_url", ""),
                "ranking_string": det.get("ranking_string", ""),
            })

        result = {
            "enabled": True,
            "city": city,
            "location_id": loc["location_id"],
            "attractions": attractions,
        }
        _cache_set(cache_key, result)
        return result

    async def get_city_hotels(self, city: str, limit: int = 6) -> dict:
        """Real TripAdvisor hotels for a city."""
        if not self.enabled:
            return {"enabled": False, "hotels": []}

        cache_key = f"hotels:{city.lower()}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        loc = await self._search_location(city)
        if not loc:
            return {"enabled": True, "hotels": [], "error": "City not found"}

        lat = float(loc.get("latitude", 0) or 0)
        lon = float(loc.get("longitude", 0) or 0)
        nearby = await self._nearby(lat, lon, "hotels", limit)

        details_tasks = [self._details(item["location_id"]) for item in nearby[:6]]
        details_list = await asyncio.gather(*details_tasks)

        hotels = []
        for item, det in zip(nearby[:6], details_list):
            photo_url = None
            if det.get("photo", {}).get("images", {}).get("medium", {}).get("url"):
                photo_url = det["photo"]["images"]["medium"]["url"]

            hotels.append({
                "location_id": item["location_id"],
                "name": item.get("name", ""),
                "rating": float(det.get("rating") or 0),
                "num_reviews": int(det.get("num_reviews") or 0),
                "price_level": det.get("price_level", ""),
                "hotel_class": det.get("hotel_class", ""),
                "address": item.get("address_obj", {}).get("address_string", ""),
                "photo_url": photo_url,
                "web_url": det.get("web_url", ""),
                "ranking_string": det.get("ranking_string", ""),
                "amenities": [a.get("localized_name", "") for a in (det.get("amenities") or [])[:6]],
            })

        result = {"enabled": True, "city": city, "hotels": hotels}
        _cache_set(cache_key, result)
        return result

    async def get_city_restaurants(self, city: str, limit: int = 8) -> dict:
        """Real TripAdvisor restaurants for a city."""
        if not self.enabled:
            return {"enabled": False, "restaurants": []}

        cache_key = f"rest:{city.lower()}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        loc = await self._search_location(city)
        if not loc:
            return {"enabled": True, "restaurants": [], "error": "City not found"}

        lat = float(loc.get("latitude", 0) or 0)
        lon = float(loc.get("longitude", 0) or 0)
        nearby = await self._nearby(lat, lon, "restaurants", limit)

        details_tasks = [self._details(item["location_id"]) for item in nearby[:8]]
        details_list = await asyncio.gather(*details_tasks)

        restaurants = []
        for item, det in zip(nearby[:8], details_list):
            photo_url = None
            if det.get("photo", {}).get("images", {}).get("medium", {}).get("url"):
                photo_url = det["photo"]["images"]["medium"]["url"]

            cuisine_list = [c.get("localized_name", "") for c in (det.get("cuisine") or [])[:3]]

            restaurants.append({
                "location_id": item["location_id"],
                "name": item.get("name", ""),
                "rating": float(det.get("rating") or 0),
                "num_reviews": int(det.get("num_reviews") or 0),
                "price_level": det.get("price_level", ""),
                "cuisine": cuisine_list,
                "address": item.get("address_obj", {}).get("address_string", ""),
                "photo_url": photo_url,
                "web_url": det.get("web_url", ""),
                "ranking_string": det.get("ranking_string", ""),
                "dietary_restrictions": [d.get("localized_name", "") for d in (det.get("dietary_restrictions") or [])],
            })

        result = {"enabled": True, "city": city, "restaurants": restaurants}
        _cache_set(cache_key, result)
        return result

    async def get_location_reviews(self, location_id: str) -> dict:
        """Fetch top reviews for a specific location."""
        if not self.enabled:
            return {"enabled": False, "reviews": []}

        reviews_raw = await self._reviews(location_id, limit=5)
        reviews = []
        for r in reviews_raw:
            reviews.append({
                "id": r.get("id"),
                "title": r.get("title", ""),
                "text": (r.get("text") or "")[:400],
                "rating": r.get("rating", 0),
                "published_date": r.get("published_date", ""),
                "user": {
                    "username": (r.get("user") or {}).get("username", "Anonymous"),
                    "user_location": (r.get("user") or {}).get("user_location", {}).get("name", ""),
                },
            })
        return {"enabled": True, "reviews": reviews}
