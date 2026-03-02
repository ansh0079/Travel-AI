from datetime import timedelta

from app.utils.cache_service import CacheService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class AttractionsService:
    def __init__(self):
        self.cache = CacheService()

    async def _fetch_attractions_from_api(self, destination_id: str, category: str) -> list:
        logger.debug("Fetching fresh attractions data from external API.")
        # Simulating an API response
        return [{"name": "Eiffel Tower", "type": "landmark"}]

    async def get_natural_attractions(self, destination_id: str) -> list:
        category = "natural"
        cache_key = CacheService.attractions_key(destination_id, category)

        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("Attractions cache hit", destination=destination_id, category=category)
            return cached

        logger.info("Attractions cache miss", destination=destination_id, category=category)
        try:
            attractions = await self._fetch_attractions_from_api(destination_id, category)
            await self.cache.set(cache_key, attractions, timedelta(hours=6))
            return attractions
        except Exception as e:
            logger.error("Attractions API error, returning empty list.", error=str(e), destination=destination_id)
            return []