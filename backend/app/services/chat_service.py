"""
Unified AI Chat Service with Memory and Context
Provides a ChatGPT-like conversational experience for travel planning
"""

from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from datetime import datetime, timedelta, date
from collections import OrderedDict
from pydantic import BaseModel, Field
import json
import asyncio
import re
import hashlib

from app.config import get_settings
from app.services.ai_providers import AIFactory
from app.services.travelgenie_service import travelgenie_service
from app.services.visa_service import VisaService
from app.services.events_service import EventsService
from app.services.flight_service import FlightService
from app.utils.logging_config import get_logger
from app.database.connection import SessionLocal
from app.database.models import User, UserPreferences, PersistedChatSession

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover - optional runtime dependency
    redis = None

logger = get_logger(__name__)


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatSession(BaseModel):
    """Conversation session with context"""
    session_id: str
    user_id: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Extracted travel preferences
    extracted_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Conversation state
    current_intent: Optional[str] = None
    pending_actions: List[Dict[str, Any]] = Field(default_factory=list)
    is_ready_for_recommendations: bool = False
    planning_stage: str = "discover"
    planning_data: Dict[str, Any] = Field(default_factory=dict)
    recommendation_feedback: Dict[str, float] = Field(default_factory=dict)


class _ResponseCache:
    """
    Simple in-memory TTL cache for AI responses.
    Avoids redundant API calls when the same question is asked in a similar context.
    """

    def __init__(self, maxsize: int = 200, ttl_seconds: int = 3600):
        self._store: Dict[str, tuple] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._maxsize = maxsize

    def _key(self, session: "ChatSession", message: str) -> str:
        # Key = planning stage + last assistant reply (first 100 chars) + current message
        last_reply = ""
        for msg in reversed(session.messages[:-1]):  # exclude the just-added user message
            if msg.role == "assistant":
                last_reply = msg.content[:100]
                break
        raw = f"{session.planning_stage}|{last_reply}|{message.strip().lower()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, session: "ChatSession", message: str) -> Optional[str]:
        key = self._key(session, message)
        entry = self._store.get(key)
        if entry:
            value, ts = entry
            if datetime.utcnow() - ts < self._ttl:
                return value
            del self._store[key]
        return None

    def set(self, session: "ChatSession", message: str, response: str) -> None:
        if len(self._store) >= self._maxsize:
            oldest = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest]
        key = self._key(session, message)
        self._store[key] = (response, datetime.utcnow())


# Max number of sessions to keep in-process memory.
# Each ChatSession ~20 KB with full history → 1 000 sessions ≈ 20 MB.
# Older sessions are evicted (they are already persisted to DB/Redis).
_MAX_SESSIONS_IN_MEMORY = 1000

# Words that signal the end of a destination name in free-form user messages.
# Used by _infer_destination() to prevent regex over-capture.
_DESTINATION_STOP_WORDS = frozenset({
    "for", "with", "my", "our", "the", "a", "an", "from", "and", "or",
    "to", "in", "at", "on", "of", "under", "over", "this", "that",
    "your", "their", "its", "during", "after", "before", "about",
    "family", "friends", "solo", "couple", "people", "days", "weeks",
    "months", "trip", "vacation", "holiday", "travel", "under",
})


