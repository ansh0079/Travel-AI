from datetime import timedelta
import httpx

from app.utils.cache_service import CacheService
from app.utils.logging_config import get_logger
from app.config import get_settings

logger = get_logger(__name__)


class VisaServiceError(Exception):
    """Custom exception for visa service errors"""
    pass


class VisaService:
    def __init__(self):
        self.cache = CacheService()
        self.settings = get_settings()
        self.api_key = self.settings.visa_requirements_api_key
        self.base_url = "https://visarequirements.p.rapidapi.com"  # Example API

    async def _fetch_visa_info(self, passport_country: str, destination_country: str) -> dict:
        """Fetch visa requirements from API"""
        if not self.api_key:
            logger.debug("Visa API key not configured, using mock data")
            return self._get_mock_visa_requirements(passport_country, destination_country)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/visa-requirements",
                    params={
                        "passport_country": passport_country,
                        "destination_country": destination_country,
                    },
                    headers={
                        "X-RapidAPI-Key": self.api_key,
                        "X-RapidAPI-Host": "visarequirements.p.rapidapi.com"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "requirement": data.get("visa_requirement", "unknown"),
                    "duration_days": data.get("allowed_stay", 90),
                    "notes": data.get("notes", ""),
                    "is_mock": False,
                }
                
        except httpx.HTTPStatusError as e:
            logger.error("Visa API HTTP error", status_code=e.response.status_code)
            raise VisaServiceError(f"Visa API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error("Visa API request error", error=str(e))
            raise VisaServiceError(f"Visa API unavailable: {str(e)}")
        except Exception as e:
            logger.error("Unexpected visa API error", error=str(e))
            raise VisaServiceError(f"Unexpected error: {str(e)}")

    def _get_mock_visa_requirements(self, passport_country: str, destination_country: str) -> dict:
        """Fallback mock visa data"""
        logger.debug("Returning mock visa data as fallback")
        # Common visa-free countries for US passport
        visa_free_countries = ["FR", "GB", "DE", "IT", "ES", "JP", "AU", "NZ", "CA", "MX"]
        
        if destination_country.upper() in visa_free_countries:
            return {
                "requirement": "visa_free",
                "duration_days": 90,
                "notes": "Visa-free for tourism/business",
                "is_mock": True,
            }
        else:
            return {
                "requirement": "visa_required",
                "duration_days": None,
                "notes": "Visa required - check embassy website",
                "is_mock": True,
            }

    async def get_visa_requirements(self, passport_country: str, destination_country: str) -> dict:
        """Get visa requirements with caching and fallback"""
        cache_key = CacheService.visa_key(passport_country, destination_country)

        # Try cache first
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info("Visa cache hit", passport=passport_country, dest=destination_country)
                return cached
        except Exception as e:
            logger.warning("Cache read error", error=str(e))

        logger.info("Visa cache miss", passport=passport_country, dest=destination_country)
        
        try:
            visa_info = await self._fetch_visa_info(passport_country, destination_country)
            # Cache for 24 hours (visa requirements change rarely)
            try:
                await self.cache.set(cache_key, visa_info, timedelta(hours=24))
            except Exception as e:
                logger.warning("Cache write error", error=str(e))
            return visa_info
        except VisaServiceError as e:
            logger.warning("Visa service error, returning mock data", error=str(e))
            return self._get_mock_visa_requirements(passport_country, destination_country)
        except Exception as e:
            logger.error("Unexpected error in get_visa_requirements", error=str(e))
            return self._get_mock_visa_requirements(passport_country, destination_country)

    def get_visa_summary(self, visa_data: dict) -> str:
        """Build a short human-readable summary for API responses."""
        requirement = (visa_data or {}).get("requirement", "unknown")
        duration_days = (visa_data or {}).get("duration_days")
        notes = (visa_data or {}).get("notes", "")

        requirement_map = {
            "visa_free": "Visa-free travel",
            "visa_on_arrival": "Visa on arrival",
            "evisa": "eVisa required",
            "visa_required": "Visa required before travel",
            "unknown": "Visa rules unavailable",
        }
        label = requirement_map.get(requirement, str(requirement).replace("_", " ").title())

        if isinstance(duration_days, int) and duration_days > 0:
            return f"{label} for up to {duration_days} days. {notes}".strip()
        if notes:
            return f"{label}. {notes}".strip()
        return label
