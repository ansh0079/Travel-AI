from typing import List, Dict, Optional
from app.config import get_settings
from app.models.destination import Destination
from app.models.user import UserPreferences, TravelRequest, Interest
from app.utils.scoring import calculate_destination_score
import asyncio
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class AIRecommendationService:
    def __init__(self):
        self.settings = get_settings()
        self._client = None  # lazy AsyncOpenAI-compatible client

    def _get_client(self):
        """Return cached AsyncOpenAI client (supports OpenAI & DeepSeek), or None."""
        if self._client is not None:
            return self._client
        api_key = self.settings.openai_api_key
        if not api_key:
            return None
        try:
            from openai import AsyncOpenAI
            kwargs: dict = {"api_key": api_key}
            if self.settings.llm_base_url:
                kwargs["base_url"] = self.settings.llm_base_url
            self._client = AsyncOpenAI(**kwargs)
        except Exception as e:
            logger.warning("Failed to init LLM client", error=str(e))
        return self._client

    @property
    def model(self) -> str:
        return self.settings.llm_model
    
    async def generate_recommendations(
        self,
        request: TravelRequest,
        destinations: List[Destination]
    ) -> List[Destination]:
        """
        Generate AI-powered personalized recommendations
        1. Score all destinations based on user preferences
        2. Sort by overall score
        3. Generate AI explanations for top recommendations
        """
        # Calculate scores for all destinations
        scored_destinations = []
        for dest in destinations:
            scores = calculate_destination_score(dest, request.user_preferences)
            dest.weather_score = scores.get("weather", 0)
            dest.affordability_score = scores.get("affordability", 0)
            dest.visa_score = scores.get("visa", 0)
            dest.attractions_score = scores.get("attractions", 0)
            dest.events_score = scores.get("events", 0)
            dest.overall_score = scores.get("overall", 0)
            scored_destinations.append(dest)
        
        # Sort by overall score (descending)
        scored_destinations.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Select top N for AI enhancement
        top_destinations = scored_destinations[:request.num_recommendations]
        
        # Generate AI explanations for top recommendations
        if self._get_client():
            explanations = await self._generate_explanations_batch(
                top_destinations, 
                request.user_preferences,
                (request.travel_start, request.travel_end)
            )
            for dest, explanation in zip(top_destinations, explanations):
                dest.recommendation_reason = explanation
        else:
            # Fallback explanations
            for dest in top_destinations:
                dest.recommendation_reason = self._generate_fallback_explanation(
                    dest, request.user_preferences
                )
        
        return top_destinations
    
    async def _generate_explanations_batch(
        self,
        destinations: List[Destination],
        preferences: UserPreferences,
        travel_dates: tuple
    ) -> List[str]:
        """Generate AI explanations for multiple destinations"""
        tasks = [
            self._generate_single_explanation(dest, preferences, travel_dates)
            for dest in destinations
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _generate_single_explanation(
        self,
        destination: Destination,
        preferences: UserPreferences,
        travel_dates: tuple
    ) -> str:
        """Generate personalized explanation for a destination"""
        try:
            # Build context for the AI
            weather_info = ""
            if destination.weather:
                weather_info = f"{destination.weather.condition}, {destination.weather.temperature}°C"
            
            visa_info = ""
            if destination.visa:
                visa_info = "Visa-free" if not destination.visa.required else \
                    f"Visa required ({'eVisa available' if destination.visa.evisa_available else 'traditional'})"
            
            affordability_info = ""
            if destination.affordability:
                affordability_info = f"{destination.affordability.cost_level}, ~${destination.affordability.daily_cost_estimate}/day"
            
            events_info = f"{len(destination.events)} events during your stay" if destination.events else "No major events"
            
            attractions_info = ""
            if destination.attractions:
                natural_count = sum(1 for a in destination.attractions if a.natural_feature)
                cultural_count = len(destination.attractions) - natural_count
                attractions_info = f"{natural_count} natural, {cultural_count} cultural attractions"
            
            prompt = f"""Generate a compelling, personalized travel recommendation (2-3 sentences) for {destination.name}, {destination.country}.

User Profile:
- Budget: ${preferences.budget_daily}/day ({preferences.travel_style.value})
- Interests: {', '.join(i.value for i in preferences.interests) if preferences.interests else 'Not specified'}
- Travel Dates: {travel_dates[0]} to {travel_dates[1]}
- Traveling with: {preferences.traveling_with}

Destination Analysis:
- Weather: {weather_info}
- Cost Level: {affordability_info}
- Visa: {visa_info}
- Attractions: {attractions_info}
- Events: {events_info}
- Match Score: {destination.overall_score:.0f}/100

Highlight:
1. Why this matches their interests and budget
2. Any special events or seasonal highlights
3. Practical tip about weather or logistics

Make it warm, enthusiastic, and specific to this traveler."""

            client = self._get_client()
            if not client:
                return self._generate_fallback_explanation(destination, preferences)
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert travel advisor who creates personalized, compelling destination recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning("LLM error for destination", destination=destination.name, error=str(e))
            return self._generate_fallback_explanation(destination, preferences)
    
    def _generate_fallback_explanation(
        self,
        destination: Destination,
        preferences: UserPreferences
    ) -> str:
        """Generate fallback explanation when AI is unavailable"""
        reasons = []
        
        # Score-based reasons
        if destination.affordability_score >= 80:
            reasons.append(f"Fits perfectly within your ${preferences.budget_daily}/day budget")
        
        if destination.weather_score >= 80:
            reasons.append("Ideal weather for your travel dates")
        
        if destination.visa_score >= 80:
            reasons.append("Hassle-free visa requirements")
        
        if destination.attractions_score >= 80:
            interests = [i.value for i in preferences.interests]
            if any(i in ["nature", "beaches", "mountains"] for i in interests):
                reasons.append("Excellent natural attractions for outdoor enthusiasts")
            if any(i in ["culture", "history", "art"] for i in interests):
                reasons.append("Rich cultural and historical experiences")
        
        if destination.events and len(destination.events) > 0:
            reasons.append(f"{len(destination.events)} exciting events during your stay")
        
        if not reasons:
            reasons.append(f"Great {preferences.travel_style.value} destination with an overall match score of {destination.overall_score:.0f}%")
        
        return " | ".join(reasons)
    
    async def generate_travel_tips(
        self,
        destination: Destination,
        preferences: UserPreferences
    ) -> List[str]:
        """Generate personalized travel tips"""
        tips = []
        
        # Weather-based tips
        if destination.weather:
            if destination.weather.temperature > 30:
                tips.append("🌡️ Pack light, breathable clothing and stay hydrated")
            elif destination.weather.temperature < 10:
                tips.append("🧥 Bring warm layers and a waterproof jacket")
            if destination.weather.condition == "Rain":
                tips.append("☔ Pack a compact umbrella and waterproof shoes")
        
        # Visa tips
        if destination.visa and destination.visa.required:
            if destination.visa.evisa_available:
                tips.append(f"📄 Apply for eVisa online ({destination.visa.processing_days or 'a few'} days processing)")
            else:
                tips.append("🛂 Contact the embassy well in advance for visa requirements")
        
        # Budget tips
        if destination.affordability:
            if destination.affordability.cost_level == "budget":
                tips.append("💰 Great value destination - your budget will go far here!")
            elif destination.affordability.cost_level == "luxury":
                tips.append("💎 Premium destination - consider prioritizing must-see experiences")
        
        # Attraction tips based on interests
        if destination.attractions:
            natural_count = sum(1 for a in destination.attractions if a.natural_feature)
            if natural_count > 3 and any(i in [Interest.NATURE, Interest.BEACHES, Interest.MOUNTAINS] for i in preferences.interests):
                tips.append(f"🏔️ Don't miss the {natural_count} beautiful natural attractions nearby")
        
        return tips[:5]  # Limit to 5 tips
    
    async def compare_destinations(
        self,
        destinations: List[Destination],
        preferences: UserPreferences
    ) -> str:
        """Generate AI comparison of destinations"""
        client = self._get_client()
        if not client or len(destinations) < 2:
            return ""

        try:
            dest_summary = "\n".join([
                f"{i+1}. {d.name}, {d.country} (Score: {d.overall_score:.0f}/100) - "
                f"{d.affordability.cost_level if d.affordability else 'Unknown cost'}, "
                f"{'Visa-free' if d.visa and not d.visa.required else 'Visa required'}"
                for i, d in enumerate(destinations[:3])
            ])

            prompt = f"""Compare these top 3 destinations for a traveler with:
- Budget: ${preferences.budget_daily}/day
- Style: {preferences.travel_style.value}
- Interests: {', '.join(i.value for i in preferences.interests) if preferences.interests else 'Not specified'}

Destinations:
{dest_summary}

Provide a brief comparison (2-3 sentences) highlighting the key differences and best fit for this traveler."""

            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning("AI comparison error", error=str(e))
            return ""