from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
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


# ─────────────────────────────────────────────────────────────────────────────
# Question Bank — 20 questions across 3 tiers
# Tier 1: Required before ready=true
# Tier 2: Important — get at least budget + interests before ready=true
# Tier 3: Enriching — ask after tier 1+2 are covered
# ─────────────────────────────────────────────────────────────────────────────

QUESTION_BANK = [
    # ── Tier 1: Required ─────────────────────────────────────────────────────
    {
        "id": "origin", "field": "origin", "tier": 1,
        "question": "Where will you be flying from?",
        "suggestions": ["London, UK", "New York, USA", "Sydney, AU", "Dubai, UAE"],
        "condition": None,
    },
    {
        "id": "dates", "field": "travel_start", "tier": 1,
        "question": "When are you planning to travel? Any specific dates?",
        "suggestions": ["Easter holidays", "Next month", "This summer", "Christmas period"],
        "condition": None,
    },
    {
        "id": "num_travelers", "field": "num_travelers", "tier": 1,
        "question": "How many people will be travelling in total?",
        "suggestions": ["Just me", "2 adults", "Family of 4", "Group of friends"],
        "condition": None,
    },

    # ── Tier 2: Important ────────────────────────────────────────────────────
    {
        "id": "budget", "field": "budget_level", "tier": 2,
        "question": "What's your rough budget for this trip?",
        "suggestions": ["Budget / backpacker (<$75/day)", "Mid-range ($75-200/day)", "Comfortable ($200-400/day)", "Luxury ($400+/day)"],
        "condition": None,
    },
    {
        "id": "kids", "field": "has_kids", "tier": 2,
        "question": "Will any children be joining you on this trip?",
        "suggestions": ["No children", "Yes - toddlers (under 5)", "Yes - school age (5-12)", "Yes - teenagers"],
        "condition": "num_travelers_gt_1",
    },
    {
        "id": "kids_ages", "field": "kids_ages", "tier": 2,
        "question": "How old are each of the children? List all ages so we can tailor activities for everyone.",
        "suggestions": ["Ages 2 and 7", "3, 9 and 14", "One child, age 8", "Teens — 15 and 17"],
        "condition": "has_kids",
    },
    {
        "id": "interests", "field": "interests", "tier": 2,
        "question": "What kind of experiences are you most excited about?",
        "suggestions": ["Beaches & relaxation", "Culture & history", "Adventure & nature", "Food & nightlife"],
        "condition": None,
    },
    {
        "id": "pace", "field": "activity_pace", "tier": 2,
        "question": "Relaxed pace or action-packed? How do you like to travel?",
        "suggestions": ["Slow & relaxed - plenty of downtime", "Balanced mix", "Jam-packed - see everything"],
        "condition": None,
    },
    {
        "id": "weather", "field": "preferred_weather", "tier": 2,
        "question": "Any preference on weather or climate?",
        "suggestions": ["Hot & sunny", "Warm (around 25C)", "Mild & pleasant", "Cool / crisp"],
        "condition": None,
    },

    # ── Tier 3: Enriching ────────────────────────────────────────────────────
    {
        "id": "accommodation", "field": "accommodation_type", "tier": 3,
        "question": "What type of accommodation suits you best?",
        "suggestions": ["Hotel (3-4 star)", "Luxury resort / 5-star", "Airbnb / apartment", "Hostel / budget"],
        "condition": None,
    },
    {
        "id": "dietary", "field": "dietary_restrictions", "tier": 3,
        "question": "Any dietary requirements to keep in mind for restaurant recommendations?",
        "suggestions": ["No restrictions", "Vegetarian", "Vegan", "Halal / Kosher"],
        "condition": None,
    },
    {
        "id": "adventure", "field": "adventure_level", "tier": 3,
        "question": "How adventurous are you feeling? Any activities on your wish list?",
        "suggestions": ["Scuba / snorkelling", "Hiking / trekking", "City tours & museums", "Spa & wellness"],
        "condition": None,
    },
    {
        "id": "nightlife", "field": "nightlife_priority", "tier": 3,
        "question": "How important is nightlife and evening entertainment?",
        "suggestions": ["Very important - we love going out", "Nice to have", "Not really our thing"],
        "condition": "not_family",
    },
    {
        "id": "car_hire", "field": "car_hire", "tier": 3,
        "question": "Planning to hire a car, or stick to public transport and taxis?",
        "suggestions": ["Yes, we'd like a car", "No - public transport is fine", "Car for day trips only"],
        "condition": None,
    },
    {
        "id": "occasion", "field": "special_occasion", "tier": 3,
        "question": "Is this for a special occasion? We can suggest romantic extras or celebration options!",
        "suggestions": ["Honeymoon / anniversary", "Birthday trip", "Just a holiday", "Family milestone"],
        "condition": None,
    },
    {
        "id": "access", "field": "accessibility_needs", "tier": 3,
        "question": "Does anyone in your group have accessibility or mobility needs we should factor in?",
        "suggestions": ["No special requirements", "Wheelchair accessible", "Limited walking", "Other needs"],
        "condition": None,
    },
    {
        "id": "flight_class", "field": "flight_class", "tier": 3,
        "question": "What cabin class are you looking at for flights?",
        "suggestions": ["Economy", "Premium Economy", "Business class", "First class"],
        "condition": "high_budget",
    },
    {
        "id": "visa", "field": "visa_preference", "tier": 3,
        "question": "Any preference around visas? Some great destinations require advance applications.",
        "suggestions": ["Visa-free only", "E-visa is fine", "Any visa - worth it for the right place"],
        "condition": None,
    },
    {
        "id": "past_trips", "field": "past_destinations", "tier": 3,
        "question": "Any destinations you've already visited and want to avoid, or a dream place you've never been?",
        "suggestions": ["Already visited Southeast Asia", "Never been to Japan", "Avoid long-haul flights", "Open to anything"],
        "condition": None,
    },
    {
        "id": "requests", "field": "special_requests", "tier": 3,
        "question": "Anything else specific you'd love - or definitely want to avoid - on this trip?",
        "suggestions": ["No big city crowds", "Must have a pool", "Love local markets", "Kid-friendly beaches only"],
        "condition": None,
    },
]

