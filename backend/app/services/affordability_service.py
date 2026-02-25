import httpx
from typing import Optional, Dict
from datetime import datetime
from app.config import get_settings
from app.models.destination import Affordability

class AffordabilityService:
    def __init__(self):
        self.settings = get_settings()
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
            "CN": {"index": 45, "daily_budget": {"budget": 35, "moderate": 70, "comfort": 130, "luxury": 300}},
            "MY": {"index": 45, "daily_budget": {"budget": 35, "moderate": 70, "comfort": 130, "luxury": 300}},
            "KH": {"index": 30, "daily_budget": {"budget": 20, "moderate": 45, "comfort": 90, "luxury": 200}},
            "PE": {"index": 35, "daily_budget": {"budget": 25, "moderate": 55, "comfort": 110, "luxury": 260}},
            "CL": {"index": 55, "daily_budget": {"budget": 45, "moderate": 90, "comfort": 160, "luxury": 350}},
            "AR": {"index": 40, "daily_budget": {"budget": 30, "moderate": 65, "comfort": 120, "luxury": 280}},
            "CO": {"index": 35, "daily_budget": {"budget": 25, "moderate": 55, "comfort": 110, "luxury": 260}},
        }
    
    async def get_affordability(
        self,
        country_code: str,
        travel_style: str = "moderate"
    ) -> Affordability:
        """Get affordability data for a destination"""
        country_data = self.cost_index_db.get(country_code, self.cost_index_db["US"])
        
        daily_budget = country_data["daily_budget"].get(travel_style, 150)
        cost_index = country_data["index"]
        
        # Calculate breakdown
        accommodation_pct = 0.40
        food_pct = 0.25
        transport_pct = 0.15
        activities_pct = 0.20
        
        # Adjust percentages based on travel style
        if travel_style == "budget":
            accommodation_pct = 0.30
            food_pct = 0.30
            transport_pct = 0.20
            activities_pct = 0.20
        elif travel_style == "luxury":
            accommodation_pct = 0.50
            food_pct = 0.20
            transport_pct = 0.10
            activities_pct = 0.20
        
        # Determine cost level
        if cost_index < 40:
            cost_level = "budget"
        elif cost_index < 60:
            cost_level = "moderate"
        elif cost_index < 85:
            cost_level = "comfort"
        else:
            cost_level = "luxury"
        
        return Affordability(
            cost_level=cost_level,
            daily_cost_estimate=daily_budget,
            accommodation_avg=daily_budget * accommodation_pct,
            food_avg=daily_budget * food_pct,
            transport_avg=daily_budget * transport_pct,
            activities_avg=daily_budget * activities_pct,
            cost_index=cost_index
        )
    
    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Optional[float]:
        """Get current exchange rate"""
        try:
            if self.settings.exchangerate_api_key:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://v6.exchangerate-api.com/v6/{self.settings.exchangerate_api_key}/pair/{from_currency}/{to_currency}",
                        timeout=10.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data.get("conversion_rate")
            
            # Fallback rates (approximate)
            fallback_rates = {
                ("USD", "EUR"): 0.85,
                ("USD", "GBP"): 0.73,
                ("USD", "JPY"): 110,
                ("USD", "AUD"): 1.35,
                ("USD", "CAD"): 1.25,
                ("USD", "CHF"): 0.92,
                ("USD", "CNY"): 6.45,
                ("USD", "INR"): 74,
                ("USD", "IDR"): 14300,
                ("USD", "THB"): 33,
            }
            return fallback_rates.get((from_currency, to_currency))
        except Exception as e:
            print(f"Exchange rate API error: {e}")
            return None
    
    def calculate_affordability_score(
        self,
        affordability: Affordability,
        user_budget_daily: float,
        travel_style: str
    ) -> float:
        """
        Calculate affordability match score (0-100)
        Higher score = better fit for user's budget
        """
        daily_cost = affordability.daily_cost_estimate
        
        # Budget fit ratio
        if daily_cost <= user_budget_daily * 0.8:
            # Well within budget - great fit
            budget_score = 90 + min((user_budget_daily - daily_cost) / user_budget_daily * 10, 10)
        elif daily_cost <= user_budget_daily:
            # Within budget
            budget_score = 80
        elif daily_cost <= user_budget_daily * 1.2:
            # Slightly over budget
            budget_score = 60
        elif daily_cost <= user_budget_daily * 1.5:
            # Moderately over budget
            budget_score = 40
        else:
            # Significantly over budget
            budget_score = 20
        
        # Travel style alignment
        style_alignment = {
            "budget": {"budget": 20, "moderate": 5, "comfort": -10, "luxury": -20},
            "moderate": {"budget": 5, "moderate": 20, "comfort": 10, "luxury": -10},
            "comfort": {"budget": -10, "moderate": 10, "comfort": 20, "luxury": 5},
            "luxury": {"budget": -20, "moderate": -10, "comfort": 10, "luxury": 20}
        }
        
        style_score = style_alignment.get(travel_style, {}).get(affordability.cost_level, 0)
        
        total_score = budget_score + style_score
        return max(0, min(100, total_score))
    
    def get_affordability_summary(self, affordability: Affordability) -> str:
        """Get human-readable affordability summary"""
        level_emojis = {
            "budget": "💰",
            "moderate": "💰💰",
            "comfort": "💰💰💰",
            "luxury": "💰💰💰💰"
        }
        
        emoji = level_emojis.get(affordability.cost_level, "💰")
        return f"{emoji} ~${affordability.daily_cost_estimate:.0f}/day"