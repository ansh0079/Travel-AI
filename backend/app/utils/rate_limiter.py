"""
Rate limiting utilities for API calls
Token bucket algorithm with multi-key rotation
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class RateLimiter:
    """Token bucket rate limiter for API calls"""
    
    def __init__(self, rate: int = 10, per: int = 1):
        self.rate = rate  # Number of requests
        self.per = per    # Per X seconds
        self.tokens = float(rate)
        self.last_refill = datetime.now()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Acquire a token, returns True if successful"""
        async with self.lock:
            now = datetime.now()
            
            # Refill tokens
            time_passed = (now - self.last_refill).total_seconds()
            self.tokens = min(
                self.rate,
                self.tokens + time_passed * (self.rate / self.per)
            )
            self.last_refill = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            # Calculate wait time
            wait_time = (1 - self.tokens) * (self.per / self.rate)
            await asyncio.sleep(wait_time)
            self.tokens = max(0, self.tokens - 1)
            return True
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class APIKeyManager:
    """Manage multiple API keys with rate limiting"""
    
    def __init__(self, keys: List[str], rate_per_key: int = 60):
        self.keys = keys
        self.current_key = 0
        self.limiters: Dict[str, RateLimiter] = {
            key: RateLimiter(rate=rate_per_key, per=60)
            for key in keys
        }
        self.lock = asyncio.Lock()
    
    async def get_key(self) -> str:
        """Get next available API key with rate limiting"""
        async with self.lock:
            start_idx = self.current_key
            attempts = 0
            max_attempts = len(self.keys) * 2
            
            while attempts < max_attempts:
                key = self.keys[self.current_key]
                limiter = self.limiters[key]
                
                # Try to acquire token
                if limiter.tokens >= 1 or await limiter.acquire():
                    # Move to next key for round-robin
                    self.current_key = (self.current_key + 1) % len(self.keys)
                    return key
                
                # Move to next key
                self.current_key = (self.current_key + 1) % len(self.keys)
                attempts += 1
                
                # If we've tried all keys, wait a bit
                if self.current_key == start_idx:
                    await asyncio.sleep(0.5)
            
            # Fallback: return first key anyway
            return self.keys[0]


class ServiceRateLimiter:
    """Rate limiter for external services"""
    
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
    
    def get_limiter(self, service_name: str, rate: int = 10, per: int = 1) -> RateLimiter:
        """Get or create rate limiter for a service"""
        key = f"{service_name}:{rate}:{per}"
        if key not in self._limiters:
            self._limiters[key] = RateLimiter(rate=rate, per=per)
        return self._limiters[key]
    
    async def call_with_limit(
        self, 
        service_name: str, 
        func, 
        *args, 
        rate: int = 10, 
        per: int = 1,
        **kwargs
    ):
        """Call a function with rate limiting"""
        limiter = self.get_limiter(service_name, rate, per)
        async with limiter:
            return await func(*args, **kwargs)


# Global rate limiter instance
service_rate_limiter = ServiceRateLimiter()
