import functools
import hashlib
import json
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
import asyncio

# Simple in-memory cache
_cache_store: dict = {}
_cache_expiry: dict = {}

class Cache:
    def __init__(self):
        self.store = {}
        self.expiry = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self.expiry:
            if datetime.now() > self.expiry[key]:
                # Expired
                del self.store[key]
                del self.expiry[key]
                return None
            return self.store.get(key)
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set value in cache with TTL"""
        self.store[key] = value
        self.expiry[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def delete(self, key: str):
        """Delete key from cache"""
        self.store.pop(key, None)
        self.expiry.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        self.store.clear()
        self.expiry.clear()

# Global cache instance
cache = Cache()

def cache_result(ttl: int = 3600, key_func: Optional[Callable] = None):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_func: Optional function to generate cache key from arguments
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: hash of function name and arguments
                key_data = {
                    "func": func.__name__,
                    "args": [str(a) for a in args],
                    "kwargs": {k: str(v) for k, v in kwargs.items()}
                }
                cache_key = hashlib.md5(
                    json.dumps(key_data, sort_keys=True).encode()
                ).hexdigest()
            
            # Check cache
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute and cache
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_data = {
                    "func": func.__name__,
                    "args": [str(a) for a in args],
                    "kwargs": {k: str(v) for k, v in kwargs.items()}
                }
                cache_key = hashlib.md5(
                    json.dumps(key_data, sort_keys=True).encode()
                ).hexdigest()
            
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        # Return appropriate wrapper based on whether function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

def clear_cache_pattern(pattern: str):
    """Clear all cache keys matching a pattern"""
    keys_to_delete = [
        key for key in list(cache.store.keys())
        if pattern in key
    ]
    for key in keys_to_delete:
        cache.delete(key)