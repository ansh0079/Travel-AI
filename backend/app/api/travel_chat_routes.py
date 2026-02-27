from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Any
import json
from datetime import date

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class TravelChatRequest(BaseModel):
    messages: List[ChatMessage]


class TravelChatResponse(BaseModel):
    reply: str
    extracted: dict
    ready: bool
    suggestions: List[str] = []


SYSTEM_PROMPT = """You are a warm, friendly travel planning assistant in a chat widget. Your job is to understand what the user wants through natural conversation and extract structured travel preferences.

Today's date: {today}

IMPORTANT: You MUST respond with ONLY valid JSON — no markdown, no code fences, no extra text. Use this exact structure:
{{
  "reply": "<your conversational response — 1-2 sentences + one follow-up question if not ready>",
  "extracted": {{
    "origin": "<departure city/airport, null if not mentioned>",
    "travel_start": "<YYYY-MM-DD, null if unknown>",
    "travel_end": "<YYYY-MM-DD, null if unknown>",
    "num_travelers": <total headcount including kids, null if unknown>,
    "has_kids": <true/false/null>,
    "kids_ages": [<list of integer ages, empty if no kids>],
    "traveling_with": "<solo|couple|family|friends|null>",
    "interests": [<subset of: nature, culture, adventure, relaxation, food, nightlife, shopping, history, art, beaches, mountains, wildlife>],
    "budget_level": "<low|moderate|high|luxury|null>",
    "budget_daily": <estimated daily budget per person in USD, null if unknown>,
    "travel_style": "<budget|moderate|comfort|luxury|null>",
    "preferred_weather": "<hot|warm|mild|cold|null>",
    "passport_country": "<2-letter ISO country code like US, GB, CA, AU, null if unknown>",
    "visa_preference": "<visa_free|evisa_ok|visa_ok|null>"
  }},
  "ready": <true ONLY when origin, travel_start, travel_end, and num_travelers are all known>,
  "suggestions": ["<2-3 short clickable reply options for common answers to your question>"]
}}

Extraction rules:
- Easter 2026 = April 2–13. "Easter holidays April 5-12" → travel_start: 2026-04-05, travel_end: 2026-04-12
- "5 days" → figure out end date from start date if start is known
- "2 adults and 2 kids aged 7 and 10" → num_travelers: 4, has_kids: true, kids_ages: [7, 10], traveling_with: family
- "just the two of us" → num_travelers: 2, traveling_with: couple
- "warm destination" → preferred_weather: warm
- "beach holiday" → interests includes beaches
- "family friendly" or kids → add nature, beaches to interests if no others mentioned
- "budget" / "cheap" → budget_level: low, travel_style: budget, budget_daily: 75
- "luxury" / "splurge" → budget_level: luxury, travel_style: luxury, budget_daily: 600
- UK origin → passport_country: GB
- Australian → passport_country: AU
- US / American → passport_country: US

Conversation rules:
- If user gives a lot of info at once (like the example), extract everything and only ask for the single most important missing piece
- Most important missing fields in order: origin → dates → num_travelers → budget
- If passport_country is unclear, default to US silently (don't ask about it unless user brings it up)
- When ready is true, reply should confirm all details and say you're searching now — no question needed
- Keep replies warm and human. Never say "I have extracted" or sound robotic.
- suggestions should be plausible short answers to whatever question you asked"""


async def call_llm(messages: list) -> dict:
    """Call the configured LLM and parse JSON response."""
    from app.services.ai_recommendation_service import AIRecommendationService
    svc = AIRecommendationService()
    client = svc._get_client()

    if not client:
        print("[TravelChat] No LLM client configured — using context-aware fallback")
        return _fallback_parse(messages)

    raw = ""
    try:
        response = await client.chat.completions.create(
            model=svc.model,
            messages=messages,
            max_tokens=600,
            temperature=0.4,
            # No response_format — not universally supported; rely on prompt instead
        )
        raw = response.choices[0].message.content.strip()
        print(f"[TravelChat] LLM raw: {raw[:300]}")

        # Strip markdown fences if the model wrapped the JSON anyway
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[TravelChat] JSON parse error: {e} | raw={raw[:300]}")
        return _fallback_parse(messages)
    except Exception as e:
        print(f"[TravelChat] LLM call failed: {e}")
        return _fallback_parse(messages)