# Human-readable condition labels for system prompt
_CONDITION_LABELS = {
    "num_travelers_gt_1": "only for groups of 2+ travellers",
    "has_kids": "only if travelling with children",
    "not_family": "skip if travelling with kids",
    "high_budget": "only for high or luxury budget",
}


def _check_condition(condition: Optional[str], extracted: dict) -> bool:
    """Evaluate a question bank condition string against current extracted state."""
    if condition is None:
        return True
    if condition == "num_travelers_gt_1":
        return (extracted.get("num_travelers") or 1) > 1
    if condition == "has_kids":
        return extracted.get("has_kids") is True
    if condition == "not_family":
        return extracted.get("traveling_with") != "family" and not extracted.get("has_kids")
    if condition == "high_budget":
        return extracted.get("budget_level") in ("high", "luxury")
    return True


def _build_question_bank_prompt() -> str:
    """Condense QUESTION_BANK into plain text for the system prompt (no curly braces)."""
    tier_labels = {
        1: "TIER 1 -- Required (must have all before ready=true):",
        2: "TIER 2 -- Important (get at least budget_level + interests before ready=true):",
        3: "TIER 3 -- Enriching (weave in naturally once tier 2 is mostly covered):",
    }
    lines = ["QUESTION BANK -- cover these topics in order; extract from free text, ask if still missing:\n"]
    current_tier = 0
    for q in QUESTION_BANK:
        if q["tier"] != current_tier:
            current_tier = q["tier"]
            lines.append(f"\n{tier_labels[current_tier]}")
        cond_note = f"  [{_CONDITION_LABELS[q['condition']]}]" if q["condition"] else ""
        lines.append(f"  * {q['field']}: \"{q['question']}\"{cond_note}")
    return "\n".join(lines)


