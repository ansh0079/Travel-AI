"""
Caching Layer for Travel AI
Supports both Redis (production) and in-memory (development) caching
"""
import asyncio
import json
import hashlib
import time
from typing import Any, Optional, Callable, TypeVar, Union
from datetime import datetime, timedelta
from functools import wraps
import logging

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Try to import redis, but don't fail if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory caching")

from app.config import get_settings


T = TypeVar('T')


class CacheBackend:
    """Base cache backend interface."""
    
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raise NotImplementedError
    
    async def delete(self, key: str) -> None:
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        raise NotImplementedError


class RedisCache(CacheBackend):
    """Redis cache backend for production."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Lazy connection to Redis."""
        if not self._redis:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                self._redis = None
    
    async def get(self, key: str) -> Optional[Any]:
        if not self._redis:
            await self.connect()
        
        if not self._redis:
            return None
        
        try:
            value = await self._redis.get(key)
            if value:
                data = json.loads(value)
                # Check if expired
                if 'expires_at' in data and data['expires_at']:
                    if datetime.now().isoformat() > data['expires_at']:
                        await self.delete(key)
                        return None
                return data.get('value')
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if not self._redis:
            await self.connect()
        
        if not self._redis:
            return
        
        try:
            data = {
                'value': value,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=ttl)).isoformat() if ttl else None
            }
            
            if ttl:
                await self._redis.setex(key, ttl, json.dumps(data))
            else:
                await self._redis.set(key, json.dumps(data))
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
    
    async def delete(self, key: str) -> None:
        if not self._redis:
            return
        
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        if not self._redis:
            return False
        
        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            return False
    
    async def close(self):
        if self._redis:
            await self._redis.close()


class InMemoryCache(CacheBackend):
    """In-memory cache backend for development/testing."""
    
    def __init__(self):
        self._cache: dict = {}
        self._expiry: dict = {}
        self._hits = 0
        self._misses = 0
        self._sets = 0
    
    async def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            self._misses += 1
            return None
        
        # Check expiry
        if key in self._expiry and self._expiry[key]:
            if datetime.now() > self._expiry[key]:
                await self.delete(key)
                self._misses += 1
                return None
        
        self._hits += 1
        return self._cache[key]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._cache[key] = value
        self._sets += 1
        
        if ttl:
            self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
        elif key in self._expiry:
            del self._expiry[key]
    
    async def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
        if key in self._expiry:
            del self._expiry[key]
    
    async def exists(self, key: str) -> bool:
        return key in self._cache and key not in self._expiry
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self._hits,
            'misses': self._misses,
            'sets': self._sets,
            'hit_rate': round(hit_rate, 2),
            'keys_count': len(self._cache),
            'memory_usage_estimate': f"{len(str(self._cache)) / 1024:.2f} KB"
        }
    
    async def cleanup_expired(self):
        """Remove expired entries."""
        now = datetime.now()
        expired = [k for k, v in self._expiry.items() if v and now > v]
        for key in expired:
            await self.delete(key)