class ChatService:
    """
    Production-ready chat service with:
    - Conversation memory and context
    - Intent recognition
    - Preference extraction
    - Multi-turn conversations
    - Action execution (search, book, compare)
    - Streaming support
    """

    PIPELINE_STAGES = ["discover", "shortlist", "compare", "itinerary", "booking_checklist"]
    SESSION_TTL_DAYS = 7
    COUNTRY_CODE_BY_DESTINATION = {
        "paris": "FR",
        "france": "FR",
        "london": "GB",
        "united kingdom": "GB",
        "rome": "IT",
        "italy": "IT",
        "tokyo": "JP",
        "japan": "JP",
        "bangkok": "TH",
        "thailand": "TH",
        "bali": "ID",
        "indonesia": "ID",
        "dubai": "AE",
        "uae": "AE",
        "new york": "US",
        "united states": "US",
        "barcelona": "ES",
        "spain": "ES",
    }
    DESTINATION_COST_LEVEL = {
        "paris": "luxury",
        "london": "luxury",
        "tokyo": "high",
        "new york": "luxury",
        "dubai": "high",
        "rome": "moderate",
        "barcelona": "moderate",
        "bangkok": "budget",
        "bali": "budget",
    }

    def __init__(self):
        self.settings = get_settings()
        self.ai_provider = None
        # Ordered dict used as an LRU store: newest entries at the end.
        # Evicts the least-recently-used session when the cap is reached.
        self.sessions: OrderedDict[str, ChatSession] = OrderedDict()
        self.visa_service = VisaService()
        self.events_service = EventsService()
        self.flight_service = FlightService()
        self.redis_client = self._init_redis()
        self._response_cache = _ResponseCache()
        self._init_ai()

    def _put_session(self, session: ChatSession) -> None:
        """Insert/refresh a session in the LRU memory store, evicting the
        oldest entry if the cap is reached (already persisted to DB/Redis)."""
        sid = session.session_id
        if sid in self.sessions:
            self.sessions.move_to_end(sid)
        else:
            if len(self.sessions) >= _MAX_SESSIONS_IN_MEMORY:
                self.sessions.popitem(last=False)  # remove least-recently-used
        self.sessions[sid] = session
    
    def _init_ai(self):
        """Initialize AI provider"""
        try:
            self.ai_provider = AIFactory.create_from_settings()
            logger.info("Chat AI provider initialized", provider=type(self.ai_provider).__name__)
        except Exception as e:
            logger.warning("Failed to initialize AI provider", error=str(e))
            self.ai_provider = None

    def _init_redis(self):
        """Initialize Redis client for session persistence if configured."""
        if not redis or not self.settings.redis_url:
            return None
        try:
            client = redis.from_url(self.settings.redis_url, decode_responses=True)
            logger.info("Chat Redis persistence enabled")
            return client
        except Exception as e:
            logger.warning("Failed to initialize Redis for chat persistence", error=str(e))
            return None

    async def _save_session(self, session: ChatSession):
        """Persist session to Redis (if available) and DB fallback."""
        session.updated_at = datetime.utcnow()
        expires_at = datetime.utcnow() + timedelta(days=self.SESSION_TTL_DAYS)
        payload = session.model_dump_json()

        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"chat:session:{session.session_id}",
                    int(timedelta(days=self.SESSION_TTL_DAYS).total_seconds()),
                    payload,
                )
            except Exception as e:
                logger.warning("Redis session save failed; continuing with DB", error=str(e))

        db = SessionLocal()
        try:
            record = db.query(PersistedChatSession).filter(
                PersistedChatSession.session_id == session.session_id
            ).first()
            if not record:
                record = PersistedChatSession(session_id=session.session_id)
                db.add(record)
            record.user_id = session.user_id
            record.payload = payload
            record.planning_stage = session.planning_stage
            record.expires_at = expires_at
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning("DB session persistence failed", session_id=session.session_id, error=str(e))
        finally:
            db.close()

    async def _load_session(self, session_id: str) -> Optional[ChatSession]:
        """Load session from memory, Redis, or DB."""
        if session_id in self.sessions:
            return self.sessions[session_id]

        if self.redis_client:
            try:
                raw = await self.redis_client.get(f"chat:session:{session_id}")
                if raw:
                    session = ChatSession.model_validate_json(raw)
                    self._put_session(session)
                    return session
            except Exception as e:
                logger.warning("Redis session load failed; trying DB", session_id=session_id, error=str(e))

        db = SessionLocal()
        try:
            record = db.query(PersistedChatSession).filter(
                PersistedChatSession.session_id == session_id
            ).first()
            if not record:
                return None
            if record.expires_at and record.expires_at < datetime.utcnow():
                db.delete(record)
                db.commit()
                return None
            session = ChatSession.model_validate_json(record.payload)
            self._put_session(session)
            return session
        except Exception as e:
            logger.warning("DB session load failed", session_id=session_id, error=str(e))
            return None
        finally:
            db.close()

    async def _delete_session_persistence(self, session_id: str):
        """Delete persisted session state from Redis and DB."""
        if self.redis_client:
            try:
                await self.redis_client.delete(f"chat:session:{session_id}")
            except Exception as e:
                logger.warning("Redis session delete failed", session_id=session_id, error=str(e))

        db = SessionLocal()
        try:
            db.query(PersistedChatSession).filter(
                PersistedChatSession.session_id == session_id
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning("DB session delete failed", session_id=session_id, error=str(e))
        finally:
            db.close()

    def _hydrate_from_user_profile(self, session: ChatSession):
        """Prime extracted preferences from saved user profile for personalization."""
        if not session.user_id:
            return

        db = SessionLocal()
        try:
            prefs = db.query(UserPreferences).filter(UserPreferences.user_id == session.user_id).first()
            user = db.query(User).filter(User.id == session.user_id).first()
            if not prefs and not user:
                return

            profile = {}
            if user and user.passport_country:
                profile["passport_country"] = user.passport_country
            if prefs:
                profile.update({
                    "budget_daily": prefs.budget_daily,
                    "budget_total": prefs.budget_total,
                    "budget_level": prefs.travel_style or "moderate",
                    "interests": json.loads(prefs.interests) if prefs.interests else [],
                    "preferred_weather": prefs.preferred_weather,
                    "visa_preference": prefs.visa_preference,
                    "traveling_with": prefs.traveling_with,
                    "accessibility_needs": json.loads(prefs.accessibility_needs) if prefs.accessibility_needs else [],
                    "dietary_restrictions": json.loads(prefs.dietary_restrictions) if prefs.dietary_restrictions else [],
                })

            for key, value in profile.items():
                if value not in (None, "", [], {}):
                    session.extracted_preferences.setdefault(key, value)
        except Exception as e:
            logger.warning("Failed to hydrate chat session from profile", user_id=session.user_id, error=str(e))
        finally:
            db.close()
    
    def _get_system_prompt(self, session: ChatSession) -> str:
        """Generate dynamic system prompt based on context"""
        base_prompt = """You are TravelAI, an expert travel assistant with deep knowledge of destinations worldwide.

YOUR CAPABILITIES:
- Provide personalized destination recommendations
- Search flights, hotels, and attractions
- Create detailed day-by-day itineraries
- Check visa requirements and travel advisories
- Find events and activities
- Compare destinations
- Answer travel-related questions

COMMUNICATION STYLE:
- Be friendly, enthusiastic, and helpful
- Use emojis sparingly to make responses engaging
- Keep responses concise but informative
- Ask clarifying questions when needed
- Proactively suggest relevant information

RESPONSE FORMAT:
- Use markdown for formatting (bold, lists, etc.)
- Structure information clearly
- Include practical details (prices, durations, best times)
- When suggesting destinations, mention 2-3 key highlights

CURRENT CONTEXT:
- User preferences: {preferences}
- Conversation focus: {intent}
- Extracted info: {extracted}

Remember: Your goal is to help users plan their perfect trip while gathering enough information to provide personalized recommendations."""

        preferences = session.extracted_preferences.get('preferences_summary', 'Not yet specified')
        intent = session.current_intent or 'General travel inquiry'
        extracted = json.dumps(session.extracted_preferences, indent=2) if session.extracted_preferences else 'None yet'
        
        return base_prompt.format(
            preferences=preferences,
            intent=intent,
            extracted=extracted
        )
    
    async def send_message(
        self,
        session_id: str,
        user_message: str,
        user_id: Optional[str] = None
    ) -> ChatSession:
        """
        Process a user message and generate AI response.

        Optimised flow (minimises API calls):
        1. Check response cache → 0 API calls on hit.
        2. Collect grounding facts only when useful (destination known + relevant stage/keywords).
        3. ONE combined API call that extracts preferences AND generates the response
           (replaces the old 2-call approach of _update_context + _generate_response).
        """
        # Get or create session
        session = await self._load_session(session_id)
        if not session:
            session = ChatSession(session_id=session_id, user_id=user_id)
            self._put_session(session)
            self._hydrate_from_user_profile(session)
        elif user_id and not session.user_id:
            session.user_id = user_id
            self._hydrate_from_user_profile(session)

        # Add user message
        session.messages.append(ChatMessage(
            role='user',
            content=user_message,
            timestamp=datetime.utcnow()
        ))

        # --- Optimised AI path ---
        if self.ai_provider and getattr(self.ai_provider, 'client', None):
            # 1. Cache check (0 API calls)
            cached = self._response_cache.get(session, user_message)
            if cached:
                logger.info("Response cache hit", session_id=session_id)
                ai_response = cached
                extracted: Dict[str, Any] = {}
            else:
                # 2. Grounding (skipped when not useful)
                grounding = (
                    await self._collect_grounded_facts(session, user_message)
                    if self._should_run_grounding(session, user_message)
                    else {"facts": {}, "citations": []}
                )
                # 3. Single combined API call
                ai_response, extracted = await self._combined_api_call(session, grounding)
                self._response_cache.set(session, user_message, ai_response)

            # Update session with extracted preferences
            if extracted:
                session.extracted_preferences.update(
                    {k: v for k, v in extracted.items() if v is not None}
                )
                if extracted.get('intent'):
                    session.current_intent = extracted['intent']
        else:
            ai_response = self._fallback_response(session)

        # Add assistant response
        session.messages.append(ChatMessage(
            role='assistant',
            content=ai_response,
            timestamp=datetime.utcnow()
        ))

        session.updated_at = datetime.utcnow()
        session.is_ready_for_recommendations = self._check_ready_for_recommendations(session)
        session.planning_stage = self._infer_planning_stage(session, user_message)
        await self._save_session(session)

        return session
    
    async def send_message_streaming(
        self,
        session_id: str,
        user_message: str,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response token by token (ChatGPT-style).

        Flow:
        1. Stream response tokens immediately (low latency for the user).
        2. After the full response is assembled, run preference extraction
           (_update_context) so extracted_preferences + planning_stage are
           populated before the SSE 'done' event is emitted.
        """
        # Get or create session
        session = await self._load_session(session_id)
        if not session:
            session = ChatSession(session_id=session_id, user_id=user_id)
            self._put_session(session)
            self._hydrate_from_user_profile(session)
        elif user_id and not session.user_id:
            session.user_id = user_id
            self._hydrate_from_user_profile(session)

        # Add user message
        session.messages.append(ChatMessage(
            role='user',
            content=user_message,
            timestamp=datetime.utcnow()
        ))

        # Collect grounding only when useful (skip extraction to save API call)
        grounding = (
            await self._collect_grounded_facts(session, user_message)
            if self._should_run_grounding(session, user_message)
            else {"facts": {}, "citations": []}
        )

        # Generate streaming response (pass pre-computed grounding)
        full_response = ""
        async for token in self._generate_response_stream(session, grounding):
            full_response += token
            yield token

        # Save complete response
        session.messages.append(ChatMessage(
            role='assistant',
            content=full_response,
            timestamp=datetime.utcnow()
        ))

        # Extract preferences from the completed conversation so that
        # extracted_preferences is populated in the SSE 'done' event.
        # This runs after streaming finishes, so it doesn't add latency
        # to token delivery — only to the final metadata event.
        await self._update_context(session, user_message)

        session.updated_at = datetime.utcnow()
        session.is_ready_for_recommendations = self._check_ready_for_recommendations(session)
        session.planning_stage = self._infer_planning_stage(session, user_message)
        await self._save_session(session)

    async def _update_context(self, session: ChatSession, user_message: str):
        """Extract preferences and detect intent from message"""
        if not self.ai_provider:
            return
        
        try:
            # Use AI to extract structured information
            extraction_prompt = f"""Analyze this travel-related message and extract structured information.

Message: "{user_message}"

Extract the following (use null if not mentioned):
- origin: departure city/country
- destinations: mentioned destinations (array)
- travel_dates: {{start: "YYYY-MM", end: "YYYY-MM"}}
- duration: number of days
- budget_level: "budget" | "moderate" | "luxury" | "ultra-luxury"
- interests: activities they enjoy (array)
- traveling_with: "solo" | "couple" | "family" | "friends"
- kids_ages: ages if family with children (array)
- accommodation_type: "hotel" | "hostel" | "airbnb" | "resort"
- activity_pace: "relaxed" | "moderate" | "active"
- special_occasion: honeymoon, anniversary, birthday, etc.
- dietary_restrictions: (array)
- accessibility_needs: (array)
- visa_preference: "visa_free" | "easy_visa" | "any"
- weather_preference: "warm" | "cold" | "mild" | "tropical"
- nightlife_priority: "low" | "medium" | "high"
- car_hire: boolean
- flight_class: "economy" | "premium" | "business" | "first"

Also detect:
- intent: main purpose (recommendation, booking, comparison, information, itinerary)
- confidence: 0-1 how confident in extraction

Return as JSON only."""

            client = getattr(self.ai_provider, 'client', None)
            if client:
                response = await client.chat.completions.create(
                    model=getattr(self.ai_provider, 'model', 'gpt-3.5-turbo'),
                    messages=[
                        {"role": "system", "content": "You are a travel preference extraction assistant. Return only valid JSON."},
                        {"role": "user", "content": extraction_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                
                extracted = json.loads(response.choices[0].message.content.strip())
                
                # Update session context
                session.extracted_preferences.update(extracted)
                session.current_intent = extracted.get('intent')
                
                logger.info("Extracted preferences", extracted=extracted)
                
        except Exception as e:
            logger.warning("Failed to extract preferences", error=str(e))
    
    async def _generate_response_stream(
        self,
        session: ChatSession,
        grounding: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using pre-computed grounding (avoids duplicate fetch)."""
        if not self.ai_provider or not getattr(self.ai_provider, 'client', None):
            yield self._fallback_response(session)
            return

        try:
            user_message = session.messages[-1].content if session.messages else ""
            # Use passed-in grounding; compute lazily only if not provided
            if grounding is None:
                grounding = (
                    await self._collect_grounded_facts(session, user_message)
                    if self._should_run_grounding(session, user_message)
                    else {"facts": {}, "citations": []}
                )
            messages = [
                {"role": "system", "content": self._get_system_prompt(session)}
            ]
            if grounding["facts"]:
                messages.append({
                    "role": "system",
                    "content": (
                        "Grounded travel data from tools (prefer this over assumptions):\n"
                        f"{json.dumps(grounding['facts'], indent=2)}"
                    )
                })
            
            recent_messages = session.messages[-10:]
            for msg in recent_messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            client = getattr(self.ai_provider, 'client', None)
            stream = await client.chat.completions.create(
                model=getattr(self.ai_provider, 'model', 'gpt-3.5-turbo'),
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("Streaming response failed", error=str(e))
            yield self._fallback_response(session)
    
    def _fallback_response(self, session: ChatSession) -> str:
        """Fallback response when AI is unavailable"""
        last_message = session.messages[-1].content.lower() if session.messages else ""
        
        if "weather" in last_message:
            return "I can help with weather information! Which destination are you interested in? 🌤️"
        elif "flight" in last_message or "fly" in last_message:
            return "I can search flights for you! Where are you departing from and where to? ✈️"
        elif "hotel" in last_message or "accommodation" in last_message:
            return "I can help find accommodations! What's your preferred destination and budget? 🏨"
        else:
            return "I'm your AI travel assistant! Tell me about your dream trip - where, when, who's coming, and what you love doing! 🌍"
    
    def _check_ready_for_recommendations(self, session: ChatSession) -> bool:
        """Check if we have enough info to provide recommendations"""
        prefs = session.extracted_preferences
        
        required_fields = ['destinations', 'origin', 'travel_dates', 'budget_level']
        filled = sum(1 for field in required_fields if prefs.get(field))
        
        return filled >= 2  # Need at least 2 key fields
    
    def _infer_destination(self, session: ChatSession, message: str) -> Optional[str]:
        destinations = session.extracted_preferences.get("destinations") or []
        if isinstance(destinations, list) and destinations:
            return str(destinations[0]).strip()

        match = re.search(r"(?:to|in|visit)\s+([A-Za-z\s]{2,40})", message, re.IGNORECASE)
        if match:
            # Trim at the first stop-word so "Europe with my family" → "Europe"
            words = match.group(1).strip().split()
            dest_words: List[str] = []
            for word in words:
                if word.lower() in _DESTINATION_STOP_WORDS:
                    break
                dest_words.append(word)
            if dest_words:
                return " ".join(dest_words[:3]).strip()  # max 3-word destination name
        return None

    def _should_run_grounding(self, session: ChatSession, message: str) -> bool:
        """
        Only fetch external tool data (weather/visa/events/flights) when it would
        actually improve the response. Skips grounding during early discovery or
        when no destination is known — saving API calls and latency.
        """
        # Need a destination to ground anything useful
        if not self._infer_destination(session, message):
            return False
        # Past discovery phase → always worth grounding
        if session.planning_stage != "discover":
            return True
        # In discovery, only ground when user explicitly asks for real-time data
        grounding_triggers = {
            "weather", "flight", "fly", "hotel", "accommodation",
            "event", "festival", "visa", "cost", "price", "when",
            "best time", "cheap", "budget", "how much",
        }
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in grounding_triggers)

    def _infer_planning_stage(self, session: ChatSession, message: str) -> str:
        lower = message.lower()
        prefs = session.extracted_preferences
        has_destination = bool(prefs.get("destinations"))
        has_dates = bool(prefs.get("travel_dates"))
        has_budget = bool(prefs.get("budget_level") or prefs.get("budget_daily") or prefs.get("budget_total"))

        if any(k in lower for k in ["book", "reserve", "checklist", "packing"]):
            return "booking_checklist"
        if any(k in lower for k in ["itinerary", "day plan", "schedule"]):
            return "itinerary"
        if any(k in lower for k in ["compare", "vs", "versus"]):
            return "compare"
        if has_destination and has_dates and has_budget:
            return "shortlist"
        return "discover"

    async def _combined_api_call(
        self,
        session: ChatSession,
        grounding: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Single API call that BOTH extracts travel preferences AND generates a response.
        Replaces the previous 2-call approach (_update_context + _generate_response),
        cutting API usage in half for every non-streaming message.

        Returns: (response_text, extracted_preferences_dict)
        """
        client = getattr(self.ai_provider, 'client', None)
        if not client:
            return self._fallback_response(session), {}

        try:
            system = (
                self._get_system_prompt(session)
                + """

OUTPUT FORMAT (required):
Reply with a single JSON object — no markdown fences, no extra text:
{"extracted":{"origin":null,"destinations":null,"travel_dates":null,"duration":null,"budget_level":null,"interests":null,"traveling_with":null,"intent":null},"response":"Your reply here"}

Rules:
- In "extracted": only fill fields you can confidently identify from the user's message; leave others null.
- In "response": write a natural, friendly travel assistant reply, max 150 words.
- Output ONLY the JSON object — nothing before or after it."""
            )

            messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]

            if grounding.get("facts"):
                messages.append({
                    "role": "system",
                    "content": (
                        "Live travel data (use when relevant):\n"
                        + json.dumps(grounding["facts"], indent=2)
                    ),
                })

            for msg in session.messages[-10:]:
                messages.append({"role": msg.role, "content": msg.content})

            resp = await client.chat.completions.create(
                model=getattr(self.ai_provider, 'model', 'gpt-3.5-turbo'),
                messages=messages,
                temperature=0.7,
                max_tokens=700,
                # Note: no response_format here — we parse JSON ourselves so this
                # works even with providers that don't support the parameter.
            )

            raw = resp.choices[0].message.content.strip()

            # --- Robust JSON parsing ---
            # Strip markdown code fences the model may wrap around JSON
            clean = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.IGNORECASE)
            clean = re.sub(r'\s*```$', '', clean).strip()

            extracted: Dict[str, Any] = {}
            ai_response = raw  # default: return raw text if JSON parsing fails

            try:
                data = json.loads(clean)
                if isinstance(data, dict):
                    reply = data.get("response", "").strip()
                    if reply:
                        ai_response = reply
                    extracted = {
                        k: v for k, v in data.get("extracted", {}).items()
                        if v is not None
                    }
            except (json.JSONDecodeError, ValueError):
                # The model didn't return valid JSON — use the raw text as the reply.
                # This is fine; preference extraction just won't happen this turn.
                logger.warning("Combined call: could not parse JSON, using raw response")
                ai_response = raw

            if grounding.get("citations"):
                citations = " | ".join(
                    f"{c['source']} ({c['last_updated']})" for c in grounding["citations"]
                )
                ai_response = f"{ai_response}\n\nSources: {citations}"

            return ai_response or self._fallback_response(session), extracted

        except Exception as e:
            logger.error("Combined API call failed", error=str(e))
            return self._fallback_response(session), {}

    async def _collect_grounded_facts(self, session: ChatSession, user_message: str) -> Dict[str, Any]:
        """Collect tool data and citations used to ground assistant responses."""
        facts: Dict[str, Any] = {}
        citations: List[Dict[str, str]] = []
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

        destination = self._infer_destination(session, user_message)
        if not destination:
            return {"facts": facts, "citations": citations}

        travel_dates = session.extracted_preferences.get("travel_dates") or {}
        start_date = travel_dates.get("start") if isinstance(travel_dates, dict) else None
        if start_date and len(start_date) == 7:
            start_date = f"{start_date}-01"
        elif not start_date:
            start_date = date.today().isoformat()

        weather = travelgenie_service.get_weather(destination, start_date)
        if weather and not weather.get("error"):
            facts["weather"] = weather
            citations.append({"source": "weather_agent", "last_updated": now})

        country_code = self.COUNTRY_CODE_BY_DESTINATION.get(destination.lower().strip())
        passport_country = (
            session.extracted_preferences.get("passport_country")
            or "US"
        )
        if country_code:
            try:
                visa = await self.visa_service.get_visa_requirements(passport_country, country_code)
                facts["visa"] = visa
                citations.append({"source": "visa_service", "last_updated": now})
            except Exception as e:
                logger.warning("Grounding visa fetch failed", destination=destination, error=str(e))

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = start_date_obj + timedelta(days=7)
            events = await self.events_service.get_events(destination, start_date_obj, end_date_obj, country_code or "US")
            facts["events"] = [e.model_dump(mode='json') for e in events[:5]]
            citations.append({"source": "events_service", "last_updated": now})
        except Exception as e:
            logger.warning("Grounding events fetch failed", destination=destination, error=str(e))

        origin = session.extracted_preferences.get("origin")
        if origin:
            try:
                origin_code = await self.flight_service.get_airport_code(origin)
                dest_code = await self.flight_service.get_airport_code(destination)
                if origin_code and dest_code:
                    flights = await self.flight_service.search_flights(
                        origin=origin_code,
                        destination=dest_code,
                        departure_date=datetime.strptime(start_date, "%Y-%m-%d").date(),
                    )
                    facts["flights"] = [f.model_dump(mode='json') for f in flights[:3]]
                    citations.append({"source": "flight_service", "last_updated": now})
            except Exception as e:
                logger.warning("Grounding flights fetch failed", origin=origin, destination=destination, error=str(e))

        return {"facts": facts, "citations": citations}

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get existing session from memory or DB fallback."""
        session = self.sessions.get(session_id)
        if session:
            return session

        db = SessionLocal()
        try:
            record = db.query(PersistedChatSession).filter(
                PersistedChatSession.session_id == session_id
            ).first()
            if not record:
                return None
            if record.expires_at and record.expires_at < datetime.utcnow():
                db.delete(record)
                db.commit()
                return None
            session = ChatSession.model_validate_json(record.payload)
            self._put_session(session)
            return session
        except Exception as e:
            logger.warning("Session fallback load failed", session_id=session_id, error=str(e))
            return None
        finally:
            db.close()
    
    async def execute_action(
        self,
        session_id: str,
        action_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute travel-related actions (search, compare, book)
        """
        # Use full load path (memory → Redis → DB) to avoid "not found" after restart
        session = await self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        try:
            if action_type == "search_flights":
                result = travelgenie_service.get_flights(**params)
            elif action_type == "search_attractions":
                result = travelgenie_service.get_attractions(params.get("location", ""))
            elif action_type == "search_events":
                result = travelgenie_service.get_events(
                    params.get("location", ""),
                    params.get("start_date"),
                    params.get("end_date")
                )
            elif action_type == "get_weather":
                result = travelgenie_service.get_weather(
                    params.get("location", ""),
                    params.get("date", "")
                )
            elif action_type == "rank_destinations":
                result = await self.rank_destinations(
                    session_id=session_id,
                    candidates=params.get("candidates", []),
                    constraints=params.get("constraints", {}),
                )
            elif action_type == "submit_feedback":
                result = await self.submit_recommendation_feedback(
                    session_id=session_id,
                    destination=params.get("destination", ""),
                    feedback=float(params.get("feedback", 0)),
                )
            else:
                return {"error": f"Unknown action type: {action_type}"}
            
            # Add action result to session context.
            # Use .isoformat() so the dict serialises cleanly via model_dump_json().
            session.pending_actions.append({
                "type": action_type,
                "params": params,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            })
            await self._save_session(session)
            return result
            
        except Exception as e:
            logger.error("Action execution failed", action=action_type, error=str(e))
            return {"error": str(e)}

    async def advance_pipeline_stage(self, session_id: str, target_stage: Optional[str] = None) -> Dict[str, Any]:
        session = await self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        if target_stage:
            if target_stage not in self.PIPELINE_STAGES:
                return {"error": f"Invalid stage '{target_stage}'"}
            session.planning_stage = target_stage
        else:
            idx = self.PIPELINE_STAGES.index(session.planning_stage) if session.planning_stage in self.PIPELINE_STAGES else 0
            session.planning_stage = self.PIPELINE_STAGES[min(idx + 1, len(self.PIPELINE_STAGES) - 1)]

        await self._save_session(session)
        return {"session_id": session_id, "planning_stage": session.planning_stage}

    async def update_planning_data(self, session_id: str, planning_data: Dict[str, Any]) -> Dict[str, Any]:
        session = await self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}
        session.planning_data.update(planning_data)
        await self._save_session(session)
        return {"session_id": session_id, "planning_data": session.planning_data}

    async def rank_destinations(
        self,
        session_id: str,
        candidates: List[str],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        session = await self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}

        constraints = constraints or {}
        feedback = session.recommendation_feedback or {}
        budget_level = constraints.get("budget_level") or session.extracted_preferences.get("budget_level")
        visa_pref = constraints.get("visa_preference") or session.extracted_preferences.get("visa_preference")
        weather_pref = constraints.get("weather_preference") or session.extracted_preferences.get("weather_preference")

        ranked = []
        for destination in candidates:
            key = destination.lower().strip()
            score = 50.0
            reasons: List[str] = []

            cost_level = self.DESTINATION_COST_LEVEL.get(key, "moderate")
            if budget_level:
                if budget_level in ["budget", "low"] and cost_level == "budget":
                    score += 20
                    reasons.append("Strong budget match")
                elif budget_level in ["luxury", "ultra-luxury"] and cost_level in ["high", "luxury"]:
                    score += 15
                    reasons.append("Fits premium budget preference")
                elif budget_level == "moderate" and cost_level == "moderate":
                    score += 10
                    reasons.append("Balanced cost fit")
                elif budget_level in ["budget", "low"] and cost_level in ["high", "luxury"]:
                    score -= 20
                    reasons.append("Likely above budget")

            if visa_pref == "visa_free":
                code = self.COUNTRY_CODE_BY_DESTINATION.get(key)
                if code:
                    visa = await self.visa_service.get_visa_requirements(
                        session.extracted_preferences.get("passport_country", "US"),
                        code
                    )
                    requirement = str(visa.get("requirement", "")).lower()
                    if "visa_free" in requirement:
                        score += 15
                        reasons.append("Visa-free travel")
                    else:
                        score -= 10
                        reasons.append("May require visa")

            if weather_pref and weather_pref in ["warm", "hot", "tropical"]:
                if key in ["bangkok", "bali", "dubai"]:
                    score += 8
                    reasons.append("Aligns with warm-weather preference")

            if destination in feedback:
                delta = feedback[destination]
                score += delta * 8
                reasons.append("Adjusted using your previous feedback")

            ranked.append({
                "destination": destination,
                "score": round(max(0, min(100, score)), 1),
                "reasons": reasons[:3],
                "constraints_applied": {
                    "budget_level": budget_level,
                    "visa_preference": visa_pref,
                    "weather_preference": weather_pref,
                }
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        session.planning_data["ranked_destinations"] = ranked
        await self._save_session(session)
        return {"ranked_destinations": ranked}

    async def submit_recommendation_feedback(
        self,
        session_id: str,
        destination: str,
        feedback: float
    ) -> Dict[str, Any]:
        session = await self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}
        if not destination:
            return {"error": "Destination is required"}

        current = session.recommendation_feedback.get(destination, 0.0)
        clamped = max(-2.0, min(2.0, current + max(-1.0, min(1.0, feedback))))
        session.recommendation_feedback[destination] = clamped
        await self._save_session(session)
        return {
            "destination": destination,
            "feedback_score": session.recommendation_feedback[destination]
        }
    
    def clear_session(self, session_id: str):
        """Clear conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._delete_session_persistence(session_id))
        except RuntimeError:
            pass


# Global chat service instance
chat_service = ChatService()
