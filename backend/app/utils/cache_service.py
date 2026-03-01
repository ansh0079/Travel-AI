"""
Redis caching service for improved performance
Provides caching for API responses, weather data, and other expensive operations
"""
import json
import redis.asyncio as redis
from typing import Optional, Any, Dict
from datetime import timedelta
from app.config import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class CacheService:
    """Redis caching service"""
    
    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None
        self._enabled = False
    
    async def connect(self) -> bool:
        """Connect to Redis server"""
        if not self.settings.redis_url:
            logger.info("Redis URL not configured, caching disabled")
            return False
        
        try:
            self._redis = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            self._enabled = True
            logger.info("Connected to Redis successfully")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self._enabled = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._enabled or not self._redis:
            return None
        
        try:
            value = await self._redis.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            logger.debug(f"Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache with optional expiration"""
        if not self._enabled or not self._redis:
            return False
        
        try:
            serialized = json.dumps(value)
            if expire:
                await self._redis.setex(key, int(expire.total_seconds()), serialized)
            else:
                await self._redis.set(key, serialized)
            logger.debug(f"Cache set: {key}")
            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._enabled or not self._redis:
            return False
        
        try:
            await self._redis.delete(key)
            logger.debug(f"Cache delete: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._enabled or not self._redis:
            return False
        
        try:
            return await self._redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching a pattern"""
        if not self._enabled or not self._redis:
            return False
        
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} keys matching pattern: {pattern}")
            return True
        except Exception as e:
            logger.error(f"Error clearing pattern {pattern}: {e}")
            return False
    
    # Convenience methods for common caching patterns
    
    async def get_or_set(
        self,
        key: str,
        factory: callable,
        expire: timedelta = timedelta(hours=1)
    ) -> Any:
        """Get from cache or set using factory function"""
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        value = await factory()
        await self.set(key, value, expire)
        return value
    
    # Cache key helpers
    
    @staticmethod
    def weather_key(lat: float, lon: float, date: str) -> str:
        """Generate cache key for weather data"""
        return f"weather:{lat}:{lon}:{date}"
    
    @staticmethod
    def visa_key(passport_country: str, destination_country: str) -> str:
        """Generate cache key for visa requirements"""
        return f"visa:{passport_country}:{destination_country}"
    
    @staticmethod
    def attractions_key(lat: float, lon: float, limit: int = 10) -> str:
        """Generate cache key for attractions"""
        return f"attractions:{lat}:{lon}:{limit}"
    
    @staticmethod
    def events_key(city: str, start_date: str, end_date: str) -> str:
        """Generate cache key for events"""
        return f"events:{city}:{start_date}:{end_date}"
    
    @staticmethod
    def destination_key(destination_id: str) -> str:
        """Generate cache key for destination details"""
        return f"destination:{destination_id}"
    
    @staticmethod
    def recommendations_key(user_prefs_hash: str) -> str:
        """Generate cache key for recommendations"""
        return f"recommendations:{user_prefs_hash}"
    
    @staticmethod
    def hotel_key(city: str, check_in: str, check_out: str, adults: int, max_price: Optional[float]) -> str:
        """Generate cache key for hotel search"""
        return f"hotel:{city}:{check_in}:{check_out}:{adults}:{max_price}"
    
    @staticmethod
    def affordability_key(country_code: str, travel_style: str) -> str:
        """Generate cache key for affordability data"""
        return f"affordability:{country_code}:{travel_style}"


# Global cache instance
cache_service = CacheService()


async def get_cache() -> CacheService:
    """Get cache service instance"""
    return cache_service


async def init_cache() -> bool:
    """Initialize cache connection"""
    return await cache_service.connect()


async def close_cache():
    """Close cache connection"""
    await cache_service.disconnect()
