from datetime import timedelta

from app.utils.cache_service import CacheService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class VisaService:
    def __init__(self):
        self.cache = CacheService()

    async def _fetch_visa_info(self, passport_country: str, destination_country: str) -> dict:
        logger.debug("Fetching fresh visa data from external API.")
        # Simulating an API response
        return {"requirement": "visa_free", "duration_days": 90}

    async def get_visa_requirements(self, passport_country: str, destination_country: str) -> dict:
        cache_key = CacheService.visa_key(passport_country, destination_country)

        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("Visa cache hit", passport=passport_country, dest=destination_country)
            return cached

        logger.info("Visa cache miss", passport=passport_country, dest=destination_country)
        try:
            visa_info = await self._fetch_visa_info(passport_country, destination_country)
            await self.cache.set(cache_key, visa_info, timedelta(hours=24))
            return visa_info
        except Exception as e:
            logger.error("Visa API error, returning default.", error=str(e), passport=passport_country, dest=destination_country)
            return {"requirement": "unknown", "duration_days": None}