class TravelCache:
    """
    Main cache manager for Travel AI.
    Automatically uses Redis if available, falls back to in-memory.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.backend: CacheBackend
        
        # Initialize appropriate backend
        if REDIS_AVAILABLE and self.settings.redis_url:
            self.backend = RedisCache(self.settings.redis_url)
            logger.info("Using Redis cache backend")
        else:
            self.backend = InMemoryCache()
            logger.info("Using in-memory cache backend")
        
        # Default TTLs (in seconds)
        self.TTL_FLIGHTS = 3600  # 1 hour
        self.TTL_HOTELS = 3600  # 1 hour
        self.TTL_RESTAURANTS = 7200  # 2 hours
        self.TTL_EVENTS = 1800  # 30 minutes
        self.TTL_WEATHER = 900  # 15 minutes
        self.TTL_BLOGS = 86400  # 24 hours
        self.TTL_SAFETY = 43200  # 12 hours
        self.TTL_RESEARCH = 3600  # 1 hour
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters."""
        # Create sorted string of kwargs for consistent hashing
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        hash_obj = hashlib.md5(params_str.encode())
        hash_hex = hash_obj.hexdigest()[:12]
        return f"travel:{prefix}:{hash_hex}"
    
    async def get(self, key: str) -> Optional[Any]:
        return await self.backend.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self.backend.set(key, value, ttl)
    
    async def delete(self, key: str) -> None:
        await self.backend.delete(key)
    
    async def exists(self, key: str) -> bool:
        return await self.backend.exists(key)
    
    # Convenience methods for specific data types
    
    async def get_flights(self, origin: str, destination: str, date: str) -> Optional[list]:
        key = self._generate_key("flights", origin=origin, destination=destination, date=date)
        return await self.get(key)
    
    async def set_flights(self, origin: str, destination: str, date: str, data: list) -> None:
        key = self._generate_key("flights", origin=origin, destination=destination, date=date)
        await self.set(key, data, self.TTL_FLIGHTS)
    
    async def get_hotels(self, destination: str, check_in: str, check_out: str) -> Optional[list]:
        key = self._generate_key("hotels", destination=destination, check_in=check_in, check_out=check_out)
        return await self.get(key)
    
    async def set_hotels(self, destination: str, check_in: str, check_out: str, data: list) -> None:
        key = self._generate_key("hotels", destination=destination, check_in=check_in, check_out=check_out)
        await self.set(key, data, self.TTL_HOTELS)
    
    async def get_restaurants(self, destination: str) -> Optional[list]:
        key = self._generate_key("restaurants", destination=destination)
        return await self.get(key)
    
    async def set_restaurants(self, destination: str, data: list) -> None:
        key = self._generate_key("restaurants", destination=destination)
        await self.set(key, data, self.TTL_RESTAURANTS)
    
    async def get_events(self, destination: str, start_date: str, end_date: str) -> Optional[list]:
        key = self._generate_key("events", destination=destination, start_date=start_date, end_date=end_date)
        return await self.get(key)
    
    async def set_events(self, destination: str, start_date: str, end_date: str, data: list) -> None:
        key = self._generate_key("events", destination=destination, start_date=start_date, end_date=end_date)
        await self.set(key, data, self.TTL_EVENTS)
    
    async def get_weather(self, destination: str, date: str) -> Optional[dict]:
        key = self._generate_key("weather", destination=destination, date=date)
        return await self.get(key)
    
    async def set_weather(self, destination: str, date: str, data: dict) -> None:
        key = self._generate_key("weather", destination=destination, date=date)
        await self.set(key, data, self.TTL_WEATHER)
    
    async def get_blogs(self, destination: str) -> Optional[list]:
        key = self._generate_key("blogs", destination=destination)
        return await self.get(key)
    
    async def set_blogs(self, destination: str, data: list) -> None:
        key = self._generate_key("blogs", destination=destination)
        await self.set(key, data, self.TTL_BLOGS)
    
    async def get_safety(self, destination: str) -> Optional[dict]:
        key = self._generate_key("safety", destination=destination)
        return await self.get(key)
    
    async def set_safety(self, destination: str, data: dict) -> None:
        key = self._generate_key("safety", destination=destination)
        await self.set(key, data, self.TTL_SAFETY)
    
    async def get_research(self, job_id: str) -> Optional[dict]:
        key = self._generate_key("research", job_id=job_id)
        return await self.get(key)
    
    async def set_research(self, job_id: str, data: dict) -> None:
        key = self._generate_key("research", job_id=job_id)
        await self.set(key, data, self.TTL_RESEARCH)
    
    async def get_stats(self) -> dict:
        """Get cache statistics."""
        if hasattr(self.backend, 'get_stats'):
            return self.backend.get_stats()
        return {'backend': 'redis', 'status': 'connected'}
    
    async def cleanup(self):
        """Cleanup expired entries (for in-memory cache)."""
        if hasattr(self.backend, 'cleanup_expired'):
            await self.backend.cleanup_expired()


# Global cache instance
_cache: Optional[TravelCache] = None


def get_cache() -> TravelCache:
    """Get or create cache instance."""
    global _cache
    if not _cache:
        _cache = TravelCache()
    return _cache


# Cache decorator for async functions
def cached(ttl: Optional[int] = None, key_prefix: str = "auto"):
    """
    Decorator to cache async function results.
    
    Usage:
        @cached(ttl=3600, key_prefix="flights")
        async def search_flights(origin, destination):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key from function name and arguments
            key = cache._generate_key(
                f"{key_prefix}_{func.__name__}",
                args=args,
                kwargs=kwargs
            )
            
            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for {key}")
                return cached_result
            
            # Execute function
            logger.debug(f"Cache MISS for {key}, executing function")
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Backward compatibility with earlier cache API names used by existing services.
def cache_result(ttl: Optional[int] = None, key_prefix: str = "auto"):
    """Alias for cached() to keep legacy imports working."""
    return cached(ttl=ttl, key_prefix=key_prefix)


class Cache(TravelCache):
    """Legacy class name kept for import compatibility."""
    pass


# Initialize cache on module load
async def init_cache():
    """Initialize cache backend."""
    cache = get_cache()
    if hasattr(cache.backend, 'connect'):
        await cache.backend.connect()
    return cache


# Cleanup cache on shutdown
async def close_cache():
    """Close cache connections."""
    global _cache
    if _cache and hasattr(_cache.backend, 'close'):
        await _cache.backend.close()
    _cache = None
