from typing import Dict, Optional, Tuple
from datetime import date
from app.models.destination import Destination
from app.models.user import UserPreferences, Interest

def calculate_destination_score(
    destination: Destination,
    preferences: UserPreferences
) -> Dict[str, float]:
    """
    Calculate comprehensive destination score based on multiple factors
    Returns dict with individual and overall scores
    """
    scores = {}
    
    # Weather score (20% weight)
    if destination.weather:
        from app.services.weather_service import WeatherService
        weather_service = WeatherService()
        scores["weather"] = weather_service.calculate_weather_score(
            destination.weather, 
            preferences.preferred_weather
        )
    else:
        scores["weather"] = 50  # Neutral if no data
    
    # Affordability score (25% weight)
    if destination.affordability:
        from app.services.affordability_service import AffordabilityService
        affordability_service = AffordabilityService()
        scores["affordability"] = affordability_service.calculate_affordability_score(
            destination.affordability,
            preferences.budget_daily,
            preferences.travel_style.value
        )
    else:
        scores["affordability"] = 50
    
    # Visa score (15% weight)
    if destination.visa:
        from app.services.visa_service import VisaService
        visa_service = VisaService()
        scores["visa"] = visa_service.calculate_visa_score(
            destination.visa,
            preferences.visa_preference
        )
    else:
        scores["visa"] = 50
    
    # Attractions score (20% weight)
    if destination.attractions:
        from app.services.attractions_service import AttractionsService
        attractions_service = AttractionsService()
        scores["attractions"] = attractions_service.calculate_attractions_score(
            destination.attractions,
            [i.value for i in preferences.interests]
        )
    else:
        scores["attractions"] = 50
    
    # Events score (10% weight)
    if destination.events:
        scores["events"] = min(len(destination.events) * 10, 100)
    else:
        scores["events"] = 30  # Slight penalty for no events
    
    # Interest alignment bonus (10% weight)
    scores["interest_alignment"] = calculate_interest_alignment(
        destination, 
        preferences.interests
    )
    
    # Calculate weighted overall score
    weights = {
        "weather": 0.20,
        "affordability": 0.25,
        "visa": 0.15,
        "attractions": 0.20,
        "events": 0.10,
        "interest_alignment": 0.10
    }
    
    overall = sum(scores.get(k, 50) * w for k, w in weights.items())
    scores["overall"] = round(overall, 1)
    
    return scores

def calculate_interest_alignment(
    destination: Destination,
    interests: list
) -> float:
    """
    Calculate how well destination matches user interests
    Returns score 0-100
    """
    if not interests:
        return 50  # Neutral
    
    score = 0
    max_possible = 0
    
    interest_mappings = {
        Interest.NATURE: lambda d: sum(1 for a in d.attractions if a.natural_feature) if d.attractions else 0,
        Interest.BEACHES: lambda d: sum(1 for a in d.attractions if "beach" in a.type.lower()) if d.attractions else 0,
        Interest.MOUNTAINS: lambda d: sum(1 for a in d.attractions if "mountain" in a.type.lower() or "hiking" in a.type.lower()) if d.attractions else 0,
        Interest.CULTURE: lambda d: sum(1 for a in d.attractions if not a.natural_feature) if d.attractions else 0,
        Interest.HISTORY: lambda d: sum(1 for a in d.attractions if a.type in ["landmark", "museum"]) if d.attractions else 0,
        Interest.ART: lambda d: sum(1 for a in d.attractions if a.type == "museum") if d.attractions else 0,
        Interest.ADVENTURE: lambda d: sum(1 for a in d.attractions if a.type in ["hiking_area", "waterfall", "national_park"]) if d.attractions else 0,
        Interest.RELAXATION: lambda d: 1 if d.affordability and d.affordability.cost_level in ["budget", "moderate"] else 0,
        Interest.FOOD: lambda d: 1,  # Assume all destinations have food
        Interest.NIGHTLIFE: lambda d: sum(1 for e in d.events if e.type.value == "music") if d.events else 0,
        Interest.SHOPPING: lambda d: 1,  # Assume available
        Interest.WILDLIFE: lambda d: sum(1 for a in d.attractions if "wildlife" in a.description.lower() or "nature" in a.type.lower()) if d.attractions else 0,
    }
    
    for interest in interests:
        max_possible += 20
        if interest in interest_mappings:
            match_strength = interest_mappings[interest](destination)
            if isinstance(match_strength, int):
                if match_strength >= 3:
                    score += 20
                elif match_strength >= 1:
                    score += 10
    
    return min(100, (score / max_possible * 100) if max_possible > 0 else 50)

def get_score_breakdown(scores: Dict[str, float]) -> str:
    """Generate human-readable score breakdown"""
    breakdown = []
    emoji_map = {
        "weather": "🌤️",
        "affordability": "💰",
        "visa": "🛂",
        "attractions": "🎯",
        "events": "🎉",
        "interest_alignment": "❤️"
    }
    
    for key, score in scores.items():
        if key != "overall":
            emoji = emoji_map.get(key, "📊")
            label = key.replace("_", " ").title()
            breakdown.append(f"{emoji} {label}: {score:.0f}/100")
    
    return " | ".join(breakdown)