SYSTEM_PROMPT = """You are a warm, friendly travel planning assistant. Your job is to understand what the user wants through natural conversation and extract structured travel preferences using the question bank below.

Today's date: {today}

{question_bank}

IMPORTANT: Respond with ONLY valid JSON -- no markdown, no code fences, no extra text. Use this exact structure:
{{
  "reply": "<conversational response -- warm, 1-2 sentences + one follow-up question from the bank if not ready>",
  "extracted": {{
    "origin": "<departure city/airport, null if not mentioned>",
    "travel_start": "<YYYY-MM-DD, null if unknown>",
    "travel_end": "<YYYY-MM-DD, null if unknown>",
    "num_travelers": <total headcount including kids, null if unknown>,
    "has_kids": <true/false/null>,
    "kids_ages": [<integer ages, empty if no kids>],
    "traveling_with": "<solo|couple|family|friends|null>",
    "interests": [<subset of: nature,culture,adventure,relaxation,food,nightlife,shopping,history,art,beaches,mountains,wildlife>],
    "budget_level": "<low|moderate|high|luxury|null>",
    "budget_daily": <estimated USD per person per day, null if unknown>,
    "travel_style": "<budget|moderate|comfort|luxury|null>",
    "preferred_weather": "<hot|warm|mild|cold|null>",
    "passport_country": "<2-letter ISO code, null if unknown>",
    "visa_preference": "<visa_free|evisa_ok|visa_ok|null>",
    "accommodation_type": "<hotel|hostel|airbnb|resort|villa|null>",
    "activity_pace": "<relaxed|moderate|packed|null>",
    "adventure_level": "<low|medium|high|null>",
    "nightlife_priority": "<high|medium|low|null>",
    "car_hire": <true/false/null>,
    "flight_class": "<economy|premium_economy|business|first|null>",
    "dietary_restrictions": [<list of strings, empty if none>],
    "accessibility_needs": [<list of strings, empty if none>],
    "special_occasion": "<honeymoon|anniversary|birthday|milestone|none|null>",
    "past_destinations": [<list of places already visited or to avoid, empty if none>],
    "special_requests": "<any extra preferences as free text, null if none>"
  }},
  "ready": <true ONLY when origin, travel_start, travel_end, num_travelers are all known AND (budget_level is known OR interests is non-empty)>,
  "suggestions": ["<2-3 short clickable reply options for your question>"]
}}

Extraction rules:
- Easter 2026 = April 2-13. "Easter holidays April 5-12" -> travel_start: 2026-04-05, travel_end: 2026-04-12
- "5 days" -> calculate travel_end from travel_start if start is known
- "2 adults and 2 kids aged 7 and 10" -> num_travelers: 4, has_kids: true, kids_ages: [7,10], traveling_with: family
- "Ages 2 and 7" -> kids_ages: [2,7]; "3, 9 and 14" -> kids_ages: [3,9,14]; "Teens — 15 and 17" -> kids_ages: [15,17]
- Extract EACH individual age, not ranges — if user says "3, 9 and 14" all three ages go in the list
- "just the two of us" -> num_travelers: 2, traveling_with: couple
- "beach holiday" -> interests: [beaches, relaxation]
- "family friendly" + kids mentioned -> add nature, beaches to interests if none listed
- "budget"/"cheap"/"backpacker" -> budget_level: low, travel_style: budget, budget_daily: 75
- "mid-range"/"moderate" -> budget_level: moderate, travel_style: moderate, budget_daily: 175
- "comfortable"/"nice hotels" -> budget_level: high, travel_style: comfort, budget_daily: 350
- "luxury"/"splurge"/"5-star" -> budget_level: luxury, travel_style: luxury, budget_daily: 600
- "relaxed"/"slow travel"/"chill" -> activity_pace: relaxed
- "packed"/"see everything"/"action-packed" -> activity_pace: packed
- "honeymoon" -> special_occasion: honeymoon; add relaxation, beaches to interests
- "anniversary" -> special_occasion: anniversary
- "birthday" -> special_occasion: birthday
- UK/British -> passport_country: GB; Australian -> passport_country: AU; US/American -> passport_country: US
- "vegetarian"/"vegan"/"halal"/"kosher"/"gluten-free" -> dietary_restrictions list
- "wheelchair"/"mobility issues"/"limited walking" -> accessibility_needs list
- "business class" -> flight_class: business; "first class" -> flight_class: first; "premium economy" -> flight_class: premium_economy
- "hire a car"/"rent a car"/"car hire" -> car_hire: true
- "no nightlife"/"early nights" -> nightlife_priority: low; "love going out"/"clubbing" -> nightlife_priority: high
- "hotel" -> accommodation_type: hotel; "airbnb"/"apartment" -> accommodation_type: airbnb; "resort" -> accommodation_type: resort

Conversation rules:
- Extract EVERYTHING possible from each message before deciding what to ask next
- Cover Tier 1 first, then Tier 2; weave Tier 3 questions in naturally once tier 2 is mostly covered
- If user gives lots of info at once, only ask for the single most important missing piece
- Default passport_country to US silently if unclear -- never ask about it
- When ready=true, reply confirms all key details and says you're searching now -- no question needed
- Keep replies warm and human. Never say "I have extracted" or sound robotic
- suggestions should be plausible short answers to whatever question you just asked"""


