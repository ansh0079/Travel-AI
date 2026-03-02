from datetime import date, timedelta

from app.utils.cache_service import CacheService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class WeatherService:
    def __init__(self):
        self.cache = CacheService()

    async def _fetch_openweather(self, lat: float, lon: float, date_obj: date) -> dict:
        # In a real implementation, this would make an HTTP request to the OpenWeather API.
        logger.debug("Fetching fresh weather data from external API.")
        # Simulating an API response
        return {"temperature": 25, "condition": "Clear", "humidity": 60}

    def _get_mock_weather(self, lat: float, lon: float, date_obj: date) -> dict:
        # Fallback data in case of API failure
        logger.debug("Returning mock weather data as fallback.")
        return {"temperature": 22, "condition": "Partly Cloudy", "humidity": 55}

    async def get_weather(self, lat: float, lon: float, date_obj: date) -> dict:
        cache_key = CacheService.weather_key(lat, lon, str(date_obj))

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("Weather cache hit", lat=lat, lon=lon, date=str(date_obj))
            return cached

        logger.info("Weather cache miss", lat=lat, lon=lon, date=str(date_obj))
        # Fetch from API
        try:
            weather = await self._fetch_openweather(lat, lon, date_obj)
            # Cache for 1 hour
            await self.cache.set(cache_key, weather, timedelta(hours=1))
            return weather
        except Exception as e:
            logger.warning("Weather API error, returning mock data.", error=str(e), lat=lat, lon=lon)
            return self._get_mock_weather(lat, lon, date_obj)