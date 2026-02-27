"""
AI Provider abstraction for travel recommendations
Supports OpenAI, Anthropic, and mock fallback
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def generate_recommendations(
        self, 
        preferences: Dict[str, Any],
        destinations: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate travel recommendations"""
        pass
    
    @abstractmethod
    async def analyze_destination(
        self, 
        destination: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze a destination and provide insights"""
        pass


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model = model
        self.client = None
        if api_key:
            try:
                from openai import AsyncOpenAI
                kwargs: dict = {"api_key": api_key}
                if base_url:
                    kwargs["base_url"] = base_url
                self.client = AsyncOpenAI(**kwargs)
            except ImportError:
                pass
    
    async def generate_recommendations(
        self,
        preferences: Dict[str, Any],
        destinations: List[str]
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return await MockAIProvider().generate_recommendations(preferences, destinations)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a travel expert. Provide recommendations in JSON format."},
                {"role": "user", "content": f"Recommend destinations from {destinations} based on preferences: {json.dumps(preferences)}. Return as JSON array with destination, score, and reasons."}
            ]
        )
        return self._parse_response(response.choices[0].message.content)

    async def analyze_destination(
        self,
        destination: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.client:
            return await MockAIProvider().analyze_destination(destination, context)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Analyze this destination and return JSON with highlights, tips, and best_for."},
                {"role": "user", "content": f"Analyze {destination} with context: {json.dumps(context)}"}
            ]
        )
        return self._parse_response(response.choices[0].message.content)
    
    def _parse_response(self, content: str) -> Any:
        try:
            return json.loads(content)
        except:
            return {"raw_response": content}


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = None
        if api_key:
            try:
                from anthropic import AsyncAnthropic
                self.client = AsyncAnthropic(api_key=api_key)
            except ImportError:
                pass
    
    async def generate_recommendations(
        self, 
        preferences: Dict[str, Any],
        destinations: List[str]
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return MockAIProvider().generate_recommendations(preferences, destinations)
        
        response = await self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{"role": "user", "content": f"Recommend destinations from {destinations} based on: {json.dumps(preferences)}. Return JSON."}]
        )
        return self._parse_response(response.content[0].text)
    
    async def analyze_destination(
        self, 
        destination: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.client:
            return MockAIProvider().analyze_destination(destination, context)
        
        response = await self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{"role": "user", "content": f"Analyze {destination} with context: {json.dumps(context)}. Return JSON."}]
        )
        return self._parse_response(response.content[0].text)
    
    def _parse_response(self, content: str) -> Any:
        try:
            return json.loads(content)
        except:
            return {"raw_response": content}


class MockAIProvider(AIProvider):
    """Mock AI provider for when no API keys are available"""
    
    async def generate_recommendations(
        self, 
        preferences: Dict[str, Any],
        destinations: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate simple mock recommendations based on matching interests"""
        interests = preferences.get("interests", [])
        budget = preferences.get("budget_level", "moderate")
        
        scored = []
        for dest in destinations[:5]:
            score = 70  # Base score
            
            # Budget matching
            if budget == "low" and any(c in dest.lower() for c in ["thailand", "vietnam", "india", "mexico"]):
                score += 15
            elif budget == "luxury" and any(c in dest.lower() for c in ["switzerland", "monaco", "dubai", "maldives"]):
                score += 15
            
            # Interest matching (simplified)
            if "beach" in interests and any(c in dest.lower() for c in ["bali", "phuket", "maldives", "maui"]):
                score += 10
            if "city" in interests and any(c in dest.lower() for c in ["tokyo", "paris", "london", "new york"]):
                score += 10
            
            reasons = [
                f"Great match for {budget} budget travelers",
                f"Perfect for {', '.join(interests[:2])}" if interests else "Popular destination"
            ]
            
            scored.append({
                "destination": dest,
                "score": min(98, score),
                "reasons": reasons,
                "ai_analyzed": False
            })
        
        return sorted(scored, key=lambda x: x["score"], reverse=True)
    
    async def analyze_destination(
        self, 
        destination: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "highlights": [f"Famous landmarks in {destination}", "Local culture and cuisine", "Beautiful scenery"],
            "tips": ["Book accommodations early", "Try local food", "Use public transport"],
            "best_for": ["First-time visitors", "Culture enthusiasts"],
            "ai_analyzed": False
        }


class AIFactory:
    """Factory for creating AI providers"""
    
    @staticmethod
    def create_provider(provider_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-3.5-turbo") -> AIProvider:
        """Create an AI provider instance"""
        if provider_name.lower() == "mock":
            return MockAIProvider()
        if provider_name.lower() == "anthropic":
            return AnthropicProvider(api_key)
        # openai and deepseek both use OpenAIProvider (OpenAI-compatible API)
        return OpenAIProvider(api_key=api_key, base_url=base_url, model=model)

    @staticmethod
    def create_from_settings() -> AIProvider:
        """Create provider based on app settings (reads LLM_PROVIDER env var)."""
        from app.config import get_settings
        settings = get_settings()

        provider = settings.llm_provider.lower()  # "openai" | "deepseek" | "anthropic" | "mock"
        api_key = settings.openai_api_key
        base_url = settings.llm_base_url
        model = settings.llm_model

        if provider == "anthropic":
            anthropic_key = getattr(settings, "anthropic_api_key", None)
            return AnthropicProvider(api_key=anthropic_key)

        if not api_key:
            return MockAIProvider()

        # deepseek uses base_url https://api.deepseek.com/v1; openai uses default
        return OpenAIProvider(api_key=api_key, base_url=base_url, model=model)
