"""
AI Agent API Routes
Endpoints for the autonomous travel research agent
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from app.services.agent_service import TravelResearchAgent, research_travel_destination

router = APIRouter(prefix="/api/v1/agent", tags=["ai-agent"])


# Request/Response Models
class ResearchRequest(BaseModel):
    destination: str
    travel_start: Optional[date] = None
    travel_end: Optional[date] = None
    interests: Optional[List[str]] = []
    budget: Optional[str] = None  # low, moderate, high, luxury


class CompareRequest(BaseModel):
    destinations: List[str]
    criteria: List[str] = ["affordability", "weather", "activities", "safety"]
    travel_start: Optional[date] = None
    travel_end: Optional[date] = None


class HiddenGemsRequest(BaseModel):
    region: str
    interests: List[str] = []
    avoid_crowds: bool = True


class ItineraryResearchRequest(BaseModel):
    destination: str
    days: int
    interests: List[str] = []
    travel_style: str = "moderate"


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[dict]] = []
    user_preferences: Optional[dict] = None


# Initialize agent
agent = TravelResearchAgent()


@router.post("/research")
async def research_destination(request: ResearchRequest):
    """
    Have the AI agent research a destination comprehensively
    """
    try:
        travel_dates = None
        if request.travel_start and request.travel_end:
            travel_dates = (request.travel_start, request.travel_end)
        
        result = await agent.research_destination(
            destination=request.destination,
            travel_dates=travel_dates,
            interests=request.interests,
            budget=request.budget
        )
        
        return {
            "status": "success",
            "agent_id": f"research_{request.destination.lower().replace(' ', '_')}",
            "result": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent research failed: {str(e)}")


@router.post("/compare")
async def compare_destinations(request: CompareRequest):
    """
    Have the AI agent compare multiple destinations
    """
    try:
        travel_dates = None
        if request.travel_start and request.travel_end:
            travel_dates = (request.travel_start, request.travel_end)
        
        result = await agent.compare_destinations(
            destinations=request.destinations,
            criteria=request.criteria,
            travel_dates=travel_dates
        )
        
        return {
            "status": "success",
            "agent_id": "comparison_agent",
            "result": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent comparison failed: {str(e)}")


@router.post("/hidden-gems")
async def find_hidden_gems(request: HiddenGemsRequest):
    """
    Find lesser-known destinations and experiences
    """
    try:
        gems = await agent.find_hidden_gems(
            region=request.region,
            interests=request.interests,
            avoid_crowds=request.avoid_crowds
        )
        
        return {
            "status": "success",
            "region": request.region,
            "gems_found": len(gems),
            "hidden_gems": gems
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hidden gems search failed: {str(e)}")


@router.post("/itinerary-research")
async def research_itinerary(request: ItineraryResearchRequest):
    """
    Research and suggest day-by-day itinerary
    """
    try:
        result = await agent.research_itinerary(
            destination=request.destination,
            days=request.days,
            interests=request.interests,
            travel_style=request.travel_style
        )
        
        return {
            "status": "success",
            "agent_id": "itinerary_planner",
            "result": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Itinerary research failed: {str(e)}")


@router.post("/travel-advisory")
async def check_travel_advisory(destination: str):
    """
    Check current travel advisories for a destination
    """
    try:
        result = await agent.check_travel_advisories(destination)
        
        return {
            "status": "success",
            "destination": destination,
            "advisory": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advisory check failed: {str(e)}")


@router.post("/chat")
async def agent_chat(request: ChatRequest):
    """
    Chat with the AI agent - natural language travel queries
    """
    try:
        message = request.message.lower()
        
        # Simple intent detection
        if any(word in message for word in ["research", "tell me about", "info on", "what is"]):
            # Extract destination (simplified)
            words = message.replace("tell me about", "").replace("research", "").replace("what is", "").strip()
            if words:
                result = await research_travel_destination(words[:50])
                return {
                    "status": "success",
                    "response_type": "research",
                    "message": f"I've researched {words[:50]}. Here's what I found:",
                    "data": result
                }
        
        elif any(word in message for word in ["compare", "vs", "versus", "difference between"]):
            # Extract destinations to compare
            return {
                "status": "success",
                "response_type": "comparison_prompt",
                "message": "I'd be happy to compare destinations for you! Please use the compare tool and enter the destinations you'd like to compare."
            }
        
        elif any(word in message for word in ["hidden gem", "secret", "off beaten", "less touristy"]):
            # Extract region
            return {
                "status": "success",
                "response_type": "gems_prompt",
                "message": "I can help you find hidden gems! Please specify which region you're interested in exploring."
            }
        
        elif any(word in message for word in ["itinerary", "plan", "schedule", "day by day"]):
            return {
                "status": "success",
                "response_type": "itinerary_prompt",
                "message": "I can help plan your itinerary! Please provide your destination, number of days, and interests."
            }
        
        # Default response
        return {
            "status": "success",
            "response_type": "general",
            "message": "I'm your AI travel research assistant! I can:\n\n🔍 Research destinations in depth\n📊 Compare multiple destinations\n💎 Find hidden gems\n📅 Plan day-by-day itineraries\n⚠️ Check travel advisories\n\nWhat would you like me to help you with?"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent chat failed: {str(e)}")


@router.get("/status")
async def agent_status():
    """
    Check if the AI agent is operational
    """
    return {
        "status": "operational",
        "agent_name": "TravelAI Research Agent",
        "capabilities": [
            "web_search",
            "destination_research",
            "destination_comparison",
            "hidden_gems_discovery",
            "itinerary_planning",
            "travel_advisory_check"
        ],
        "version": "1.0.0"
    }