def _fallback_parse(messages: list) -> dict:
    """Context-aware fallback parser used when no LLM is available or LLM fails."""
    user_msgs = [m for m in messages if m["role"] == "user"]
    asst_msgs = [m for m in messages if m["role"] == "assistant"]

    combined_users = " ".join(m["content"] for m in user_msgs).lower()
    last_user = user_msgs[-1]["content"].strip() if user_msgs else ""
    last_asst = asst_msgs[-1]["content"].lower() if asst_msgs else ""

    extracted: dict = {
        "origin": None, "travel_start": None, "travel_end": None,
        "num_travelers": None, "has_kids": None, "kids_ages": [],
        "traveling_with": None, "interests": [], "budget_level": None,
        "budget_daily": None, "travel_style": None, "preferred_weather": None,
        "passport_country": None, "visa_preference": None,
    }

    # --- Context-aware: use user's last reply as the answer to what the bot asked ---
    origin_triggers = ("flying from", "departing from", "traveling from", "travelling from",
                       "where are you", "where will you", "city are you")
    date_triggers = ("when are you", "what date", "travel date", "which date", "how long")
    traveler_triggers = ("how many people", "how many traveler", "how many traveller",
                         "who's coming", "who is coming", "group size")

    if any(t in last_asst for t in origin_triggers):
        extracted["origin"] = last_user  # direct answer to "where from?"
    elif any(t in last_asst for t in date_triggers):
        pass  # date parsing without LLM is unreliable; leave null
    elif any(t in last_asst for t in traveler_triggers):
        import re
        nums = re.findall(r'\d+', last_user)
        if nums:
            extracted["num_travelers"] = int(nums[0])

    # --- Scan all user text for interests / vibe ---
    if "beach" in combined_users or "seaside" in combined_users:
        extracted["interests"].append("beaches")
    if "mountain" in combined_users or "hiking" in combined_users:
        extracted["interests"].append("mountains")
    if "culture" in combined_users or "museum" in combined_users or "history" in combined_users:
        extracted["interests"].append("culture")
    if "food" in combined_users or "cuisine" in combined_users:
        extracted["interests"].append("food")
    if "warm" in combined_users or "sunny" in combined_users:
        extracted["preferred_weather"] = "warm"
    if "hot" in combined_users:
        extracted["preferred_weather"] = "hot"
    if "kid" in combined_users or "child" in combined_users or "family" in combined_users:
        extracted["has_kids"] = True
        extracted["traveling_with"] = "family"
        if not extracted["interests"]:
            extracted["interests"] = ["beaches", "nature"]
    if "solo" in combined_users or "just me" in combined_users or "myself" in combined_users:
        if not extracted["num_travelers"]:
            extracted["num_travelers"] = 1
        extracted["traveling_with"] = "solo"
    if "couple" in combined_users or "two of us" in combined_users or "partner" in combined_users:
        if not extracted["num_travelers"]:
            extracted["num_travelers"] = 2
        extracted["traveling_with"] = "couple"
    if "budget" in combined_users or "cheap" in combined_users or "affordable" in combined_users:
        extracted["budget_level"] = "low"
        extracted["budget_daily"] = 75
    if "luxury" in combined_users or "splurge" in combined_users:
        extracted["budget_level"] = "luxury"
        extracted["budget_daily"] = 600

    # --- Determine what's still missing ---
    QUESTIONS = {
        "origin": ("Where will you be flying from?",
                   ["London, UK", "New York, USA", "Sydney, AU"]),
        "dates": ("When are you planning to travel? Any specific dates?",
                  ["Easter holidays", "Next month", "This summer"]),
        "travelers": ("How many people will be travelling?",
                      ["Just me", "2 adults", "Family of 4"]),
    }

    for key, (question, suggestions) in QUESTIONS.items():
        need = (
            (key == "origin" and not extracted["origin"]) or
            (key == "dates" and not extracted["travel_start"]) or
            (key == "travelers" and not extracted["num_travelers"])
        )
        if need:
            return {"reply": question, "extracted": extracted, "ready": False, "suggestions": suggestions}

    return {
        "reply": "Great, I have everything I need — searching for your perfect destinations now!",
        "extracted": extracted,
        "ready": True,
        "suggestions": [],
    }


@router.post("/travel", response_model=TravelChatResponse)
async def travel_chat(request: TravelChatRequest):
    """
    LLM-powered travel preference extraction through natural conversation.
    Send the full message history; receive a reply, extracted fields, and ready flag.
    """
    today = date.today().isoformat()
    system = SYSTEM_PROMPT.format(today=today)

    llm_messages = [{"role": "system", "content": system}]
    for m in request.messages:
        llm_messages.append({"role": m.role, "content": m.content})

    result = await call_llm(llm_messages)

    # Ensure required keys exist with safe defaults
    return TravelChatResponse(
        reply=result.get("reply", "Tell me more about your trip!"),
        extracted=result.get("extracted", {}),
        ready=result.get("ready", False),
        suggestions=result.get("suggestions", []),
    )
