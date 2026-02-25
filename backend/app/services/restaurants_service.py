"""
Restaurants & Dining Service
Provides dining recommendations, restaurant data, and food scene information
"""

from typing import List, Dict, Any, Optional
from app.config import get_settings


class RestaurantsService:
    """Service for finding restaurants and dining options"""
    
    def __init__(self):
        self.settings = get_settings()
    
    def get_restaurants(
        self,
        destination: str,
        cuisine_types: Optional[List[str]] = None,
        budget_level: str = "moderate",
        dining_style: str = "any"  # casual, fine_dining, street_food, any
    ) -> List[Dict[str, Any]]:
        """
        Get restaurant recommendations for a destination
        
        Args:
            destination: City or country name
            cuisine_types: List of preferred cuisines (e.g., ['italian', 'asian'])
            budget_level: low, moderate, high, luxury
            dining_style: casual, fine_dining, street_food, any
        """
        # Mock restaurant database - in production, integrate with Google Places, Yelp, etc.
        restaurants_db = self._get_mock_restaurants(destination)
        
        # Filter by budget
        price_ranges = {
            "low": ["$", "$$"],
            "moderate": ["$$", "$$$"],
            "high": ["$$$", "$$$$"],
            "luxury": ["$$$$"]
        }
        allowed_prices = price_ranges.get(budget_level, ["$$", "$$$"])
        
        filtered = [r for r in restaurants_db if r.get("price_level") in allowed_prices]
        
        # Filter by cuisine if specified
        if cuisine_types:
            filtered = [
                r for r in filtered 
                if any(c.lower() in r.get("cuisine", []).lower() for c in cuisine_types)
            ]
        
        # Filter by dining style
        if dining_style != "any":
            filtered = [r for r in filtered if r.get("style") == dining_style]
        
        # Sort by rating
        filtered.sort(key=lambda x: x.get("rating", 0), reverse=True)
        
        return filtered[:10]
    
    def get_food_scene(self, destination: str) -> Dict[str, Any]:
        """Get overview of the food scene in a destination"""
        food_scenes = {
            "tokyo": {
                "signature_dishes": ["Sushi", "Ramen", "Tempura", "Wagyu Beef"],
                "dining_culture": "Incredible variety from street food to Michelin stars",
                "must_try": "Tsukiji Outer Market, themed cafes, izakayas",
                "price_range": "$$-$$$$",
                "vegetarian_friendly": "Moderate - fish stock common"
            },
            "paris": {
                "signature_dishes": ["Croissants", "Coq au Vin", "Macarons", "French Onion Soup"],
                "dining_culture": "Café culture, long lunches, wine with every meal",
                "must_try": "Local bistros, patisseries, wine bars",
                "price_range": "$$$-$$$$",
                "vegetarian_friendly": "Good - many options available"
            },
            "bangkok": {
                "signature_dishes": ["Pad Thai", "Tom Yum", "Green Curry", "Mango Sticky Rice"],
                "dining_culture": "Street food paradise, night markets, floating markets",
                "must_try": "Street food stalls, rooftop bars, night markets",
                "price_range": "$-$$",
                "vegetarian_friendly": "Excellent - many Buddhist vegetarian options"
            },
            "rome": {
                "signature_dishes": ["Pasta Carbonara", "Pizza", "Gelato", "Supplì"],
                "dining_culture": "Long dinners, aperitivo hour, family-style dining",
                "must_try": "Trattorias, aperitivo bars, gelaterias",
                "price_range": "$$-$$$",
                "vegetarian_friendly": "Excellent - many pasta/pizza options"
            },
            "mexico city": {
                "signature_dishes": ["Tacos", "Tamales", "Chiles en Nogada", "Mezcal"],
                "dining_culture": "Street food culture, cantinas, mercados",
                "must_try": "Taco stands, mercados, pulquerías",
                "price_range": "$-$$",
                "vegetarian_friendly": "Good - many bean/cheese options"
            },
            "barcelona": {
                "signature_dishes": ["Paella", "Tapas", "Churros", "Sangria"],
                "dining_culture": "Late dining, tapas hopping, beachside restaurants",
                "must_try": "La Boqueria market, tapas bars, beach chiringuitos",
                "price_range": "$$-$$$",
                "vegetarian_friendly": "Good - many tapas are vegetarian"
            },
            "istanbul": {
                "signature_dishes": ["Kebabs", "Baklava", "Turkish Breakfast", "Meze"],
                "dining_culture": "Tea culture, meyhane tradition, street simit",
                "must_try": "Grand Bazaar food, Bosphorus restaurants, kahvaltı",
                "price_range": "$-$$",
                "vegetarian_friendly": "Excellent - many meze options"
            },
            "mumbai": {
                "signature_dishes": ["Vada Pav", "Pani Puri", "Butter Chicken", "Biryani"],
                "dining_culture": "Street food capital, Irani cafes, thali meals",
                "must_try": "Chowpatty Beach, Mohammed Ali Road, Parsi cafes",
                "price_range": "$-$$",
                "vegetarian_friendly": "Excellent - 40%+ population vegetarian"
            }
        }
        
        # Find matching destination
        dest_lower = destination.lower()
        for key, scene in food_scenes.items():
            if key in dest_lower:
                return {
                    "destination": destination,
                    "food_scene": scene,
                    "source": "local_knowledge"
                }
        
        # Default response
        return {
            "destination": destination,
            "food_scene": {
                "signature_dishes": ["Local specialties"],
                "dining_culture": "Explore local restaurants and street food",
                "must_try": "Ask locals for recommendations",
                "price_range": "$$",
                "vegetarian_friendly": "Check with individual restaurants"
            },
            "source": "general"
        }
    
    def get_dietary_options(
        self,
        destination: str,
        dietary_restrictions: List[str]
    ) -> Dict[str, Any]:
        """
        Get information about dietary options in a destination
        
        Args:
            destination: City or country
            dietary_restrictions: List like ['vegetarian', 'vegan', 'gluten_free', 'halal', 'kosher']
        """
        result = {
            "destination": destination,
            "dietary_restrictions": dietary_restrictions,
            "recommendations": {}
        }
        
        dest_lower = destination.lower()
        
        for restriction in dietary_restrictions:
            if restriction == "vegetarian":
                if any(x in dest_lower for x in ["india", "mumbai", "delhi", "bangkok", "chiang mai"]):
                    result["recommendations"][restriction] = "Excellent options - many traditional dishes are vegetarian"
                elif any(x in dest_lower for x in ["italy", "rome", "paris", "spain", "barcelona"]):
                    result["recommendations"][restriction] = "Good options - pasta, pizza, salads widely available"
                else:
                    result["recommendations"][restriction] = "Moderate options - research vegetarian-friendly restaurants"
            
            elif restriction == "vegan":
                if any(x in dest_lower for x in ["berlin", "london", "los angeles", "portland", "tel aviv"]):
                    result["recommendations"][restriction] = "Excellent vegan scene with dedicated restaurants"
                else:
                    result["recommendations"][restriction] = "Growing options - check HappyCow app for listings"
            
            elif restriction == "gluten_free":
                if any(x in dest_lower for x in ["italy", "rome"]):
                    result["recommendations"][restriction] = "Good awareness - many restaurants offer gluten-free pasta"
                else:
                    result["recommendations"][restriction] = "Learn key phrases in local language - bring GF cards"
            
            elif restriction == "halal":
                if any(x in dest_lower for x in ["istanbul", "dubai", "cairo", "kuala lumpur", "indonesia"]):
                    result["recommendations"][restriction] = "Widely available - majority of food is halal"
                else:
                    result["recommendations"][restriction] = "Check for halal certification - Middle Eastern restaurants often suitable"
            
            elif restriction == "kosher":
                if any(x in dest_lower for x in ["jerusalem", "tel aviv", "new york"]):
                    result["recommendations"][restriction] = "Strong kosher infrastructure available"
                else:
                    result["recommendations"][restriction] = "Limited options - bring packaged food, research Chabad houses"
        
        return result
    
    def _get_mock_restaurants(self, destination: str) -> List[Dict[str, Any]]:
        """Generate mock restaurant data based on destination"""
        import random
        
        # Base templates for different cuisines
        templates = {
            "italian": [
                {"name": "Trattoria Romana", "cuisine": "Italian", "style": "casual", "rating": 4.5},
                {"name": "Osteria del Centro", "cuisine": "Italian", "style": "fine_dining", "rating": 4.7},
                {"name": "Pizzeria Napoli", "cuisine": "Italian", "style": "casual", "rating": 4.3},
            ],
            "asian": [
                {"name": "Golden Dragon", "cuisine": "Chinese", "style": "casual", "rating": 4.4},
                {"name": "Sakura Sushi", "cuisine": "Japanese", "style": "fine_dining", "rating": 4.8},
                {"name": "Thai Spice", "cuisine": "Thai", "style": "casual", "rating": 4.5},
            ],
            "local": [
                {"name": "The Local Table", "cuisine": "Local", "style": "casual", "rating": 4.6},
                {"name": "Market Kitchen", "cuisine": "Local", "style": "fine_dining", "rating": 4.5},
                {"name": "Street Food Corner", "cuisine": "Street Food", "style": "street_food", "rating": 4.3},
            ],
            "international": [
                {"name": "Global Bites", "cuisine": "International", "style": "casual", "rating": 4.2},
                {"name": "Fusion Garden", "cuisine": "Fusion", "style": "fine_dining", "rating": 4.6},
                {"name": "Café Central", "cuisine": "Café", "style": "casual", "rating": 4.4},
            ]
        }
        
        # Generate varied mock data
        restaurants = []
        all_cuisines = list(templates.values())
        
        for i in range(12):
            cuisine_group = random.choice(all_cuisines)
            base = random.choice(cuisine_group).copy()
            base["id"] = f"rest_{i}"
            base["price_level"] = random.choice(["$", "$$", "$$$", "$$$$"])
            base["rating"] = round(random.uniform(3.8, 4.9), 1)
            base["review_count"] = random.randint(100, 5000)
            base["address"] = f"{random.randint(1, 999)} {random.choice(['Main St', 'Broadway', 'High St', 'Market St'])}"
            base["opening_hours"] = "11:00 AM - 10:00 PM"
            base["phone"] = f"+1-555-{random.randint(1000, 9999)}"
            
            # Add dietary options
            base["dietary_options"] = random.sample(
                ["vegetarian", "vegan", "gluten_free", "halal"], 
                k=random.randint(0, 3)
            )
            
            restaurants.append(base)
        
        return restaurants


# Convenience function
def get_dining_recommendations(
    destination: str,
    cuisine_types: Optional[List[str]] = None,
    budget_level: str = "moderate"
) -> Dict[str, Any]:
    """Quick access to dining recommendations"""
    service = RestaurantsService()
    
    return {
        "destination": destination,
        "restaurants": service.get_restaurants(destination, cuisine_types, budget_level),
        "food_scene": service.get_food_scene(destination),
        "budget_level": budget_level
    }
