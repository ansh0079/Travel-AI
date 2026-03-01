import httpx
from typing import List, Optional, Dict
from datetime import timedelta
from app.config import get_settings
from app.models.destination import Attraction
import random
from app.utils.cache_service import cache_service, CacheService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class AttractionsService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.cache = cache_service

    async def get_natural_attractions(
        self,
        lat: float,
        lon: float,
        radius: int = 50000,  # 50km radius
        limit: int = 10
    ) -> List[Attraction]:
        """Get natural attractions (parks, beaches, mountains, etc.) with caching"""
        cache_key = CacheService.attractions_key(lat, lon, limit) + ":natural"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug("Natural attractions cache hit", lat=lat, lon=lon)
            return [Attraction(**a) for a in cached]
        
        logger.debug("Natural attractions cache miss", lat=lat, lon=lon)
        
        try:
            if self.settings.google_places_api_key:
                attractions = await self._fetch_google_places_natural(lat, lon, radius, limit)
                # Cache for 6 hours
                await self.cache.set(cache_key, [a.model_dump() for a in attractions], expire=timedelta(hours=6))
                return attractions

            return self._get_mock_natural_attractions(lat, lon, limit)
        except Exception as e:
            logger.warning("Attractions API error", error=str(e), lat=lat, lon=lon)
            return self._get_mock_natural_attractions(lat, lon, limit)

    async def get_all_attractions(
        self,
        lat: float,
        lon: float,
        radius: int = 10000,
        limit: int = 15
    ) -> List[Attraction]:
        """Get all types of attractions with caching"""
        cache_key = CacheService.attractions_key(lat, lon, limit) + ":all"
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug("All attractions cache hit", lat=lat, lon=lon)
            return [Attraction(**a) for a in cached]
        
        logger.debug("All attractions cache miss", lat=lat, lon=lon)
        
        try:
            if self.settings.google_places_api_key:
                attractions = await self._fetch_google_places_all(lat, lon, radius, limit)
                # Cache for 6 hours
                await self.cache.set(cache_key, [a.model_dump() for a in attractions], expire=timedelta(hours=6))
                return attractions

            return self._get_mock_all_attractions(lat, lon, limit)
        except Exception as e:
            logger.warning("Attractions API error", error=str(e), lat=lat, lon=lon)
            return self._get_mock_all_attractions(lat, lon, limit)
    
    async def _fetch_google_places_natural(
        self,
        lat: float,
        lon: float,
        radius: int,
        limit: int
    ) -> List[Attraction]:
        """Fetch natural attractions from Google Places"""
        natural_types = [
            "park", "natural_feature", "campground", "beach",
            "hiking_area", "national_park", "waterfall", "mountain"
        ]
        
        all_attractions = []
        
        async with httpx.AsyncClient() as client:
            for place_type in natural_types[:3]:  # Limit API calls
                try:
                    response = await client.get(
                        f"{self.base_url}/nearbysearch/json",
                        params={
                            "location": f"{lat},{lon}",
                            "radius": radius,
                            "type": place_type,
                            "key": self.settings.google_places_api_key
                        },
                        timeout=10.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for place in data.get("results", [])[:5]:
                        attraction = Attraction(
                            id=place["place_id"],
                            name=place["name"],
                            type=place_type,
                            rating=place.get("rating", 0),
                            description=place.get("vicinity", ""),
                            location={
                                "lat": place["geometry"]["location"]["lat"],
                                "lng": place["geometry"]["location"]["lng"]
                            },
                            natural_feature=True,
                            image_url=self._get_photo_url(place.get("photos", [{}])[0]) if place.get("photos") else None
                        )
                        all_attractions.append(attraction)
                except Exception as e:
                    logger.warning("Error fetching place type", place_type=place_type, error=str(e))
                    continue
        
        # Remove duplicates and sort by rating
        seen = set()
        unique = []
        for a in all_attractions:
            if a.name not in seen:
                seen.add(a.name)
                unique.append(a)
        
        return sorted(unique, key=lambda x: x.rating, reverse=True)[:limit]
    
    async def _fetch_google_places_all(
        self,
        lat: float,
        lon: float,
        radius: int,
        limit: int
    ) -> List[Attraction]:
        """Fetch all attraction types"""
        # Include both natural and cultural attractions
        all_types = [
            "tourist_attraction", "point_of_interest", "museum",
            "park", "natural_feature", "beach", "landmark"
        ]
        
        all_attractions = []
        
        async with httpx.AsyncClient() as client:
            for place_type in all_types[:4]:
                try:
                    response = await client.get(
                        f"{self.base_url}/nearbysearch/json",
                        params={
                            "location": f"{lat},{lon}",
                            "radius": radius,
                            "type": place_type,
                            "key": self.settings.google_places_api_key
                        },
                        timeout=10.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for place in data.get("results", [])[:5]:
                        attraction = Attraction(
                            id=place["place_id"],
                            name=place["name"],
                            type=place_type,
                            rating=place.get("rating", 0),
                            description=place.get("vicinity", ""),
                            location={
                                "lat": place["geometry"]["location"]["lat"],
                                "lng": place["geometry"]["location"]["lng"]
                            },
                            natural_feature=place_type in ["park", "natural_feature", "beach"],
                            image_url=self._get_photo_url(place.get("photos", [{}])[0]) if place.get("photos") else None
                        )
                        all_attractions.append(attraction)
                except Exception as e:
                    continue
        
        # Remove duplicates
        seen = set()
        unique = []
        for a in all_attractions:
            if a.name not in seen:
                seen.add(a.name)
                unique.append(a)
        
        return sorted(unique, key=lambda x: x.rating, reverse=True)[:limit]
    
    def _get_photo_url(self, photo_data: dict) -> Optional[str]:
        """Generate photo URL from Google Places photo reference"""
        if not photo_data or not isinstance(photo_data, dict):
            return None
        photo_ref = photo_data.get("photo_reference")
        if photo_ref and self.settings.google_places_api_key:
            return f"{self.base_url}/photo?maxwidth=400&photoreference={photo_ref}&key={self.settings.google_places_api_key}"
        return None
    
    def _get_mock_natural_attractions(self, lat: float, lon: float, limit: int) -> List[Attraction]:
        """Generate mock natural attractions"""
        mock_attractions = [
            {
                "name": "Crystal Lake National Park",
                "type": "national_park",
                "rating": 4.8,
                "description": "Breathtaking mountain scenery with crystal-clear lakes",
                "natural_feature": True
            },
            {
                "name": "Sunset Beach",
                "type": "beach",
                "rating": 4.5,
                "description": "Pristine sandy beach with stunning sunsets",
                "natural_feature": True
            },
            {
                "name": "Eagle Peak Trail",
                "type": "hiking_area",
                "rating": 4.7,
                "description": "Challenging hike with panoramic views",
                "natural_feature": True
            },
            {
                "name": "Azure Waterfall",
                "type": "waterfall",
                "rating": 4.6,
                "description": "Majestic waterfall surrounded by rainforest",
                "natural_feature": True
            },
            {
                "name": "Botanical Gardens",
                "type": "park",
                "rating": 4.4,
                "description": "Beautiful gardens with native and exotic plants",
                "natural_feature": True
            },
            {
                "name": "Whale Watching Point",
                "type": "natural_feature",
                "rating": 4.9,
                "description": "Best spot for whale watching during migration season",
                "natural_feature": True
            }
        ]
        
        attractions = []
        for i, data in enumerate(mock_attractions[:limit]):
            attractions.append(Attraction(
                id=f"nat_attr_{i}_{lat}_{lon}",
                name=data["name"],
                type=data["type"],
                rating=data["rating"],
                description=data["description"],
                location={"lat": lat + random.uniform(-0.1, 0.1), "lng": lon + random.uniform(-0.1, 0.1)},
                natural_feature=data["natural_feature"],
                entry_fee=random.choice([None, 10, 15, 20, 25])
            ))
        
        return attractions
    
    def _get_mock_all_attractions(self, lat: float, lon: float, limit: int) -> List[Attraction]:
        """Generate mock mix of natural and cultural attractions"""
        mock_attractions = [
            {"name": "Central Museum", "type": "museum", "rating": 4.6, "natural_feature": False, "desc": "World-class art and history collections"},
            {"name": "Historic Old Town", "type": "landmark", "rating": 4.5, "natural_feature": False, "desc": "Charming historic district with cobblestone streets"},
            {"name": "Royal Palace", "type": "tourist_attraction", "rating": 4.7, "natural_feature": False, "desc": "Magnificent palace with guided tours"},
            {"name": "City Cathedral", "type": "landmark", "rating": 4.4, "natural_feature": False, "desc": "Stunning Gothic architecture"},
            {"name": "Crystal Lake National Park", "type": "national_park", "rating": 4.8, "natural_feature": True, "desc": "Breathtaking mountain scenery"},
            {"name": "Sunset Beach", "type": "beach", "rating": 4.5, "natural_feature": True, "desc": "Pristine sandy beach with stunning sunsets"},
            {"name": "Modern Art Gallery", "type": "museum", "rating": 4.3, "natural_feature": False, "desc": "Contemporary art exhibitions"},
            {"name": "Ancient Temple", "type": "tourist_attraction", "rating": 4.8, "natural_feature": False, "desc": "Sacred temple with centuries of history"},
        ]
        
        attractions = []
        for i, data in enumerate(mock_attractions[:limit]):
            attractions.append(Attraction(
                id=f"attr_{i}_{lat}_{lon}",
                name=data["name"],
                type=data["type"],
                rating=data["rating"],
                description=data["desc"],
                location={"lat": lat + random.uniform(-0.05, 0.05), "lng": lon + random.uniform(-0.05, 0.05)},
                natural_feature=data["natural_feature"],
                entry_fee=random.choice([0, 10, 15, 20, 25]) if not data["natural_feature"] else None
            ))
        
        return attractions
    
    def calculate_attractions_score(
        self,
        attractions: List[Attraction],
        interests: List[str]
    ) -> float:
        """
        Calculate attractions match score (0-100)
        Based on quantity, quality (ratings), and interest alignment
        """
        if not attractions:
            return 20.0  # Base score for no data
        
        # Quantity score (more attractions = better, up to 20)
        quantity_score = min(len(attractions) * 4, 20)
        
        # Quality score based on ratings
        avg_rating = sum(a.rating for a in attractions) / len(attractions)
        quality_score = (avg_rating / 5.0) * 30
        
        # Interest alignment
        interest_score = 0
        if interests:
            natural_interests = ["nature", "beaches", "mountains", "wildlife", "adventure"]
            cultural_interests = ["culture", "history", "art"]
            
            natural_count = sum(1 for a in attractions if a.natural_feature)
            cultural_count = len(attractions) - natural_count
            
            has_natural_interest = any(i in natural_interests for i in interests)
            has_cultural_interest = any(i in cultural_interests for i in interests)
            
            if has_natural_interest:
                interest_score += (natural_count / len(attractions)) * 25
            if has_cultural_interest:
                interest_score += (cultural_count / len(attractions)) * 25
            
            # Cap at 50
            interest_score = min(interest_score, 50)
        else:
            interest_score = 40  # Neutral if no preferences specified
        
        return min(100, quantity_score + quality_score + interest_score)