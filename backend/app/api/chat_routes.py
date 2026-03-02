"""
Enhanced Travel Chat Routes with Memory and Streaming
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import json

from app.services.chat_service import chat_service, ChatSession
from app.utils.logging_config import get_logger
from app.utils.security import get_current_user
from app.database.models import User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["AI Chat"])


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    extracted_preferences: Dict[str, Any]
    is_ready_for_recommendations: bool
    suggestions: List[str]


class StreamingChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    extracted_preferences: Dict[str, Any]
    is_ready_for_recommendations: bool
    current_intent: Optional[str]


class ExecuteActionRequest(BaseModel):
    session_id: str
    action_type: str
    params: Dict[str, Any]


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Send a message and get AI response
    
    This is the main chat endpoint for conversational travel planning.
    The AI will:
    - Remember conversation context
    - Extract travel preferences automatically
    - Provide personalized recommendations
    - Suggest next steps
    """
    session_id = request.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    
    try:
        session = await chat_service.send_message(
            session_id=session_id,
            user_message=request.message,
            user_id=user_id
        )
        
        # Get last assistant message
        from app.services.chat_service import ChatMessage
        last_message = session.messages[-1] if session.messages else ChatMessage(role='assistant', content='')
        
        # Generate smart suggestions based on context
        suggestions = generate_suggestions(session)
        
        return ChatResponse(
            session_id=session_id,
            response=last_message.content,
            extracted_preferences=session.extracted_preferences,
            is_ready_for_recommendations=session.is_ready_for_recommendations,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error("Chat message failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message/stream")
async def send_message_stream(
    request: StreamingChatRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Send a message and stream the AI response (ChatGPT-style)
    
    Returns a Server-Sent Events stream for real-time typing effect
    """
    session_id = request.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    
    async def generate_stream():
        try:
            async for token in chat_service.send_message_streaming(
                session_id=session_id,
                user_message=request.message,
                user_id=user_id
            ):
                # Send token as SSE
                yield f"data: {json.dumps({'token': token})}\n\n"
            
            # Send completion signal
            session = chat_service.get_session(session_id)
            if session:
                yield f"data: {json.dumps({
                    'done': True,
                    'extracted_preferences': session.extracted_preferences,
                    'is_ready': session.is_ready_for_recommendations
                })}\n\n"
                
        except Exception as e:
            logger.error("Stream error", error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
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
async def get_session_info(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get current session state and extracted preferences"""
    session = chat_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify ownership if user is authenticated
    if current_user and session.user_id and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    
    return SessionInfo(
        session_id=session.session_id,
        message_count=len(session.messages),
        extracted_preferences=session.extracted_preferences,
        is_ready_for_recommendations=session.is_ready_for_recommendations,
        current_intent=session.current_intent
    )


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Clear conversation history"""
    chat_service.clear_session(session_id)
    return {"message": "Session cleared"}


@router.post("/action")
async def execute_action(
    request: ExecuteActionRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Execute travel-related actions through the chat
    
    Actions:
    - search_flights: Search for flights
    - search_attractions: Find attractions
    - search_events: Find events
    - get_weather: Get weather forecast
    - search_hotels: Find accommodations
    """
    result = await chat_service.execute_action(
        session_id=request.session_id,
        action_type=request.action_type,
        params=request.params
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/suggestions/{session_id}")
async def get_suggestions(session_id: str):
    """Get smart conversation suggestions based on context"""
    session = chat_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    suggestions = generate_suggestions(session)
    return {"suggestions": suggestions}


def generate_suggestions(session: ChatSession) -> List[str]:
    """Generate context-aware conversation suggestions"""
    suggestions = []
    
    intent = session.current_intent
    prefs = session.extracted_preferences
    
    # If no destination mentioned yet
    if not prefs.get('destinations'):
        suggestions.extend([
            "🏖️ Beach vacation",
            "🏔️ Mountain adventure",
            "🏛️ Cultural city break",
            "🌴 Tropical getaway"
        ])
    
    # If destination mentioned but no dates
    if prefs.get('destinations') and not prefs.get('travel_dates'):
        suggestions.extend([
            "📅 When is the best time to visit?",
            "Help me pick travel dates",
            "What's the weather like there?"
        ])
    
    # If we have basic info, suggest next steps
    if session.is_ready_for_recommendations:
        suggestions.extend([
            "✈️ Search flights",
            "🏨 Find accommodations",
            "🗺️ Create an itinerary",
            "🎯 Show me recommendations"
        ])
    
    # Always include general options
    suggestions.extend([
        "💰 What's my budget breakdown?",
        "📋 Visa requirements",
        "🎭 Local events and festivals"
    ])
    
    return suggestions[:5]  # Return top 5

