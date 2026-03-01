import httpx
from typing import Optional, Dict
from datetime import datetime, timedelta
from app.config import get_settings
from app.models.destination import Affordability
from app.utils.cache_service import cache_service, CacheService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class AffordabilityService:
    def __init__(self):
        self.settings = get_settings()
        self.cache = cache_service
        # Cost of living index database (approximate values)
        # 100 = New York City baseline
        self.cost_index_db = self._load_cost_index_database()
    
    def _load_cost_index_database(self) -> Dict[str, Dict]:
        """Load cost index data by country code"""
        return {
            "US": {"index": 100, "daily_budget": {"budget": 80, "moderate": 150, "comfort": 250, "luxury": 500}},
            "FR": {"index": 85, "daily_budget": {"budget": 70, "moderate": 140, "comfort": 220, "luxury": 450}},
            "JP": {"index": 90, "daily_budget": {"budget": 75, "moderate": 150, "comfort": 250, "luxury": 500}},
            "ID": {"index": 35, "daily_budget": {"budget": 25, "moderate": 50, "comfort": 100, "luxury": 250}},
            "GB": {"index": 90, "daily_budget": {"budget": 80, "moderate": 160, "comfort": 280, "luxury": 550}},
            "AE": {"index": 80, "daily_budget": {"budget": 60, "moderate": 120, "comfort": 220, "luxury": 500}},
            "SG": {"index": 95, "daily_budget": {"budget": 70, "moderate": 140, "comfort": 250, "luxury": 550}},
            "AU": {"index": 85, "daily_budget": {"budget": 75, "moderate": 150, "comfort": 250, "luxury": 500}},
            "IT": {"index": 75, "daily_budget": {"budget": 60, "moderate": 120, "comfort": 200, "luxury": 400}},
            "ES": {"index": 70, "daily_budget": {"budget": 55, "moderate": 110, "comfort": 180, "luxury": 380}},
            "ZA": {"index": 45, "daily_budget": {"budget": 35, "moderate": 70, "comfort": 120, "luxury": 280}},
            "MA": {"index": 35, "daily_budget": {"budget": 25, "moderate": 50, "comfort": 100, "luxury": 250}},
            "TH": {"index": 40, "daily_budget": {"budget": 30, "moderate": 60, "comfort": 120, "luxury": 280}},
            "TR": {"index": 35, "daily_budget": {"budget": 25, "moderate": 55, "comfort": 110, "luxury": 250}},
            "IS": {"index": 110, "daily_budget": {"budget": 100, "moderate": 200, "comfort": 350, "luxury": 700}},
            "BR": {"index": 40, "daily_budget": {"budget": 35, "moderate": 70, "comfort": 130, "luxury": 300}},
            "EG": {"index": 25, "daily_budget": {"budget": 20, "moderate": 40, "comfort": 80, "luxury": 200}},
            "CZ": {"index": 55, "daily_budget": {"budget": 40, "moderate": 80, "comfort": 150, "luxury": 320}},
            "NZ": {"index": 85, "daily_budget": {"budget": 75, "moderate": 150, "comfort": 260, "luxury": 520}},
            "IN": {"index": 25, "daily_budget": {"budget": 20, "moderate": 45, "comfort": 90, "luxury": 220}},
            "VN": {"index": 30, "daily_budget": {"budget": 20, "moderate": 45, "comfort": 90, "luxury": 200}},
            "PH": {"index": 35, "daily_budget": {"budget": 25, "moderate": 50, "comfort": 100, "luxury": 250}},
            "MX": {"index": 45, "daily_budget": {"budget": 35, "moderate": 70, "comfort": 130, "luxury": 300}},
            "GR": {"index": 65, "daily_budget": {"budget": 50, "moderate": 100, "comfort": 170, "luxury": 350}},
            "PT": {"index": 65, "daily_budget": {"budget": 50, "moderate": 100, "comfort": 170, "luxury": 350}},
            "NL": {"index": 88, "daily_budget": {"budget": 75, "moderate": 150, "comfort": 260, "luxury": 520}},
            "DE": {"index": 82, "daily_budget": {"budget": 70, "moderate": 140, "comfort": 230, "luxury": 480}},
            "CH": {"index": 130, "daily_budget": {"budget": 120, "moderate": 240, "comfort": 400, "luxury": 800}},
            "SE": {"index": 95, "daily_budget": {"budget": 85, "moderate": 170, "comfort": 280, "luxury": 550}},
            "NO": {"index": 110, "daily_budget": {"budget": 100, "moderate": 200, "comfort": 350, "luxury": 700}},
            "DK": {"index": 100, "daily_budget": {"budget": 90, "moderate": 180, "comfort": 300, "luxury": 600}},
            "FI": {"index": 90, "daily_budget": {"budget": 80, "moderate": 160, "comfort": 270, "luxury": 540}},
            "KR": {"index": 80, "daily_budget": {"budget": 60, "moderate": 120, "comfort": 200, "luxury": 450}},
        }
    
    async def get_affordability(
        self,
        country_code: str,
        travel_style: str = "moderate"
    ) -> Affordability:
        """Get affordability data for a country with caching"""
        cache_key = CacheService.affordability_key(country_code, travel_style)
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug("Affordability cache hit", country=country_code, style=travel_style)
            return Affordability(**cached)
        
        logger.debug("Affordability cache miss", country=country_code, style=travel_style)
        
        country_data = self.cost_index_db.get(country_code.upper(), {
            "index": 50,
            "daily_budget": {"budget": 40, "moderate": 80, "comfort": 150, "luxury": 300}
        })
        
        # Get daily budget for travel style
        daily_cost = country_data["daily_budget"].get(travel_style, 150)
        
        # Determine cost level
        cost_index = country_data["index"]
        if cost_index < 40:
            cost_level = "budget"
        elif cost_index < 70:
            cost_level = "moderate"
        elif cost_index < 100:
            cost_level = "expensive"
        else:
            cost_level = "luxury"
        
        affordability = Affordability(
            cost_level=cost_level,
            daily_cost_estimate=daily_cost,
            currency="USD",
            accommodation_avg=daily_cost * 0.4,
            food_avg=daily_cost * 0.25,
            transport_avg=daily_cost * 0.15,
            activities_avg=daily_cost * 0.2,
            cost_index=cost_index
        )
        
        # Cache for 24 hours (affordability data changes rarely)
        await self.cache.set(cache_key, affordability.model_dump(), expire=timedelta(hours=24))
        
        return affordability
    
    def calculate_affordability_score(
        self,
        affordability: Affordability,
        user_budget_daily: float,
        user_travel_style: str
    ) -> float:
        """
        Calculate how well destination matches user's budget (0-100)
        Higher score = better match
        """
        # Calculate budget fit
        budget_ratio = user_budget_daily / affordability.daily_cost_estimate
        
        if budget_ratio >= 1.5:
            # User budget is much higher than needed - great fit
            base_score = 100
        elif budget_ratio >= 1.0:
            # User budget comfortably covers costs
            base_score = 90 + (budget_ratio - 1.0) * 20
        elif budget_ratio >= 0.8:
            # Slightly tight but manageable
            base_score = 70 + (budget_ratio - 0.8) * 100
        elif budget_ratio >= 0.6:
            # Tight budget
            base_score = 50 + (budget_ratio - 0.6) * 100
        else:
            # Way over budget
            base_score = max(0, budget_ratio * 83)
        
        # Travel style alignment
        style_scores = {
            "budget": {"budget": 15, "moderate": 5, "expensive": -10, "luxury": -20},
            "moderate": {"budget": 5, "moderate": 15, "expensive": 5, "luxury": -10},
            "comfort": {"budget": -5, "moderate": 5, "expensive": 15, "luxury": 5},
            "luxury": {"budget": -20, "moderate": -10, "expensive": 5, "luxury": 15}
        }
        
        style_adjustment = style_scores.get(user_travel_style, {}).get(affordability.cost_level, 0)
        
        return max(0, min(100, base_score + style_adjustment))


# Add cache key helper to CacheService
setattr(CacheService, 'affordability_key', staticmethod(
    lambda country_code, travel_style: f"affordability:{country_code}:{travel_style}"
))
