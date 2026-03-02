"""
Enhanced Travel Chat Routes
Now uses the unified ChatService for better conversation management
Maintains backward compatibility with legacy /chat endpoint
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date
import uuid
import json

from app.utils.logging_config import get_logger
from app.services.chat_service import chat_service, ChatSession
from app.services.ai_providers import AIFactory
from app.services.weather_service import WeatherService
from app.services.visa_service import VisaService
from app.services.attractions_service import AttractionsService
from app.utils.security import get_current_user_optional
from app.database.models import User

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["Travel Chat"])


# ============= Legacy Models (for backward compatibility) =============

class LegacyChatMessage(BaseModel):
    user_id: str
    message: str


class LegacyChatResponse(BaseModel):
    response: str


# ============= New Enhanced Models =============

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    session_id: str
    response: str
    extracted_preferences: Dict[str, Any]
    is_ready_for_recommendations: bool
    suggestions: List[str]
    planning_stage: str


class TravelChatMessage(BaseModel):
    role: str
    content: str


class TravelChatRequest(BaseModel):
    messages: List[TravelChatMessage]


class TravelChatResponse(BaseModel):
    reply: str
    extracted: Dict[str, Any]
    ready: bool
    suggestions: List[str]


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    extracted_preferences: Dict[str, Any]
    is_ready_for_recommendations: bool
    current_intent: Optional[str]
    planning_stage: str
    planning_data: Dict[str, Any]


class StreamingChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ExecuteActionRequest(BaseModel):
    session_id: str
    action_type: str
    params: Dict[str, Any]


class PipelineAdvanceRequest(BaseModel):
    stage: Optional[str] = None


class PlanningDataUpdateRequest(BaseModel):
    planning_data: Dict[str, Any]


class RankingRequest(BaseModel):
    session_id: str
    candidates: List[str]
    constraints: Optional[Dict[str, Any]] = None


class FeedbackRequest(BaseModel):
    session_id: str
    destination: str
    feedback: float  # -1 to 1


class TripPlanningRequest(BaseModel):
    destination: str
    duration_days: int
    budget_level: str = "moderate"  # low, moderate, luxury
    interests: List[str]
    start_date: Optional[date] = None


class DayPlan(BaseModel):
    day: int
    theme: str
    morning_activity: str
    afternoon_activity: str
    evening_activity: str
    dining_suggestion: str


class TripPlanResponse(BaseModel):
    destination: str
    itinerary: List[DayPlan]
    estimated_cost: str
    weather_note: Optional[str] = None


class TrendingDestination(BaseModel):
    id: str
    name: str
    image_url: str
    vibe_tag: str
    description: str

# ============= Mock Geocoder (for demo/tool usage) =============

MOCK_GEOCODER = {
    "paris": {"lat": 48.8566, "lon": 2.3522, "name": "Paris"},
    "london": {"lat": 51.5072, "lon": -0.1276, "name": "London"},
    "new york": {"lat": 40.7128, "lon": -74.0060, "name": "New York"},
    "tokyo": {"lat": 35.6762, "lon": 139.6503, "name": "Tokyo"},
    "rome": {"lat": 41.9028, "lon": 12.4964, "name": "Rome"},
    "japan": {"country_code": "JP"},
    "thailand": {"country_code": "TH"},
    "france": {"country_code": "FR"},
    "italy": {"country_code": "IT"},
    "spain": {"country_code": "ES"},
    "germany": {"country_code": "DE"},
    "australia": {"country_code": "AU"},
    "canada": {"country_code": "CA"},
    "mexico": {"country_code": "MX"},
    "brazil": {"country_code": "BR"},
    "india": {"country_code": "IN"},
    "china": {"country_code": "CN"},
    "south korea": {"country_code": "KR"},
    "singapore": {"country_code": "SG"},
    "dubai": {"country_code": "AE"},
    "uae": {"country_code": "AE"},
}


# ============= Enhanced Chat Endpoints =============

@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Send a message to the AI travel assistant
    
    This endpoint:
    - Maintains conversation memory
    - Extracts travel preferences automatically
    - Provides context-aware responses
    - Returns smart suggestions
    
    Perfect for building a ChatGPT-like travel planning experience.
    """
    session_id = request.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None

    # Prevent session hijacking by enforcing ownership for user-bound sessions
    if request.session_id:
        _ensure_session_access(session_id=request.session_id, current_user=current_user, allow_missing=True)
    
    try:
        session = await chat_service.send_message(
            session_id=session_id,
            user_message=request.message,
            user_id=user_id
        )
        
        # Get last assistant message
        last_message = session.messages[-1] if session.messages else None
        response_text = last_message.content if last_message else "I'm here to help with your travel plans!"
        
        # Generate smart suggestions
        suggestions = _generate_suggestions(session)
        
        return ChatMessageResponse(
            session_id=session_id,
            response=response_text,
            extracted_preferences=session.extracted_preferences,
            is_ready_for_recommendations=session.is_ready_for_recommendations,
            suggestions=suggestions,
            planning_stage=session.planning_stage
        )
        
    except Exception as e:
        logger.error("Chat message failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Chat processing failed")


