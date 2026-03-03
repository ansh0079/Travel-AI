from datetime import date, timedelta
import httpx

from app.utils.cache_service import CacheService
from app.utils.logging_config import get_logger
from app.config import get_settings

logger = get_logger(__name__)


class WeatherServiceError(Exception):
    """Custom exception for weather service errors"""
    pass


class WeatherService:
    def __init__(self):
        self.cache = CacheService()
        self.settings = get_settings()
        self.api_key = self.settings.openweather_api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def _fetch_openweather(self, lat: float, lon: float, date_obj: date) -> dict:
        """Fetch weather from OpenWeatherMap API"""
        if not self.api_key:
            logger.debug("OpenWeather API key not configured, using mock data")
            return self._get_mock_weather(lat, lon, date_obj)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "appid": self.api_key,
                        "units": "metric",
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Parse forecast data
                if "list" in data and len(data["list"]) > 0:
                    forecast = data["list"][0]
                    return {
                        "temperature": round(forecast["main"]["temp"]),
                        "condition": forecast["weather"][0]["description"],
                        "humidity": forecast["main"]["humidity"],
                        "feels_like": round(forecast["main"]["feels_like"]),
                        "wind_speed": forecast["wind"]["speed"],
                    }
                
                return self._get_mock_weather(lat, lon, date_obj)
                
        except httpx.HTTPStatusError as e:
            logger.error("Weather API HTTP error", status_code=e.response.status_code)
            raise WeatherServiceError(f"Weather API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error("Weather API request error", error=str(e))
            raise WeatherServiceError(f"Weather API unavailable: {str(e)}")
        except Exception as e:
            logger.error("Unexpected weather API error", error=str(e))
            raise WeatherServiceError(f"Unexpected error: {str(e)}")

    def _get_mock_weather(self, lat: float, lon: float, date_obj: date) -> dict:
        """Fallback mock weather data"""
        logger.debug("Returning mock weather data as fallback")
        return {
            "temperature": 22,
            "condition": "Partly Cloudy",
            "humidity": 55,
            "feels_like": 22,
            "wind_speed": 10,
            "is_mock": True,
        }

    async def get_weather(self, lat: float, lon: float, date_obj: date) -> dict:
        """Get weather with caching and fallback"""
        cache_key = CacheService.weather_key(lat, lon, str(date_obj))

        # Try cache first
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info("Weather cache hit", lat=lat, lon=lon, date=str(date_obj))
                return cached
        except Exception as e:
            logger.warning("Cache read error", error=str(e))

        logger.info("Weather cache miss", lat=lat, lon=lon, date=str(date_obj))
        
        # Fetch from API
        try:
            weather = await self._fetch_openweather(lat, lon, date_obj)
            # Cache for 1 hour
            try:
                await self.cache.set(cache_key, weather, timedelta(hours=1))
            except Exception as e:
                logger.warning("Cache write error", error=str(e))
            return weather
        except WeatherServiceError as e:
            logger.warning("Weather service error, returning mock data", error=str(e))
            return self._get_mock_weather(lat, lon, date_obj)
        except Exception as e:
            logger.error("Unexpected error in get_weather", error=str(e))
            return self._get_mock_weather(lat, lon, date_obj)