async def call_llm(messages: list) -> dict:
    """Call the configured LLM and parse JSON response."""
    from app.services.ai_recommendation_service import AIRecommendationService
    svc = AIRecommendationService()
    client = svc._get_client()

    if not client:
        print("[TravelChat] No LLM client configured -- using context-aware fallback")
        return _fallback_parse(messages)

    raw = ""
    try:
        response = await client.chat.completions.create(
            model=svc.model,
            messages=messages,
            max_tokens=800,
            temperature=0.4,
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
    import re
    from datetime import date as _date

    user_msgs = [m for m in messages if m["role"] == "user"]
    asst_msgs = [m for m in messages if m["role"] == "assistant"]

    combined_users = " ".join(m["content"] for m in user_msgs).lower()

    extracted: dict = {
        "origin": None, "travel_start": None, "travel_end": None,
        "num_travelers": None, "has_kids": None, "kids_ages": [],
        "traveling_with": None, "interests": [], "budget_level": None,
        "budget_daily": None, "travel_style": None, "preferred_weather": None,
        "passport_country": None, "visa_preference": None,
        "accommodation_type": None, "activity_pace": None, "adventure_level": None,
        "nightlife_priority": None, "car_hire": None, "flight_class": None,
        # None = question not yet answered; [] = answered with "no restrictions"
        "dietary_restrictions": None, "accessibility_needs": None,
        "special_occasion": None, "past_destinations": None, "special_requests": None,
    }

    # ── Trigger keyword lists ─────────────────────────────────────────────────

    _origin_triggers = ("flying from", "departing from", "traveling from", "travelling from",
                        "where are you", "where will you", "city are you", "fly from",
                        "where are you based", "where do you live")
    _dates_triggers = ("when are you planning", "when do you", "when would you",
                       "planning to travel", "specific dates", "travel date",
                       "when are you going", "how long", "how many nights",
                       "how many days", "what dates", "when will you")
    _traveler_triggers = ("how many people", "how many traveler", "how many traveller",
                          "who's coming", "who is coming", "group size",
                          "travelling in total", "traveling in total")
    _budget_triggers = ("rough budget", "budget for", "price range", "how much", "afford")
    _kids_triggers = ("children be joining", "children joining", "kids joining",
                      "children coming", "little ones", "will any children")
    _kids_ages_triggers = ("how old are each", "how old are the", "ages of the", "age of the", "list all ages")
    _pace_triggers = ("pace or action", "action-packed", "like to travel", "itinerary style",
                      "relaxed pace", "how do you like")
    _weather_triggers = ("weather or climate", "climate preference", "temperature prefer",
                         "preference on weather", "preference on climate")
    _accommodation_triggers = ("type of accommodation", "type of place", "where to stay", "hotel or")
    _dietary_triggers = ("dietary requirement", "food restriction", "allergies", "dietary need")
    _nightlife_triggers = ("nightlife and evening", "going out", "evening entertainment")
    _occasion_triggers = ("special occasion", "celebrating", "anniversary or", "birthday trip")
    _access_triggers = ("accessibility or mobility", "mobility need", "wheelchair")
    _car_triggers = ("hire a car", "public transport", "car or stick")
    _flight_triggers = ("cabin class", "flight class", "class of travel")
    _visa_triggers = ("preference around visa", "visa preference")

    # ── Date extraction helper (handles holiday names + ISO dates) ────────────

    def _try_extract_dates(text: str):
        if extracted["travel_start"]:
            return  # already have dates, don't overwrite
        t = text.lower()
        today = _date.today()
        yr = today.year
        if "easter" in t:
            extracted["travel_start"] = f"{yr}-04-02"
            extracted["travel_end"] = f"{yr}-04-13"
        elif "christmas" in t or "xmas" in t:
            extracted["travel_start"] = f"{yr}-12-23"
            extracted["travel_end"] = f"{yr + 1}-01-02"
        elif "new year" in t:
            extracted["travel_start"] = f"{yr}-12-30"
            extracted["travel_end"] = f"{yr + 1}-01-05"
        elif "summer" in t:
            extracted["travel_start"] = f"{yr}-07-15"
            extracted["travel_end"] = f"{yr}-08-15"
        elif "next month" in t:
            nm_month = (today.month % 12) + 1
            nm_year = yr if today.month < 12 else yr + 1
            extracted["travel_start"] = f"{nm_year}-{nm_month:02d}-01"
            extracted["travel_end"] = f"{nm_year}-{nm_month:02d}-14"
        elif "spring" in t:
            extracted["travel_start"] = f"{yr}-04-15"
            extracted["travel_end"] = f"{yr}-04-28"
        elif "autumn" in t or "fall" in t:
            extracted["travel_start"] = f"{yr}-10-01"
            extracted["travel_end"] = f"{yr}-10-14"
        # ISO dates
        iso = re.findall(r'\d{4}-\d{2}-\d{2}', text)
        if len(iso) >= 2:
            extracted["travel_start"] = iso[0]
            extracted["travel_end"] = iso[1]
        elif len(iso) == 1:
            extracted["travel_start"] = iso[0]

    # ── Apply context for a single Q-A pair ──────────────────────────────────

    def _apply_pair(q_lower: str, ans: str):
        a = ans.lower()
        if any(t in q_lower for t in _origin_triggers):
            if not extracted["origin"]:
                extracted["origin"] = ans

        elif any(t in q_lower for t in _dates_triggers):
            _try_extract_dates(ans)

        elif any(t in q_lower for t in _traveler_triggers):
            if not extracted["num_travelers"]:
                if any(w in a for w in ("just me", "solo", "alone", "myself", "on my own", "only me")):
                    extracted["num_travelers"] = 1
                    if not extracted["traveling_with"]:
                        extracted["traveling_with"] = "solo"
                else:
                    nums = re.findall(r'\d+', ans)
                    if nums:
                        extracted["num_travelers"] = int(nums[0])

        elif any(t in q_lower for t in _budget_triggers):
            if not extracted["budget_level"]:
                if any(w in a for w in ("budget", "cheap", "backpack", "low", "75")):
                    extracted["budget_level"] = "low"; extracted["budget_daily"] = 75
                elif any(w in a for w in ("luxury", "splurge", "5-star", "400")):
                    extracted["budget_level"] = "luxury"; extracted["budget_daily"] = 600
                elif any(w in a for w in ("comfort", "nice", "high", "350")):
                    extracted["budget_level"] = "high"; extracted["budget_daily"] = 350
                elif any(w in a for w in ("mid", "moderate", "175", "200")):
                    extracted["budget_level"] = "moderate"; extracted["budget_daily"] = 175

        elif any(t in q_lower for t in _kids_triggers):
            if extracted["has_kids"] is None:
                if any(w in a for w in ("no", "none", "without", "don't", "nope")):
                    extracted["has_kids"] = False
                else:
                    extracted["has_kids"] = True
                    nums = re.findall(r'\d+', ans)
                    if nums:
                        extracted["kids_ages"] = [int(n) for n in nums]

        elif any(t in q_lower for t in _kids_ages_triggers):
            if not extracted["kids_ages"]:
                nums = re.findall(r'\d+', ans)
                if nums:
                    extracted["kids_ages"] = [int(n) for n in nums]
                    extracted["has_kids"] = True

        elif any(t in q_lower for t in _pace_triggers):
            if not extracted["activity_pace"]:
                if any(w in a for w in ("relax", "slow", "easy", "chill", "downtime")):
                    extracted["activity_pace"] = "relaxed"
                elif any(w in a for w in ("packed", "everything", "full", "action")):
                    extracted["activity_pace"] = "packed"
                else:
                    extracted["activity_pace"] = "moderate"

        elif any(t in q_lower for t in _weather_triggers):
            if not extracted["preferred_weather"]:
                if "hot" in a: extracted["preferred_weather"] = "hot"
                elif "warm" in a: extracted["preferred_weather"] = "warm"
                elif "mild" in a: extracted["preferred_weather"] = "mild"
                elif any(w in a for w in ("cool", "cold", "crisp")): extracted["preferred_weather"] = "cold"

        elif any(t in q_lower for t in _accommodation_triggers):
            if not extracted["accommodation_type"]:
                if "hotel" in a: extracted["accommodation_type"] = "hotel"
                elif "airbnb" in a or "apartment" in a: extracted["accommodation_type"] = "airbnb"
                elif "resort" in a: extracted["accommodation_type"] = "resort"
                elif "hostel" in a: extracted["accommodation_type"] = "hostel"
                elif "villa" in a: extracted["accommodation_type"] = "villa"

        elif any(t in q_lower for t in _dietary_triggers):
            # Mark as answered (even if empty — prevents the question looping)
            if extracted["dietary_restrictions"] is None:
                extracted["dietary_restrictions"] = []
            if "vegetarian" in a and "vegetarian" not in extracted["dietary_restrictions"]:
                extracted["dietary_restrictions"].append("vegetarian")
            if "vegan" in a and "vegan" not in extracted["dietary_restrictions"]:
                extracted["dietary_restrictions"].append("vegan")
            if "halal" in a and "halal" not in extracted["dietary_restrictions"]:
                extracted["dietary_restrictions"].append("halal")
            if "kosher" in a and "kosher" not in extracted["dietary_restrictions"]:
                extracted["dietary_restrictions"].append("kosher")
            if "gluten" in a and "gluten-free" not in extracted["dietary_restrictions"]:
                extracted["dietary_restrictions"].append("gluten-free")

        elif any(t in q_lower for t in _nightlife_triggers):
            if not extracted["nightlife_priority"]:
                if any(w in a for w in ("yes", "love", "important", "very", "definitely")):
                    extracted["nightlife_priority"] = "high"
                elif any(w in a for w in ("no", "not", "none", "nope")):
                    extracted["nightlife_priority"] = "low"
                else:
                    extracted["nightlife_priority"] = "medium"

        elif any(t in q_lower for t in _occasion_triggers):
            if not extracted["special_occasion"]:
                if "honeymoon" in a: extracted["special_occasion"] = "honeymoon"
                elif "anniversary" in a: extracted["special_occasion"] = "anniversary"
                elif "birthday" in a: extracted["special_occasion"] = "birthday"
                elif "milestone" in a: extracted["special_occasion"] = "milestone"
                else: extracted["special_occasion"] = "none"

        elif any(t in q_lower for t in _car_triggers):
            if extracted["car_hire"] is None:
                extracted["car_hire"] = any(w in a for w in ("yes", "car", "hire", "rent", "drive"))

        elif any(t in q_lower for t in _access_triggers):
            # Mark as answered (even if no special needs — prevents looping)
            if extracted["accessibility_needs"] is None:
                extracted["accessibility_needs"] = []
            if "wheelchair" in a and "wheelchair accessible" not in extracted["accessibility_needs"]:
                extracted["accessibility_needs"].append("wheelchair accessible")
            elif ("walking" in a or "limited" in a) and "limited walking" not in extracted["accessibility_needs"]:
                extracted["accessibility_needs"].append("limited walking")

        elif any(t in q_lower for t in _flight_triggers):
            if not extracted["flight_class"]:
                if "first" in a: extracted["flight_class"] = "first"
                elif "business" in a: extracted["flight_class"] = "business"
                elif "premium" in a: extracted["flight_class"] = "premium_economy"
                else: extracted["flight_class"] = "economy"

        elif any(t in q_lower for t in _visa_triggers):
            if not extracted["visa_preference"]:
                if "free" in a or "no visa" in a: extracted["visa_preference"] = "visa_free"
                elif "evisa" in a or "e-visa" in a or "online" in a: extracted["visa_preference"] = "evisa_ok"
                else: extracted["visa_preference"] = "visa_ok"

    # ── Process ALL past Q-A pairs (not just the last one) ───────────────────
    # Bot reply at index i → user answer at user_msgs[i+1]
    for pair_idx in range(len(asst_msgs)):
        q_lower = asst_msgs[pair_idx]["content"].lower()
        ans_idx = pair_idx + 1
        if ans_idx >= len(user_msgs):
            break
        _apply_pair(q_lower, user_msgs[ans_idx]["content"].strip())

    # Also try to extract dates from ANY user message (catches initial free-text messages)
    if not extracted["travel_start"]:
        _try_extract_dates(combined_users)

    # ── Scan ALL user text for signals ───────────────────────────────────────

    def _add_interest(val: str):
        if val not in extracted["interests"]:
            extracted["interests"].append(val)

    if "beach" in combined_users or "seaside" in combined_users or "coastal" in combined_users:
        _add_interest("beaches")
    if "mountain" in combined_users or "hiking" in combined_users or "trek" in combined_users:
        _add_interest("mountains")
    if "culture" in combined_users or "museum" in combined_users:
        _add_interest("culture")
    if "history" in combined_users or "historic" in combined_users:
        _add_interest("history")
    if "food" in combined_users or "cuisine" in combined_users or "restaurant" in combined_users:
        _add_interest("food")
    if "adventure" in combined_users or "thrill" in combined_users:
        _add_interest("adventure")
    if "nightlife" in combined_users or "clubbing" in combined_users:
        _add_interest("nightlife")
    if "wildlife" in combined_users or "safari" in combined_users:
        _add_interest("wildlife")
    if "relax" in combined_users or "wellness" in combined_users or "spa" in combined_users:
        _add_interest("relaxation")
    if "art" in combined_users or "gallery" in combined_users:
        _add_interest("art")
    if "shop" in combined_users or "market" in combined_users:
        _add_interest("shopping")
    if "nature" in combined_users or "forest" in combined_users or "national park" in combined_users:
        _add_interest("nature")

    if "hot" in combined_users and not extracted["preferred_weather"]:
        extracted["preferred_weather"] = "hot"
    elif "warm" in combined_users or "sunny" in combined_users:
        if not extracted["preferred_weather"]:
            extracted["preferred_weather"] = "warm"
    if "cold" in combined_users or "snow" in combined_users or " ski " in combined_users:
        extracted["preferred_weather"] = "cold"
    elif "mild" in combined_users and not extracted["preferred_weather"]:
        extracted["preferred_weather"] = "mild"

    if "kid" in combined_users or "child" in combined_users:
        extracted["has_kids"] = True
        extracted["traveling_with"] = "family"
        ages = re.findall(r'aged?\s*(\d+)', combined_users)
        if ages and not extracted["kids_ages"]:
            extracted["kids_ages"] = [int(a) for a in ages]
        if not extracted["interests"]:
            extracted["interests"] = ["beaches", "nature"]
    if "family" in combined_users:
        extracted["traveling_with"] = "family"
        if extracted["has_kids"] is None:
            extracted["has_kids"] = True
    if "solo" in combined_users or "just me" in combined_users or "myself" in combined_users:
        if not extracted["num_travelers"]: extracted["num_travelers"] = 1
        extracted["traveling_with"] = "solo"
    if "couple" in combined_users or "two of us" in combined_users or "partner" in combined_users:
        if not extracted["num_travelers"]: extracted["num_travelers"] = 2
        extracted["traveling_with"] = "couple"
    if "friends" in combined_users or "group of" in combined_users:
        extracted["traveling_with"] = "friends"

    if not extracted["budget_level"]:
        if any(w in combined_users for w in ("budget", "cheap", "backpack", "affordable")):
            extracted["budget_level"] = "low"; extracted["budget_daily"] = 75
        elif any(w in combined_users for w in ("luxury", "splurge", "5-star", "five star")):
            extracted["budget_level"] = "luxury"; extracted["budget_daily"] = 600
        elif any(w in combined_users for w in ("comfort", "nice hotel")):
            extracted["budget_level"] = "high"; extracted["budget_daily"] = 350
        elif any(w in combined_users for w in ("mid-range", "moderate budget")):
            extracted["budget_level"] = "moderate"; extracted["budget_daily"] = 175

    _diet_keywords = {"vegetarian": "vegetarian", "vegan": "vegan", "halal": "halal", "gluten": "gluten-free"}
    for kw, label in _diet_keywords.items():
        if kw in combined_users:
            if extracted["dietary_restrictions"] is None:
                extracted["dietary_restrictions"] = []
            if label not in extracted["dietary_restrictions"]:
                extracted["dietary_restrictions"].append(label)

    if not extracted["special_occasion"]:
        if "honeymoon" in combined_users: extracted["special_occasion"] = "honeymoon"
        elif "anniversary" in combined_users: extracted["special_occasion"] = "anniversary"
        elif "birthday" in combined_users: extracted["special_occasion"] = "birthday"

    if "wheelchair" in combined_users:
        if extracted["accessibility_needs"] is None:
            extracted["accessibility_needs"] = []
        if "wheelchair accessible" not in extracted["accessibility_needs"]:
            extracted["accessibility_needs"].append("wheelchair accessible")

    if not extracted["flight_class"]:
        if "business class" in combined_users: extracted["flight_class"] = "business"
        elif "first class" in combined_users: extracted["flight_class"] = "first"
        elif "premium economy" in combined_users: extracted["flight_class"] = "premium_economy"

    if not extracted["car_hire"]:
        if any(p in combined_users for p in ("hire a car", "rent a car", "car hire")):
            extracted["car_hire"] = True

    if not extracted["activity_pace"]:
        if "relax" in combined_users and "packed" not in combined_users:
            extracted["activity_pace"] = "relaxed"
        elif "packed" in combined_users or "see everything" in combined_users:
            extracted["activity_pace"] = "packed"

    # ── Track which question fields the bot already asked and got a response for ─
    # This prevents infinite loops on tier-3 fields that have no specific handler.
    _asked_and_answered: set = set()
    for _ai, asst_msg in enumerate(asst_msgs):
        if _ai + 1 >= len(user_msgs):
            break  # no user response yet
        _q_text = asst_msg["content"].lower()
        for _q in QUESTION_BANK:
            if _q["question"].lower()[:40] in _q_text:
                _asked_and_answered.add(_q["field"])

    # ── Walk question bank to find next missing field ─────────────────────────

    def _is_ready() -> bool:
        return bool(
            extracted.get("origin") and extracted.get("travel_start") and
            extracted.get("travel_end") and extracted.get("num_travelers") and
            (extracted.get("budget_level") or extracted.get("interests"))
        )

    def _field_missing(q: dict) -> bool:
        f = q["field"]
        if f == "origin": return not extracted.get("origin")
        if f == "travel_start": return not extracted.get("travel_start") or not extracted.get("travel_end")
        if f == "num_travelers": return not extracted.get("num_travelers")
        if f == "budget_level": return not extracted.get("budget_level")
        if f == "has_kids": return extracted.get("has_kids") is None and (extracted.get("num_travelers") or 1) > 1
        if f == "kids_ages": return extracted.get("has_kids") is True and not extracted.get("kids_ages")
        if f == "interests": return not extracted.get("interests")
        if f == "activity_pace": return not extracted.get("activity_pace")
        if f == "preferred_weather": return not extracted.get("preferred_weather")
        if f == "accommodation_type": return not extracted.get("accommodation_type")
        if f == "dietary_restrictions": return extracted.get("dietary_restrictions") is None
        if f == "adventure_level": return not extracted.get("adventure_level") and f not in _asked_and_answered
        if f == "nightlife_priority": return not extracted.get("nightlife_priority")
        if f == "car_hire": return extracted.get("car_hire") is None
        if f == "special_occasion": return not extracted.get("special_occasion")
        if f == "accessibility_needs": return extracted.get("accessibility_needs") is None
        if f == "flight_class": return not extracted.get("flight_class")
        if f == "visa_preference": return not extracted.get("visa_preference")
        if f == "past_destinations": return extracted.get("past_destinations") is None and f not in _asked_and_answered
        if f == "special_requests": return extracted.get("special_requests") is None and f not in _asked_and_answered
        return False

    tier2_done = bool(
        extracted.get("origin") and extracted.get("travel_start") and
        extracted.get("num_travelers") and
        (extracted.get("budget_level") or extracted.get("interests"))
    )

    for q in QUESTION_BANK:
        if not _check_condition(q["condition"], extracted):
            continue
        if q["tier"] == 3 and not tier2_done:
            continue
        if _field_missing(q):
            return {
                "reply": q["question"],
                "extracted": extracted,
                "ready": False,
                "suggestions": q["suggestions"],
            }

    return {
        "reply": "Great, I have everything I need — searching for your perfect destinations now!",
        "extracted": extracted,
        "ready": _is_ready() or True,
        "suggestions": [],
    }


@router.post("/travel", response_model=TravelChatResponse)
async def travel_chat(request: TravelChatRequest):
    """
    LLM-powered travel preference extraction through natural conversation.
    Send the full message history; receive a reply, extracted fields, and ready flag.
    """
    today = date.today().isoformat()
    question_bank_text = _build_question_bank_prompt()
    system = SYSTEM_PROMPT.format(today=today, question_bank=question_bank_text)

    llm_messages = [{"role": "system", "content": system}]
    for m in request.messages:
        llm_messages.append({"role": m.role, "content": m.content})

    result = await call_llm(llm_messages)

    return TravelChatResponse(
        reply=result.get("reply", "Tell me more about your trip!"),
        extracted=result.get("extracted", {}),
        ready=result.get("ready", False),
        suggestions=result.get("suggestions", []),
    )
