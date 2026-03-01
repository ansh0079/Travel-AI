"""
Base service class for HTTP clients
Provides common functionality for all external API services
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import timedelta
from app.utils.logging_config import get_logger
from app.utils.cache_service import CacheService, get_cache

logger = get_logger(__name__)


class BaseService:
    """Base class for all external API services"""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._default_headers = headers or {}
        self._cache: Optional[CacheService] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            headers = self._default_headers.copy()
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers=headers,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _get_cache(self) -> Optional[CacheService]:
        """Get cache service instance"""
        if self._cache is None:
            self._cache = await get_cache()
        return self._cache if self._cache._enabled else None
    
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[timedelta] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with optional caching
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            json: JSON body for POST/PUT requests
            cache_key: Cache key (if caching desired)
            cache_ttl: Cache time-to-live
        
        Returns:
            Response JSON or None if error
        """
        # Try cache first
        if cache_key:
            cache = await self._get_cache()
            if cache:
                cached = await cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached
        
        # Make request
        client = await self._get_client()
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache response
            if cache_key and cache_ttl and data:
                cache = await self._get_cache()
                if cache:
                    await cache.set(cache_key, data, cache_ttl)
                    logger.debug(f"Cached response for {cache_key}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {endpoint}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error for {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {endpoint}: {e}")
            return None
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        cache_ttl: timedelta = timedelta(hours=1)
    ) -> Optional[Dict[str, Any]]:
        """Make GET request"""
        return await self.request(
            method="GET",
            endpoint=endpoint,
            params=params,
            cache_key=cache_key,
            cache_ttl=cache_ttl
        )
    
    async def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[timedelta] = None
    ) -> Optional[Dict[str, Any]]:
        """Make POST request"""
        return await self.request(
            method="POST",
            endpoint=endpoint,
            json=json,
            cache_key=cache_key,
            cache_ttl=cache_ttl
        )
    
    @staticmethod
    def handle_api_error(
        error: Exception,
        endpoint: str,
        fallback_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Handle API errors gracefully with optional fallback"""
        logger.warning(f"API error for {endpoint}: {error}")
        return fallback_data