@router.post("/message/stream")
async def send_message_stream(
    request: StreamingChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Send a message and stream AI response as Server-Sent Events."""
    session_id = request.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None

    if request.session_id:
        _ensure_session_access(session_id=request.session_id, current_user=current_user, allow_missing=True)

    async def generate_stream():
        try:
            async for token in chat_service.send_message_streaming(
                session_id=session_id,
                user_message=request.message,
                user_id=user_id
            ):
                yield f"data: {json.dumps({'token': token})}\n\n"

            session = chat_service.get_session(session_id)
            if session:
                yield f"data: {json.dumps({'done': True, 'extracted_preferences': session.extracted_preferences, 'is_ready': session.is_ready_for_recommendations, 'planning_stage': session.planning_stage})}\n\n"
        except Exception as e:
            logger.error("Stream error", error=str(e), exc_info=True)
            yield f"data: {json.dumps({'error': 'Streaming failed'})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get current session state and extracted preferences"""
    session = _ensure_session_access(session_id=session_id, current_user=current_user)
    
    return SessionInfo(
        session_id=session.session_id,
        message_count=len(session.messages),
        extracted_preferences=session.extracted_preferences,
        is_ready_for_recommendations=session.is_ready_for_recommendations,
        current_intent=session.current_intent,
        planning_stage=session.planning_stage,
        planning_data=session.planning_data
    )


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Clear conversation history"""
    _ensure_session_access(session_id=session_id, current_user=current_user)
    chat_service.clear_session(session_id)
    return {"message": "Session cleared", "session_id": session_id}


@router.post("/pipeline/{session_id}/advance")
async def advance_pipeline_stage(
    session_id: str,
    request: PipelineAdvanceRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Advance planning pipeline stage or set an explicit stage."""
    _ensure_session_access(session_id=session_id, current_user=current_user)
    result = await chat_service.advance_pipeline_stage(session_id=session_id, target_stage=request.stage)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/pipeline/{session_id}")
async def update_pipeline_data(
    session_id: str,
    request: PlanningDataUpdateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Update structured planning data for the current stage."""
    _ensure_session_access(session_id=session_id, current_user=current_user)
    result = await chat_service.update_planning_data(session_id=session_id, planning_data=request.planning_data)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/travel", response_model=TravelChatResponse)
async def travel_chat_legacy(request: TravelChatRequest):
    """
    Legacy travel chat endpoint (for backward compatibility)
    Accepts array of messages, returns single response
    """
    # Create a temporary session for this conversation
    session_id = f"temp_{uuid.uuid4()}"
    
    # Use the last user message
    last_message = None
    for msg in reversed(request.messages):
        if msg.role == 'user':
            last_message = msg.content
            break
    
    if not last_message:
        return TravelChatResponse(
            reply="I didn't catch that. Could you tell me more about your travel plans?",
            extracted={},
            ready=False,
            suggestions=[]
        )
    
    # Process through new chat service
    session = await chat_service.send_message(
        session_id=session_id,
        user_message=last_message,
        user_id=None
    )
    
    last_response = session.messages[-1] if session.messages else None
    
    return TravelChatResponse(
        reply=last_response.content if last_response else "I'm here to help!",
        extracted=session.extracted_preferences,
        ready=session.is_ready_for_recommendations,
        suggestions=_generate_suggestions(session)
    )


@router.post("/action")
async def execute_action(
    request: ExecuteActionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Execute travel-related actions through the chat
    
    Available actions:
    - search_flights: Search for flights
    - search_attractions: Find attractions
    - search_events: Find events
    - get_weather: Get weather forecast
    - search_hotels: Find accommodations
    - get_visa_requirements: Check visa requirements
    """
    _ensure_session_access(session_id=request.session_id, current_user=current_user)
    result = await chat_service.execute_action(
        session_id=request.session_id,
        action_type=request.action_type,
        params=request.params
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/recommendations/rank")
async def rank_recommendations(
    request: RankingRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Rank destination candidates with explainability and hard constraints."""
    _ensure_session_access(session_id=request.session_id, current_user=current_user)
    result = await chat_service.rank_destinations(
        session_id=request.session_id,
        candidates=request.candidates,
        constraints=request.constraints or {},
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/recommendations/feedback")
async def submit_recommendation_feedback(
    request: FeedbackRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Store preference feedback for re-ranking future destination recommendations."""
    _ensure_session_access(session_id=request.session_id, current_user=current_user)
    result = await chat_service.submit_recommendation_feedback(
        session_id=request.session_id,
        destination=request.destination,
        feedback=request.feedback,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/suggestions/{session_id}")
async def get_suggestions(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get smart conversation suggestions based on context"""
    session = _ensure_session_access(session_id=session_id, current_user=current_user)
    
    return {"suggestions": _generate_suggestions(session)}


@router.post("/plan", response_model=TripPlanResponse)
async def generate_structured_itinerary(request: TripPlanningRequest):
    """
    Generates a structured day-by-day itinerary based on preferences and weather.
    Returns JSON data suitable for rendering a timeline UI.
    """
    ai_provider = AIFactory.create_from_settings()
    weather_service = WeatherService()
    
    # 1. Try to get weather context to make the plan "smart"
    weather_context = "Weather data unavailable"
    city_slug = request.destination.lower()
    if city_slug in MOCK_GEOCODER:
        coords = MOCK_GEOCODER[city_slug]
        try:
            # Fetch weather for the start date or today
            target_date = request.start_date or date.today()
            weather_data = await weather_service.get_weather(coords["lat"], coords["lon"], target_date)
            weather_context = f"{weather_data.get('condition', 'Unknown')}, {weather_data.get('temperature', '?')}°C"
        except Exception as e:
            logger.warning(f"Could not fetch weather for planning: {e}")

    # 2. Construct the prompt
    system_prompt = (
        "You are an expert travel planner. Create a structured itinerary based on the user's request. "
        "Return ONLY valid JSON matching the specified structure. "
        "Consider the weather when planning activities (e.g., museums for rain, parks for sun)."
    )
    
    user_prompt = (
        f"Plan a {request.duration_days}-day trip to {request.destination}. "
        f"Budget: {request.budget_level}. Interests: {', '.join(request.interests)}. "
        f"Weather forecast: {weather_context}. "
        "Provide a JSON response with this structure: "
        "{ 'destination': str, 'estimated_cost': str, 'weather_note': str, "
        "'itinerary': [{ 'day': int, 'theme': str, 'morning_activity': str, "
        "'afternoon_activity': str, 'evening_activity': str, 'dining_suggestion': str }] }"
    )

    # 3. Call AI
    try:
        client = getattr(ai_provider, 'client', None)
        if not client:
            # Fallback for MockAIProvider
            return TripPlanResponse(
                destination=request.destination,
                estimated_cost="$2000 (Mock)",
                weather_note="Mock weather data",
                itinerary=[
                    DayPlan(
                        day=1, theme="Arrival", morning_activity="Check-in", 
                        afternoon_activity="Explore city center", evening_activity="Dinner", 
                        dining_suggestion="Local bistro"
                    )
                ]
            )

        response = await client.chat.completions.create(
            model=getattr(ai_provider, 'model', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}, # Ensure JSON output
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        # Validate and return
        return TripPlanResponse(**data)

    except Exception as e:
        logger.error("Failed to generate itinerary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate itinerary")


@router.get("/trending", response_model=List[TrendingDestination])
async def get_trending_destinations():
    """
    Get trending destinations with high-quality imagery for the home screen.
    Used to populate the UI with inspiring travel vibes.
    """
    return [
        TrendingDestination(
            id="tokyo",
            name="Tokyo, Japan",
            image_url="https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?q=80&w=1000&auto=format&fit=crop",
            vibe_tag="Neon & Tradition",
            description="Experience the perfect blend of futuristic tech and ancient temples."
        ),
        TrendingDestination(
            id="santorini",
            name="Santorini, Greece",
            image_url="https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?q=80&w=1000&auto=format&fit=crop",
            vibe_tag="Sun & Sea",
            description="White-washed buildings, blue domes, and breathtaking sunsets."
        ),
        TrendingDestination(
            id="iceland",
            name="Iceland",
            image_url="https://images.unsplash.com/photo-1476610182048-b716b8518aae?q=80&w=1000&auto=format&fit=crop",
            vibe_tag="Adventure",
            description="Chase the Northern Lights and explore dramatic landscapes."
        )
    ]


# ============= Legacy Endpoint (Backward Compatible) =============

@router.post("/chat", response_model=LegacyChatResponse, deprecated=False)
async def legacy_travel_chat(chat_message: LegacyChatMessage):
    """
    Legacy chat endpoint - maintains backward compatibility
    Uses enhanced chat service with tool calling support
    """
    logger.info("Received legacy chat message", user_id=chat_message.user_id)
    
    # Create session for this conversation
    session_id = f"legacy_{chat_message.user_id}_{uuid.uuid4()}"
    
    try:
        session = await chat_service.send_message(
            session_id=session_id,
            user_message=chat_message.message,
            user_id=chat_message.user_id
        )
        
        last_message = session.messages[-1] if session.messages else None
        response_text = last_message.content if last_message else "I'm here to help with your travel plans!"
        
        return LegacyChatResponse(response=response_text)
        
    except Exception as e:
        logger.error("Legacy chat failed", error=str(e), exc_info=True)
        # Fallback to tool-based approach if chat service fails
        return await _fallback_tool_chat(chat_message.message)


# ============= Helper Functions =============

def _generate_suggestions(session: ChatSession) -> List[str]:
    """Generate context-aware conversation suggestions"""
    suggestions = []
    intent = session.current_intent
    prefs = session.extracted_preferences
    
    # No destination yet
    if not prefs.get('destinations'):
        suggestions.extend([
            "🏖️ Beach vacation ideas",
            "🏔️ Mountain adventure",
            "🏛️ Cultural city break",
            "🌴 Tropical getaway"
        ])
    
    # Has destination but no dates
    if prefs.get('destinations') and not prefs.get('travel_dates'):
        suggestions.extend([
            "📅 When is the best time to visit?",
            "What's the weather like there?",
            "Help me pick travel dates"
        ])
    
    # Ready for recommendations
    if session.is_ready_for_recommendations:
        suggestions.extend([
            "✈️ Search flights",
            "🏨 Find accommodations",
            "🗺️ Create an itinerary",
            "🎯 Show me recommendations"
        ])
    
    # General options
    suggestions.extend([
        "💰 Budget breakdown",
        "📋 Visa requirements",
        "🎭 Local events and festivals"
    ])
    
    return list(dict.fromkeys(suggestions))[:5]  # Deduplicate and limit to 5


def _ensure_session_access(
    session_id: str,
    current_user: Optional[User],
    allow_missing: bool = False,
) -> Optional[ChatSession]:
    """Validate session visibility for authenticated and anonymous users."""
    session = chat_service.get_session(session_id)
    if not session:
        if allow_missing:
            return None
        raise HTTPException(status_code=404, detail="Session not found")

    # User-owned sessions are only visible to that user.
    if session.user_id:
        if not current_user or current_user.id != session.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

    return session


async def _fallback_tool_chat(message: str) -> LegacyChatResponse:
    """
    Fallback to tool-based chat if main service fails
    Maintains the original tool-calling functionality
    """
    ai_provider = AIFactory.create_from_settings()
    
    if ai_provider.__class__.__name__ == "MockAIProvider":
        if "weather" in message.lower():
            return LegacyChatResponse(response="I can help with weather! Which city are you interested in? 🌤️")
        elif "visa" in message.lower():
            return LegacyChatResponse(response="I can check visa requirements! What's your passport country and destination? 🛂")
        elif "attraction" in message.lower() or "visit" in message.lower():
            return LegacyChatResponse(response="I can find attractions! Which city would you like to explore? 🏛️")
        else:
            return LegacyChatResponse(response="I'm your AI travel assistant! Ask me about weather, visas, or attractions. ✈️")
    
    try:
        client = getattr(ai_provider, 'client', None)
        if not client:
            raise AttributeError("AI Provider client not available")
        
        system_prompt = (
            "You are TravelAI, a friendly travel assistant. "
            "Help users plan trips with accurate, helpful information. "
            "Use tools when you need real-time data. "
            "Be concise and engaging."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather_for_city",
                    "description": "Get weather forecast for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "City name"}
                        },
                        "required": ["city"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_visa_requirements",
                    "description": "Get visa requirements between countries",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "passport_country": {"type": "string", "description": "2-letter ISO code"},
                            "destination_country": {"type": "string", "description": "2-letter ISO code"},
                        },
                        "required": ["passport_country", "destination_country"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_attractions",
                    "description": "Get top attractions in a city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "City name"}
                        },
                        "required": ["city"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "suggest_packing_list",
                    "description": "Suggest items to pack based on destination and weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string"},
                            "duration_days": {"type": "integer"}
                        },
                        "required": ["destination"],
                    },
                },
            }
        ]
        
        response = await client.chat.completions.create(
            model=getattr(ai_provider, 'model', 'gpt-3.5-turbo'),
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        if tool_calls:
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                tool_response = ""
                
                if function_name == "get_weather_for_city":
                    city = function_args.get("city", "").lower()
                    coords = MOCK_GEOCODER.get(city)
                    if coords and "lat" in coords:
                        weather = await WeatherService().get_weather(
                            coords["lat"], coords["lon"], date.today()
                        )
                        tool_response = json.dumps(weather)
                    else:
                        tool_response = json.dumps({"error": "City not found"})
                
                elif function_name == "get_visa_requirements":
                    visa = await VisaService().get_visa_requirements(
                        function_args.get("passport_country", "US"),
                        function_args.get("destination_country", "FR")
                    )
                    tool_response = json.dumps(visa)
                
                elif function_name == "get_attractions":
                    attractions = await AttractionsService().get_natural_attractions(
                        function_args.get("city", "Paris")
                    )
                    tool_response = json.dumps(attractions)

                elif function_name == "suggest_packing_list":
                    # Simple logic: check weather and return advice
                    dest = function_args.get("destination", "").lower()
                    coords = MOCK_GEOCODER.get(dest)
                    weather_cond = "unknown"
                    if coords:
                        w = await WeatherService().get_weather(coords["lat"], coords["lon"], date.today())
                        weather_cond = w.get("condition", "unknown")
                    
                    tool_response = json.dumps({
                        "weather_condition": weather_cond,
                        "essentials": ["Passport", "Chargers"],
                        "weather_specific": ["Umbrella"] if "Rain" in weather_cond else ["Sunscreen"]
                    })
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_response,
                })
            
            second_response = await client.chat.completions.create(
                model=getattr(ai_provider, 'model', 'gpt-3.5-turbo'),
                messages=messages,
            )
            response_text = second_response.choices[0].message.content.strip()
        else:
            response_text = response_message.content.strip()
        
        return LegacyChatResponse(response=response_text)
        
    except Exception as e:
        logger.error("Fallback chat failed", error=str(e))
        return LegacyChatResponse(
            response="I'm having trouble connecting right now. Please try again in a moment!"
        )
