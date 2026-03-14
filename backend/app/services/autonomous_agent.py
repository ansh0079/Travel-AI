"""
Autonomous AI Travel Agent
==========================

Streams SSE-compatible events as it:
  1. Extracts travel preferences from the user message
  2. Builds a prioritised research plan
  3. Executes tasks (weather, visa, attractions, flights, hotels, events, web search)
  4. Synthesises all findings into a comprehensive travel plan

Event types emitted:
  status | research_started | task_started | task_completed | task_failed |
  plan_presented | done | error
"""

import asyncio
import json
import random
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from app.config import get_settings, POPULAR_DESTINATIONS
from app.services.agent_service import TravelResearchAgent
from app.services.auto_research_agent import AutoResearchAgent, ResearchDepth
from app.services.chat_service import ChatMessage, ChatService, ChatSession
from app.services.travel_agent_interpreter import TravelAgentInterpreter
from app.services.proactive_agent import get_proactive_agent
from app.utils.decision_engine import get_decision_engine
from app.utils.destination_affinity_graph import get_destination_affinity_graph
from app.utils.error_pattern_learner import get_error_pattern_learner
from app.utils.hypothesis_engine import get_hypothesis_engine
from app.utils.meta_learner import get_meta_learner
from app.utils.destination_knowledge_base import get_knowledge_base
from app.utils.user_style_classifier import get_user_style_classifier
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# ── Singleton ────────────────────────────────────────────────────────────────
_agent_instance: Optional["AutonomousAgent"] = None
_execution_registry: Dict[str, "_SessionExecutionControl"] = {}
_MAX_SESSION_LEARNING_SIGNALS = 100


class _SessionExecutionControl:
    def __init__(self) -> None:
        self.cancel_event = asyncio.Event()
        self.running_tasks: Set[asyncio.Task[Any]] = set()


def _start_execution(session_id: str) -> "_SessionExecutionControl":
    existing = _execution_registry.pop(session_id, None)
    if existing:
        existing.cancel_event.set()
        for task in list(existing.running_tasks):
            task.cancel()

    control = _SessionExecutionControl()
    _execution_registry[session_id] = control
    return control


def get_execution_control(session_id: str) -> Optional["_SessionExecutionControl"]:
    return _execution_registry.get(session_id)


def cancel_execution(session_id: str) -> bool:
    control = _execution_registry.get(session_id)
    if not control:
        return False
    control.cancel_event.set()
    for task in list(control.running_tasks):
        task.cancel()
    return True


def _clear_execution(session_id: str, control: Optional["_SessionExecutionControl"] = None) -> None:
    existing = _execution_registry.get(session_id)
    if existing and (control is None or existing is control):
        _execution_registry.pop(session_id, None)


def append_learning_signal(
    planning_data: Optional[Dict[str, Any]],
    *,
    signal_type: str,
    destination: Optional[str] = None,
    source: str = "",
    weight: Optional[Any] = None,
    features: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if not isinstance(planning_data, dict):
        return None

    normalized_type = str(signal_type or "").strip().lower()
    if not normalized_type:
        return None

    normalized_destination = str(destination or "").strip()
    normalized_source = str(source or "").strip().lower()
    feature_list = [
        str(feature).strip()
        for feature in (features or [])
        if str(feature).strip()
    ]

    try:
        numeric_weight = round(float(weight), 2) if weight is not None else None
    except (TypeError, ValueError):
        numeric_weight = None

    entry: Dict[str, Any] = {
        "type": normalized_type,
        "destination": normalized_destination,
        "source": normalized_source,
        "features": feature_list,
        "timestamp": datetime.now().isoformat(),
    }
    if numeric_weight is not None:
        entry["weight"] = numeric_weight

    if isinstance(metadata, dict):
        for key, value in metadata.items():
            if value in (None, "", [], {}):
                continue
            entry[str(key)] = value

    learning_signals = planning_data.setdefault("learning_signals", [])
    if not isinstance(learning_signals, list):
        learning_signals = []
    learning_signals.append(entry)
    planning_data["learning_signals"] = learning_signals[-_MAX_SESSION_LEARNING_SIGNALS:]
    return entry


def summarize_learning_signals(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        raw_signals = payload.get("learning_signals") or []
    elif isinstance(payload, list):
        raw_signals = payload
    else:
        raw_signals = []

    if not isinstance(raw_signals, list):
        raw_signals = []

    type_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    destination_counts: Counter[str] = Counter()
    positive_signals = 0
    negative_signals = 0
    abs_weight_total = 0.0
    weighted_count = 0

    for signal in raw_signals:
        if not isinstance(signal, dict):
            continue

        signal_type = str(signal.get("type") or "unknown").strip().lower() or "unknown"
        source = str(signal.get("source") or "unknown").strip().lower() or "unknown"
        destination = str(signal.get("destination") or "").strip()

        type_counts[signal_type] += 1
        source_counts[source] += 1
        if destination:
            destination_counts[destination] += 1

        try:
            numeric_weight = float(signal.get("weight"))
        except (TypeError, ValueError):
            numeric_weight = None

        if numeric_weight is not None:
            abs_weight_total += abs(numeric_weight)
            weighted_count += 1
            if numeric_weight > 0:
                positive_signals += 1
            elif numeric_weight < 0:
                negative_signals += 1

    return {
        "total_signals": int(sum(type_counts.values())),
        "positive_signals": int(positive_signals),
        "negative_signals": int(negative_signals),
        "avg_abs_weight": round(abs_weight_total / weighted_count, 2) if weighted_count else 0.0,
        "type_counts": {
            key: count
            for key, count in sorted(type_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
        },
        "source_counts": {
            key: count
            for key, count in sorted(source_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
        },
        "top_destinations": [
            {"destination": destination, "count": count}
            for destination, count in destination_counts.most_common(5)
        ],
    }


def get_autonomous_agent() -> "AutonomousAgent":
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AutonomousAgent()
    return _agent_instance


# ── Enums & Models ───────────────────────────────────────────────────────────

class AgentState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PLANNING = "planning"
    RESEARCHING = "researching"
    SYNTHESIZING = "synthesizing"
    PRESENTING = "presenting"
    WAITING_FOR_INPUT = "waiting_for_input"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ResearchPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResearchTask(BaseModel):
    id: str
    type: str
    priority: ResearchPriority
    priority_score: float = 0.0
    destination: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AutonomousAgentConfig(BaseModel):
    auto_research: bool = True
    max_research_iterations: int = 5
    research_depth: ResearchDepth = ResearchDepth.STANDARD
    enable_web_browsing: bool = True
    enable_real_time_updates: bool = True
    max_destinations: int = 3
    max_concurrent_tasks: int = 4
    require_user_confirmation: bool = False
    learning_enabled: bool = True


# ── Destination helpers ──────────────────────────────────────────────────────

_DEST_MAP: Dict[str, Dict] = {}
_DESTINATION_CITY_BY_NAME: Dict[str, str] = {}
_DESTINATION_COUNTRY_CODE_BY_NAME: Dict[str, str] = {}
_DESTINATION_AIRPORT_CODES_BY_NAME: Dict[str, List[str]] = {}
_DESTINATION_TAGS_BY_NAME: Dict[str, List[str]] = {}
for _d in POPULAR_DESTINATIONS:
    lookup_keys = [_d.get("name"), _d.get("city"), _d.get("id"), *(_d.get("aliases") or [])]
    for _key in lookup_keys:
        normalized_key = str(_key or "").strip().lower()
        if normalized_key:
            _DEST_MAP[normalized_key] = _d
            _DESTINATION_TAGS_BY_NAME[normalized_key] = [
                str(tag).strip().lower()
                for tag in (_d.get("focus_tags") or [])
                if str(tag).strip()
            ]
    city_name = str(_d.get("city") or _d.get("name") or "").strip()
    country_code = str(_d.get("country_code") or "").strip().upper()
    airport_codes = [str(code).strip().upper() for code in (_d.get("airport_codes") or []) if str(code).strip()]
    for _key in lookup_keys:
        if _key and city_name:
            _DESTINATION_CITY_BY_NAME[str(_key).strip().lower()] = city_name
        if _key and airport_codes:
            _DESTINATION_AIRPORT_CODES_BY_NAME[str(_key).strip().lower()] = airport_codes
    for _key in (*lookup_keys, _d.get("country")):
        if _key and country_code:
            _DESTINATION_COUNTRY_CODE_BY_NAME[str(_key).strip().lower()] = country_code

# Hand-crafted extras not in POPULAR_DESTINATIONS
_EXTRA_COORDS: Dict[str, tuple] = {
    "bali": (-8.4095, 115.1889),
    "phuket": (7.8804, 98.3923),
    "kyoto": (35.0116, 135.7681),
    "maldives": (3.2028, 73.2207),
    "queenstown": (-45.0312, 168.6626),
    "costa rica": (9.7489, -83.7534),
    "iceland": (64.9631, -19.0208),
    "santorini": (36.3932, 25.4615),
    "machu picchu": (-13.1631, -72.5450),
    "amalfi": (40.6340, 14.6027),
    "london": (51.5074, -0.1278),
    "amsterdam": (52.3676, 4.9041),
    "berlin": (52.5200, 13.4050),
    "rome": (41.9028, 12.4964),
    "milan": (45.4642, 9.1900),
    "vienna": (48.2082, 16.3738),
    "prague": (50.0755, 14.4378),
    "lisbon": (38.7169, -9.1399),
    "madrid": (40.4168, -3.7038),
    "barcelona": (41.3851, 2.1734),
    "athens": (37.9838, 23.7275),
    "istanbul": (41.0082, 28.9784),
    "dubai": (25.2048, 55.2708),
    "singapore": (1.3521, 103.8198),
    "hong kong": (22.3193, 114.1694),
    "seoul": (37.5665, 126.9780),
    "osaka": (34.6937, 135.5023),
    "shanghai": (31.2304, 121.4737),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "cairo": (30.0444, 31.2357),
    "cape town": (-33.9249, 18.4241),
    "nairobi": (-1.2921, 36.8219),
    "sydney": (-33.8688, 151.2093),
    "melbourne": (-37.8136, 144.9631),
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "mexico city": (19.4326, -99.1332),
    "cancun": (21.1619, -86.8515),
    "rio de janeiro": (-22.9068, -43.1729),
    "buenos aires": (-34.6037, -58.3816),
    "lima": (-12.0464, -77.0428),
    "miami": (25.7617, -80.1918),
    "las vegas": (36.1699, -115.1398),
    "los angeles": (34.0522, -118.2437),
    "san francisco": (37.7749, -122.4194),
    "chicago": (41.8781, -87.6298),
    "washington dc": (38.9072, -77.0369),
    "boston": (42.3601, -71.0589),
    # Greek islands & Mediterranean
    "corfu": (39.6243, 19.9217),
    "mykonos": (37.4467, 25.3289),
    "rhodes": (36.4341, 28.2176),
    "crete": (35.2401, 24.8093),
    "zakynthos": (37.7883, 20.8989),
    "paros": (37.0856, 25.1489),
    "naxos": (37.1036, 25.3764),
    "lefkada": (38.7167, 20.6500),
    "kefalonia": (38.1753, 20.5690),
    "skiathos": (39.1622, 23.4872),
    "milos": (36.6897, 24.4400),
    "hydra": (37.3480, 23.4739),
    "ibiza": (38.9067, 1.4206),
    "mallorca": (39.6953, 3.0176),
    "menorca": (39.9496, 4.1156),
    "tenerife": (28.2916, -16.6291),
    "gran canaria": (27.9202, -15.5474),
    "lanzarote": (29.0469, -13.5899),
    "sicily": (37.5999, 14.0154),
    "sardinia": (40.1209, 9.0129),
    "capri": (40.5500, 14.2167),
    "positano": (40.6280, 14.4843),
    "dubrovnik": (42.6507, 18.0944),
    "split": (43.5081, 16.4402),
    "kotor": (42.4246, 18.7712),
    "valletta": (35.8997, 14.5147),
    "monaco": (43.7384, 7.4246),
    "nice": (43.7102, 7.2620),
    "florence": (43.7696, 11.2558),
    "venice": (45.4408, 12.3155),
    "naples": (40.8518, 14.2681),
    "porto": (41.1579, -8.6291),
    "seville": (37.3891, -5.9845),
    "granada": (37.1773, -3.5986),
    "bruges": (51.2093, 3.2247),
    "ghent": (51.0543, 3.7174),
    "salzburg": (47.8095, 13.0550),
    "innsbruck": (47.2692, 11.4041),
    "zurich": (47.3769, 8.5417),
    "geneva": (46.2044, 6.1432),
    "krakow": (50.0647, 19.9450),
    "warsaw": (52.2297, 21.0122),
    "budapest": (47.4979, 19.0402),
    "bucharest": (44.4268, 26.1025),
    "sofia": (42.6977, 23.3219),
    "riga": (56.9496, 24.1052),
    "tallinn": (59.4370, 24.7536),
    "vilnius": (54.6872, 25.2797),
    "reykjavik": (64.1466, -21.9426),
    "oslo": (59.9139, 10.7522),
    "stockholm": (59.3293, 18.0686),
    "copenhagen": (55.6761, 12.5683),
    "helsinki": (60.1699, 24.9384),
    "edinburgh": (55.9533, -3.1883),
    "dublin": (53.3498, -6.2603),
}

_EXTRA_COUNTRY_CODES: Dict[str, str] = {
    "amalfi": "IT",
    "amsterdam": "NL",
    "athens": "GR",
    "berlin": "DE",
    "boston": "US",
    "bruges": "BE",
    "budapest": "HU",
    "bucharest": "RO",
    "buenos aires": "AR",
    "cancun": "MX",
    "capri": "IT",
    "chicago": "US",
    "copenhagen": "DK",
    "corfu": "GR",
    "costa rica": "CR",
    "crete": "GR",
    "delhi": "IN",
    "dublin": "IE",
    "edinburgh": "GB",
    "florence": "IT",
    "geneva": "CH",
    "ghent": "BE",
    "gran canaria": "ES",
    "granada": "ES",
    "helsinki": "FI",
    "hong kong": "HK",
    "hydra": "GR",
    "ibiza": "ES",
    "iceland": "IS",
    "innsbruck": "AT",
    "kefalonia": "GR",
    "koh samui": "TH",
    "kotor": "ME",
    "krakow": "PL",
    "lanzarote": "ES",
    "las vegas": "US",
    "lefkada": "GR",
    "lima": "PE",
    "lisbon": "PT",
    "los angeles": "US",
    "machu picchu": "PE",
    "madrid": "ES",
    "mallorca": "ES",
    "maldives": "MV",
    "melbourne": "AU",
    "menorca": "ES",
    "mexico city": "MX",
    "milan": "IT",
    "milos": "GR",
    "monaco": "MC",
    "mumbai": "IN",
    "mykonos": "GR",
    "nairobi": "KE",
    "naples": "IT",
    "naxos": "GR",
    "nice": "FR",
    "osaka": "JP",
    "oslo": "NO",
    "paros": "GR",
    "phuket": "TH",
    "porto": "PT",
    "positano": "IT",
    "prague": "CZ",
    "queenstown": "NZ",
    "reykjavik": "IS",
    "rhodes": "GR",
    "riga": "LV",
    "rio de janeiro": "BR",
    "salzburg": "AT",
    "san francisco": "US",
    "santorini": "GR",
    "sardinia": "IT",
    "seoul": "KR",
    "seville": "ES",
    "shanghai": "CN",
    "sicily": "IT",
    "singapore": "SG",
    "skiathos": "GR",
    "sofia": "BG",
    "split": "HR",
    "stockholm": "SE",
    "sydney": "AU",
    "tallinn": "EE",
    "tenerife": "ES",
    "toronto": "CA",
    "valletta": "MT",
    "vancouver": "CA",
    "venice": "IT",
    "vienna": "AT",
    "vilnius": "LT",
    "warsaw": "PL",
    "washington dc": "US",
    "zakynthos": "GR",
    "zurich": "CH",
}
for _key, _code in _EXTRA_COUNTRY_CODES.items():
    _DESTINATION_COUNTRY_CODE_BY_NAME.setdefault(_key, _code)

# Alias map: shorthand → canonical name used in _extract_preferences
_DEST_ALIASES: Dict[str, str] = {
    "nyc": "New York",
    "new york city": "New York",
    "ny": "New York",
    "la": "Los Angeles",
    "sf": "San Francisco",
    "dc": "Washington DC",
    "uk": "London",
    "england": "London",
    "france": "Paris",
    "japan": "Tokyo",
    "thailand": "Bangkok",
    "indonesia": "Bali",
    "greece": "Athens",
    "egypt": "Cairo",
    "australia": "Sydney",
    "nz": "Queenstown",
    "new zealand": "Queenstown",
    "uae": "Dubai",
    "south africa": "Cape Town",
    "brazil": "Rio de Janeiro",
    "argentina": "Buenos Aires",
    "peru": "Lima",
    "india": "Mumbai",
}


def _get_coords(destination: str) -> Optional[tuple]:
    key = destination.strip().lower()
    rec = _DEST_MAP.get(key)
    if rec:
        return rec["coordinates"]["lat"], rec["coordinates"]["lng"]
    return _EXTRA_COORDS.get(key)


def _get_destination_city(destination: str) -> str:
    key = str(destination or "").strip().lower()
    if not key:
        return ""
    return _DESTINATION_CITY_BY_NAME.get(key) or str(destination).strip()


def _get_country_code(destination: str) -> Optional[str]:
    key = str(destination or "").strip().lower()
    if not key:
        return None
    if len(key) == 2 and key.isalpha():
        return key.upper()
    return _DESTINATION_COUNTRY_CODE_BY_NAME.get(key) or _EXTRA_COUNTRY_CODES.get(key)


# ── Preference extraction ────────────────────────────────────────────────────

_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}

_INTEREST_KW: Dict[str, List[str]] = {
    "culture": ["culture", "museum", "history", "historic", "heritage", "art", "architecture"],
    "food": ["food", "cuisine", "restaurant", "eating", "gastronomy", "culinary"],
    "adventure": ["adventure", "hiking", "trekking", "outdoor", "extreme", "climbing"],
    "beach": ["beach", "ocean", "sea", "coast", "surf", "swimming", "snorkeling"],
    "shopping": ["shopping", "mall", "market", "bazaar", "boutique"],
    "nightlife": ["nightlife", "club", "bar", "party", "pub"],
    "nature": ["nature", "wildlife", "safari", "park", "forest", "garden", "national park"],
    "photography": ["photography", "photo", "scenic", "instagrammable"],
    "relaxation": ["relax", "spa", "wellness", "peaceful", "tranquil", "retreat"],
    "family": ["family", "kids", "children", "theme park", "amusement"],
}

# Region keywords — broad geographic areas that should NOT be kept as destinations
# but signal the user wants to travel to a new region (clearing previous destination).
_REGION_KEYWORDS: Dict[str, List[str]] = {
    "Europe": ["europe", "european"],
    "Asia": ["asia", "asian", "southeast asia", "east asia", "south asia"],
    "South America": ["south america", "latin america"],
    "North America": ["north america"],
    "Middle East": ["middle east"],
    "Africa": ["africa", "african"],
    "Oceania": ["oceania", "pacific islands"],
    "Caribbean": ["caribbean"],
    "Scandinavia": ["scandinavia", "scandinavian", "nordic"],
    "Balkans": ["balkans", "balkan"],
}

# Words that strongly indicate the user wants to start a completely new trip
_NEW_TRIP_SIGNALS = [
    "new trip", "new destination", "different destination", "different place",
    "somewhere else", "instead", "forget bali", "cancel that", "start over",
    "start fresh", "change destination", "never mind",
]


def _extract_preferences(text: str, existing: Dict[str, Any]) -> Dict[str, Any]:
    prefs = dict(existing)
    lower = text.lower()

    # ── New-trip intent: clear destinations so the agent asks fresh ──────────
    if any(signal in lower for signal in _NEW_TRIP_SIGNALS):
        prefs.pop("destinations", None)
        prefs.pop("region_intent", None)

    # ── Region detection ─────────────────────────────────────────────────────
    # If the user mentions a broad region (e.g. "europe") without a specific
    # city, clear the old destinations and store the region as context so the
    # agent can ask for a specific city within that region.
    detected_region = None
    for region_label, keywords in _REGION_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            detected_region = region_label
            break

    # Destinations — check aliases first, then the main map
    found = []
    # 1. Check alias map (e.g. "NYC" → "New York")
    for alias, canonical in _DEST_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", lower) and canonical not in found:
            found.append(canonical)
    # 2. Match against known destination map (minimum 4 chars to avoid false positives)
    for key, rec in _DEST_MAP.items():
        if len(key) >= 4 and (f" {key}" in f" {lower}" or lower.startswith(key)):
            city = rec["name"]
            if city not in found:
                found.append(city)
    # 3. Match against extra coords (e.g. "London", "Rome")
    for key in _EXTRA_COORDS:
        if len(key) >= 4 and re.search(r"\b" + re.escape(key) + r"\b", lower):
            canonical = key.title()
            if canonical not in found:
                found.append(canonical)
    # 4. Fallback: extract destination from explicit travel phrases
    #    e.g. "visit Corfu", "go to Santorini", "trip to X", or "Corfu, August 2026"
    if not found:
        travel_phrase = re.search(
            r"(?:visit|go to|going to|travel to|travelling to|traveling to|trip to|heading to|in|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            text
        )
        if travel_phrase:
            found.append(travel_phrase.group(1))
        else:
            # Last resort: first capitalised word(s) followed by a comma + date/number
            leading = re.match(r"^([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)?)\s*,\s*(?:\w+\s+)?\d{4}", text)
            if leading:
                found.append(leading.group(1).title())
    # Extract origin BEFORE finalising destinations so we can exclude it
    origin_m = re.search(r"(?:from|leaving|departing)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
    origin_city = origin_m.group(1) if origin_m else None
    if origin_city:
        prefs["origin"] = origin_city
        # Remove origin from destinations list
        found = [d for d in found if d.lower() != origin_city.lower()]

    if found:
        prefs["destinations"] = found[:3]
        prefs.pop("region_intent", None)  # specific city found — clear region
    elif detected_region:
        # Region mentioned but no specific city — clear stale destination and
        # store region context so the agent can ask "which city in Europe?"
        prefs.pop("destinations", None)
        prefs["region_intent"] = detected_region

    # Duration
    m = re.search(r"(\d+)\s*(day|week|night)", lower)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        prefs["duration"] = n * 7 if "week" in unit else n

    # Budget keywords — check "moderate budget" before "budget" to avoid false match
    if any(w in lower for w in ["luxury", "five star", "5-star", "high end", "premium"]):
        prefs["budget_level"] = "luxury"
    elif any(w in lower for w in ["moderate", "mid-range", "midrange", "medium"]):
        prefs["budget_level"] = "moderate"
    elif re.search(r"\bbudget\b", lower) and not re.search(r"\bmoderate\s+budget\b", lower):
        prefs["budget_level"] = "budget"
    elif any(w in lower for w in ["cheap", "affordable", "backpacker", "hostel"]):
        prefs["budget_level"] = "budget"

    # Budget dollar amount
    m2 = re.search(r"\$\s*([\d,]+)", text)
    if m2:
        prefs["budget_amount"] = int(m2.group(1).replace(",", ""))

    # Interests
    interests: List[str] = list(prefs.get("interests") or [])
    for interest, kws in _INTEREST_KW.items():
        if any(kw in lower for kw in kws) and interest not in interests:
            interests.append(interest)
    if interests:
        prefs["interests"] = interests

    # Traveling with
    if re.search(r"\b(solo|alone|by myself|myself)\b", lower):
        prefs["traveling_with"] = "solo"
    elif re.search(r"\b(couple|partner|spouse|wife|husband|girlfriend|boyfriend)\b", lower):
        prefs["traveling_with"] = "couple"
    elif re.search(r"\b(family|families|kids|children)\b", lower):
        prefs["traveling_with"] = "family"
    elif re.search(r"\b(friends|group|squad)\b", lower):
        prefs["traveling_with"] = "friends"

    # Month / dates
    for month_name, month_num in _MONTH_MAP.items():
        if re.search(r"\b" + month_name + r"\b", lower):
            yr_m = re.search(r"20\d\d", text)
            year = int(yr_m.group()) if yr_m else date.today().year
            duration = int(prefs.get("duration") or 7)
            end_day = min(28, 1 + duration)
            prefs["travel_dates"] = {
                "start": f"{year}-{month_num}-01",
                "end": f"{year}-{month_num}-{end_day:02d}",
            }
            break

    # Origin city (already extracted above, but handle if not yet set)
    if not prefs.get("origin"):
        origin_m2 = re.search(r"from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
        if origin_m2:
            prefs["origin"] = origin_m2.group(1)

    # Passport
    p_m = re.search(r"(us|uk|australian|canadian|indian|british|american)\s*(passport|citizen)", lower)
    if p_m:
        prefs["passport_country"] = {
            "us": "US", "american": "US", "uk": "UK", "british": "UK",
            "australian": "AU", "canadian": "CA", "indian": "IN",
        }.get(p_m.group(1), "US")

    return prefs


def _has_min_requirements(prefs: Dict) -> bool:
    """Only destination is required — dates and other details are optional.

    The agent will proceed with seasonal/general research if dates are missing,
    rather than blocking the user.
    """
    return bool(prefs.get("destinations"))


def _get_missing_fields(prefs: Dict) -> List[Dict[str, str]]:
    """Return list of truly blocking missing fields (destination only).

    Everything else is surfaced as optional enrichment questions, not blockers.
    """
    missing = []
    if not prefs.get("destinations"):
        missing.append({"field": "destinations", "question": "Where would you like to go?"})
    # Soft (non-blocking) hints — surfaced only when destination is already known
    if prefs.get("destinations"):
        if not prefs.get("travel_dates"):
            missing.append({"field": "travel_dates", "question": "When are you planning to travel? (e.g. 'April 2026') — I can do seasonal research without this"})
        if not prefs.get("origin"):
            missing.append({"field": "origin", "question": "Where will you be travelling from? (needed for flight search)"})
        if not prefs.get("traveling_with"):
            missing.append({"field": "traveling_with", "question": "Who's travelling? (solo, couple, family, friends)"})
        if not prefs.get("duration"):
            missing.append({"field": "duration", "question": "How many days is the trip?"})
        if not prefs.get("budget_level"):
            missing.append({"field": "budget_level", "question": "What's your budget level? (budget, moderate, luxury)"})
        if not prefs.get("interests"):
            missing.append({"field": "interests", "question": "What do you enjoy? (beaches, culture, food, adventure, nightlife, nature)"})
    return missing


def _merge_unique_list(*values: Any) -> List[str]:
    merged: List[str] = []
    seen: set = set()
    for value in values:
        items = value if isinstance(value, list) else [value]
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(text)
    return merged


def _normalize_travel_dates(value: Any, duration: Optional[int] = None) -> Optional[Dict[str, str]]:
    if isinstance(value, dict):
        start = str(value.get("start") or "").strip()
        end = str(value.get("end") or "").strip()
        if start or end:
            return {"start": start or end, "end": end or start}
        return None

    text = str(value or "").strip()
    if not text:
        return None

    iso_dates = re.findall(r"\b(\d{4}-\d{2}(?:-\d{2})?)\b", text)
    if iso_dates:
        start = iso_dates[0]
        end = iso_dates[1] if len(iso_dates) > 1 else iso_dates[0]
        if len(start) == 7:
            start = f"{start}-01"
        if len(end) == 7:
            day = min(28, 1 + int(duration or 7))
            end = f"{end}-{day:02d}"
        return {"start": start, "end": end}

    lowered = text.lower()
    for month_name, month_num in _MONTH_MAP.items():
        if re.search(r"\b" + re.escape(month_name) + r"\b", lowered):
            year_match = re.search(r"20\d\d", text)
            year = int(year_match.group()) if year_match else date.today().year
            trip_length = int(duration or 7)
            end_day = min(28, 1 + trip_length)
            return {
                "start": f"{year}-{month_num}-01",
                "end": f"{year}-{month_num}-{end_day:02d}",
            }
    return None


# ── Main agent class ─────────────────────────────────────────────────────────

class AutonomousAgent:
    """Fully autonomous AI travel research agent."""

    # Approx nightly hotel caps by budget level
    HOTEL_CAP = {"budget": 120.0, "moderate": 220.0, "high": 380.0, "luxury": 650.0}
    LOCAL_DAILY = {"budget": 70.0, "moderate": 120.0, "high": 220.0, "luxury": 400.0}
    EXTRA_COORDS = _EXTRA_COORDS
    EXTRA_COUNTRY_CODES = _EXTRA_COUNTRY_CODES

    def __init__(self, chat_service: Optional[ChatService] = None):
        self.settings = get_settings()
        self.chat_service = chat_service or ChatService()
        self.research_agent = TravelResearchAgent()
        self.auto_research_agent = AutoResearchAgent()
        self.interpreter = TravelAgentInterpreter(self.chat_service)
        self.config = AutonomousAgentConfig()

        # Phase 2: wire orchestrator for multi-agent coordination
        from app.agents.orchestrator import get_orchestrator
        self.orchestrator = get_orchestrator()

        # Apply meta-learner recommendations if available (e.g. optimal research depth)
        # With epsilon-greedy exploration: 10% of sessions try a random alternative
        # depth to collect experimental data for strategy improvement.
        self._is_exploration_session = False
        self._exploration_depth: Optional[str] = None
        try:
            import random
            recs = get_meta_learner().get_recommendations()
            optimal_depth_str = recs.get("optimal_research_depth")
            if optimal_depth_str:
                try:
                    optimal_depth = ResearchDepth(optimal_depth_str)
                    # ── Epsilon-greedy: 10% exploration ──────────────
                    epsilon = 0.10
                    if random.random() < epsilon:
                        # Pick a random DIFFERENT depth for exploration
                        alternatives = [
                            d for d in ResearchDepth
                            if d != optimal_depth
                        ]
                        if alternatives:
                            exploration_depth = random.choice(alternatives)
                            self.config.research_depth = exploration_depth
                            self._is_exploration_session = True
                            self._exploration_depth = exploration_depth.value
                            logger.info(
                                f"A/B Experiment: exploring depth "
                                f"{exploration_depth.value} instead of "
                                f"optimal {optimal_depth_str}"
                            )
                    else:
                        self.config.research_depth = optimal_depth
                        logger.debug(f"MetaLearner applied optimal depth: {optimal_depth_str}")
                except ValueError:
                    pass  # unknown depth value — ignore
        except Exception:
            pass

        # Per-conversation mutable state
        self.state = AgentState.IDLE
        self.current_session: Optional[ChatSession] = None
        self.research_tasks: List[ResearchTask] = []
        self.research_results: Dict[str, Any] = {}
        self.current_task: Optional[ResearchTask] = None
        self.completed_tasks: List[ResearchTask] = []
        self.progress_percentage = 0.0
        self._preferences: Dict[str, Any] = {}
        self._partial_results_sent = False
        self._execution_control: Optional[_SessionExecutionControl] = None
        self._research_started_at: Optional[datetime] = None
        self._run_metrics: Dict[str, Any] = {}
        self._meta_strategy: Optional[str] = None

    def _get_runtime_state(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "progress": int(self.progress_percentage),
            "current_task": self.current_task.model_dump(mode="json") if self.current_task else None,
            "tasks": [task.model_dump(mode="json") for task in self.research_tasks],
            "completed_tasks": [task.model_dump(mode="json") for task in self.completed_tasks],
            "research_results": self.research_results,
            "preferences": self._preferences,
            "research_metrics": self._research_metrics_snapshot(),
        }

    async def _persist_runtime_state(self, plan: Optional[Dict[str, Any]] = None) -> None:
        session = self.current_session
        if not session:
            return
        session.updated_at = datetime.now()
        session.extracted_preferences = dict(self._preferences or session.extracted_preferences or {})
        runtime_state = self._get_runtime_state()
        if plan is not None:
            runtime_state["plan"] = plan
        elif isinstance((session.planning_data.get("autonomous_runtime") or {}).get("plan"), dict):
            runtime_state["plan"] = session.planning_data["autonomous_runtime"]["plan"]
        session.planning_data["autonomous_runtime"] = runtime_state
        await self.chat_service._save_session(session)

    async def _hydrate_session_memory(self, session: ChatSession, user_id: Optional[str]) -> None:
        if user_id:
            session.user_id = user_id
        if not session.user_id:
            return
        session.planning_data["use_durable_preferences"] = True
        await self.chat_service._hydrate_from_user_profile(session)

    def _normalize_preferences(self, prefs: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(prefs or {})
        travel_dates = _normalize_travel_dates(
            normalized.get("travel_dates"),
            normalized.get("duration"),
        )
        if travel_dates:
            normalized["travel_dates"] = travel_dates
        elif "travel_dates" in normalized:
            normalized.pop("travel_dates", None)

        normalized["interests"] = _merge_unique_list(normalized.get("interests"))
        return {
            key: value
            for key, value in normalized.items()
            if value not in (None, "", [], {})
        }

    def _merge_preferences_with_memory(self, session: ChatSession) -> Dict[str, Any]:
        durable = self.chat_service.memory.get_durable_preferences(session)
        current = self._normalize_preferences(session.extracted_preferences or {})
        merged = dict(durable)
        merged.update(current)
        merged["interests"] = _merge_unique_list(durable.get("interests"), current.get("interests"))
        if durable.get("dietary_restrictions") or current.get("dietary_restrictions"):
            merged["dietary_restrictions"] = _merge_unique_list(
                durable.get("dietary_restrictions"),
                current.get("dietary_restrictions"),
            )
        return self._normalize_preferences(merged)

    def _boost_priority(
        self,
        priority: ResearchPriority,
        steps: int = 1,
    ) -> ResearchPriority:
        order = [
            ResearchPriority.CRITICAL,
            ResearchPriority.HIGH,
            ResearchPriority.MEDIUM,
            ResearchPriority.LOW,
        ]
        index = order.index(priority)
        return order[max(0, index - steps)]

    def _resolve_country_code(self, destination: str) -> Optional[str]:
        return _get_country_code(destination)

    async def _resolve_airport_code(self, service: Any, location: str) -> Optional[str]:
        text = str(location or "").strip()
        if not text:
            return None
        if len(text) == 3 and text.isalpha():
            return text.upper()

        known_codes = _DESTINATION_AIRPORT_CODES_BY_NAME.get(text.lower())
        if known_codes:
            return known_codes[0]

        candidates: List[str] = []
        for candidate in (text, _get_destination_city(text)):
            normalized = str(candidate or "").strip()
            if normalized and normalized.lower() not in {item.lower() for item in candidates}:
                candidates.append(normalized)

        for candidate in candidates:
            catalog_codes = _DESTINATION_AIRPORT_CODES_BY_NAME.get(candidate.lower())
            if catalog_codes:
                return catalog_codes[0]
            code = await service.get_airport_code(candidate)
            if code:
                return code.upper()
        return None

    def _infer_learned_interests(self, session: Optional[ChatSession]) -> List[str]:
        if not session or not session.user_id or not self.config.learning_enabled:
            return []
        try:
            from app.utils.learning_agent import get_learner

            profile = get_learner().get_user_profile(session.user_id) or {}
        except Exception as exc:
            logger.debug(f"Learning profile unavailable for {session.user_id}: {exc}")
            return []

        counts: Dict[str, int] = defaultdict(int)
        for interaction in profile.get("interactions", [])[-30:]:
            texts: List[str] = []
            for key in ("destination", "preferred_destinations", "rejection_reason"):
                value = interaction.get(key)
                if value:
                    texts.append(str(value))
            for feature in interaction.get("accepted_features") or []:
                texts.append(str(feature))
            feedback_data = interaction.get("feedback_data")
            if isinstance(feedback_data, dict):
                texts.extend(str(value) for value in feedback_data.values() if value)

            joined = " ".join(texts).lower()
            for interest, keywords in _INTEREST_KW.items():
                if any(keyword in joined for keyword in keywords):
                    counts[interest] += 1

        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [interest for interest, score in ranked if score > 0][:4]

    def _get_personalized_feature_weights(self, session: Optional[ChatSession]) -> Dict[str, float]:
        if not session or not session.user_id or not self.config.learning_enabled:
            return {}
        try:
            from app.utils.learning_agent import get_learner

            return get_learner().get_personalized_weights(session.user_id) or {}
        except Exception as exc:
            logger.debug(f"Personalized feature weights unavailable for {session.user_id}: {exc}")
            return {}

    def _get_user_style_profile(self, session: Optional[ChatSession]) -> Dict[str, Any]:
        if not session or not session.user_id or not self.config.learning_enabled:
            return {}
        try:
            profile = get_user_style_classifier().get_user_style(session.user_id)
        except Exception as exc:
            logger.debug(f"User style profile unavailable for {session.user_id}: {exc}")
            return {}

        if not isinstance(profile, dict):
            return {}
        if int(profile.get("interactions", 0) or 0) <= 0:
            return {}
        return profile

    def _get_active_hypotheses(self, session: Optional[ChatSession]) -> List[Dict[str, Any]]:
        if not session or not session.user_id or not self.config.learning_enabled:
            return []
        try:
            hypotheses = get_hypothesis_engine().get_active_hypotheses(session.user_id)
        except Exception as exc:
            logger.debug(f"Active hypotheses unavailable for {session.user_id}: {exc}")
            return []
        return hypotheses if isinstance(hypotheses, list) else []

    def _get_hypothesis_recommendations(self, session: Optional[ChatSession]) -> Dict[str, Any]:
        if not session or not session.user_id or not self.config.learning_enabled:
            return {}
        try:
            recommendations = get_hypothesis_engine().get_recommendations_for_user(session.user_id)
        except Exception as exc:
            logger.debug(f"Hypothesis recommendations unavailable for {session.user_id}: {exc}")
            return {}

        if not isinstance(recommendations, dict):
            return {}

        has_signal = bool(
            recommendations.get("hypothesis_count")
            or recommendations.get("strategies")
            or recommendations.get("filters")
            or recommendations.get("boosts")
        )
        return recommendations if has_signal else {}

    def _get_destination_affinity_recommendations(
        self,
        session: Optional[ChatSession],
        candidates: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not session or not session.user_id or not self.config.learning_enabled:
            return {}

        normalized_candidates = [
            str(candidate).strip()
            for candidate in (candidates or [])
            if str(candidate).strip()
        ]
        if not normalized_candidates:
            return {}

        try:
            affinity_graph = get_destination_affinity_graph()
            recommendations = affinity_graph.recommend_for_user(
                session.user_id,
                normalized_candidates,
                limit=len(normalized_candidates),
            )
        except Exception as exc:
            logger.debug(f"Destination affinity recommendations unavailable for {session.user_id}: {exc}")
            return {}

        if not isinstance(recommendations, list):
            return {}

        by_destination: Dict[str, Dict[str, Any]] = {}
        destination_details: Dict[str, Dict[str, Any]] = {}
        has_signal = False
        for recommendation in recommendations:
            if not isinstance(recommendation, dict):
                continue

            destination = str(recommendation.get("destination") or "").strip()
            if not destination:
                continue

            by_destination[destination] = recommendation
            try:
                predicted_rating = float(recommendation.get("predicted_rating", 0.0) or 0.0)
            except (TypeError, ValueError):
                predicted_rating = 0.0

            explanation = recommendation.get("explanation") or {}
            methods_used = explanation.get("methods_used") if isinstance(explanation, dict) else []
            if predicted_rating > 0.55 or recommendation.get("acceptance_rate") is not None or methods_used:
                has_signal = True

            try:
                detail = affinity_graph.get_destination_affinity(destination)
            except Exception:
                detail = {}
            if isinstance(detail, dict) and detail:
                destination_details[destination] = detail

        if not has_signal and not destination_details:
            return {}

        return {
            "recommendations": recommendations,
            "by_destination": by_destination,
            "destination_details": destination_details,
        }

    def _get_adaptive_criteria_weights(self, session: Optional[ChatSession]) -> Dict[str, float]:
        if not self.config.learning_enabled:
            return {}
        try:
            profile = get_meta_learner().get_decision_weight_profile(
                user_id=session.user_id if session else None,
            )
        except Exception as exc:
            logger.debug(f"Adaptive criteria weights unavailable: {exc}")
            return {}

        if isinstance(profile, dict):
            profile_source = str(profile.get("source") or "")
            profile_confidence = float(profile.get("confidence", 0.0) or 0.0)
            if profile_source in {"default", "per_user_fallback"} and profile_confidence <= 0:
                return {}

        weights = profile.get("weights") if isinstance(profile, dict) else {}
        if not isinstance(weights, dict):
            return {}

        normalized: Dict[str, float] = {}
        for criterion, weight in weights.items():
            if isinstance(weight, (int, float)):
                normalized[str(criterion)] = round(float(weight), 3)

        if normalized:
            return normalized
        return {}

    def _apply_learning_bias(self, session: Optional[ChatSession], prefs: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(prefs or {})
        learned_interests = self._infer_learned_interests(session)
        if learned_interests:
            merged["learned_interests"] = learned_interests
        learned_feature_weights = self._get_personalized_feature_weights(session)
        if learned_feature_weights:
            merged["learned_feature_weights"] = learned_feature_weights
        adaptive_criteria_weights = self._get_adaptive_criteria_weights(session)
        if adaptive_criteria_weights:
            merged["adaptive_criteria_weights"] = adaptive_criteria_weights
        style_profile = self._get_user_style_profile(session)
        if style_profile:
            merged["user_style_profile"] = style_profile
            merged["dominant_style"] = style_profile.get("dominant_style")
        active_hypotheses = self._get_active_hypotheses(session)
        if active_hypotheses:
            merged["active_hypotheses"] = active_hypotheses
        hypothesis_recommendations = self._get_hypothesis_recommendations(session)
        if hypothesis_recommendations:
            merged["hypothesis_recommendations"] = hypothesis_recommendations
        merged["interests"] = _merge_unique_list(
            merged.get("interests"),
            learned_interests,
        )
        return self._normalize_preferences(merged)

    async def _record_style_query_interaction(
        self,
        session: Optional[ChatSession],
        user_message: str,
    ) -> None:
        if not session or not session.user_id or not self.config.learning_enabled:
            return

        prefs = dict(self._preferences or session.extracted_preferences or {})
        if not prefs:
            return

        destination = None
        destinations = prefs.get("destinations") or []
        if destinations:
            destination = str(destinations[0] or "").strip() or None

        try:
            profile = await get_user_style_classifier().record_interaction(
                user_id=session.user_id,
                user_message=user_message,
                preferences=prefs,
                interaction_type="query",
                destination=destination,
                accepted=None,
            )
        except Exception as exc:
            logger.debug(f"Style query recording unavailable for {session.user_id}: {exc}")
            return

        if isinstance(profile, dict):
            self._preferences["user_style_profile"] = profile
            self._preferences["dominant_style"] = profile.get("dominant_style")
            session.extracted_preferences = dict(self._preferences)
            session.planning_data["user_style_profile"] = profile

    def _destination_focus_tags(self, destination: str) -> List[str]:
        return list(_DESTINATION_TAGS_BY_NAME.get(str(destination or "").strip().lower(), []))

    def _pick_exploration_destination(
        self,
        destinations: List[str],
        prefs: Dict[str, Any],
        user_id: Optional[str],
    ) -> Optional[str]:
        try:
            from app.utils.learning_agent import get_learner

            learner = get_learner()
        except Exception:
            learner = None

        existing = {str(destination or "").strip().lower() for destination in destinations}
        current_tags = set()
        for destination in destinations:
            current_tags.update(self._destination_focus_tags(destination))

        scored_candidates: List[tuple[float, str]] = []
        for entry in POPULAR_DESTINATIONS:
            name = str(entry.get("name") or "").strip()
            if not name or name.lower() in existing:
                continue

            tags = {
                str(tag).strip().lower()
                for tag in (entry.get("focus_tags") or [])
                if str(tag).strip()
            }
            overlap = len(tags & current_tags)
            union_size = max(1, len(tags | current_tags))
            diversity = 1.0 if current_tags and overlap == 0 else max(0.1, 1.0 - (overlap / union_size))
            prediction = (
                learner.predict_acceptance(
                    name,
                    user_id=user_id,
                    candidate_features=list(tags),
                    preferences=prefs,
                )
                if learner
                else {"predicted_acceptance": 0.5}
            )
            score = (diversity * 0.65) + (float(prediction.get("predicted_acceptance", 0.5)) * 0.35)
            scored_candidates.append((round(score, 3), name))

        if not scored_candidates:
            return None

        scored_candidates.sort(reverse=True)
        return scored_candidates[0][1]

    # ── Phase 3 (epsilon-greedy): wildcard injection ─────────────────────────

    def _maybe_inject_wildcard(
        self,
        destinations: List[str],
        prefs: Dict[str, Any],
        user_id: Optional[str],
    ) -> Optional[str]:
        """Epsilon-greedy wildcard: occasionally inject an unseen destination.

        Epsilon starts at 15% and decays toward 5% as session history grows
        (min 5%).  A wildcard is only injected when the random draw is below
        epsilon.  The selected destination:
          - is NOT in the user's seen / current destinations
          - matches at least one user interest tag
          - is marked as "is_wildcard" in the metadata caller adds.

        Returns the wildcard destination name, or None if no injection occurs.
        """
        meta = get_meta_learner()
        meta._ensure_loaded()
        n_sessions = len(meta.performance_history)

        # Decay: epsilon = max(0.05, 0.15 - 0.01 * floor(n_sessions / 10))
        epsilon = max(0.05, 0.15 - 0.01 * (n_sessions // 10))

        if random.random() >= epsilon:
            return None

        # Build set of destinations already seen/queued
        existing = {str(d or "").strip().lower() for d in destinations}

        # Pull seen_destinations from user profile if available
        seen_dests: set = set()
        if user_id and self.config.learning_enabled:
            try:
                from app.utils.learning_agent import get_learner
                profile = get_learner().get_user_profile(user_id) or {}
                for interaction in (profile.get("interactions") or []):
                    dest = str(interaction.get("destination") or "").strip().lower()
                    if dest:
                        seen_dests.add(dest)
            except Exception:
                pass

        excluded = existing | seen_dests
        user_interests = {str(i).strip().lower() for i in (prefs.get("interests") or []) if i}

        candidates: List[tuple] = []
        for entry in POPULAR_DESTINATIONS:
            name = str(entry.get("name") or "").strip()
            if not name or name.lower() in excluded:
                continue
            tags = {str(t).strip().lower() for t in (entry.get("focus_tags") or []) if t}
            # Require at least one interest match (or accept any if no interests set)
            if user_interests and not (tags & user_interests):
                continue
            # Use meta-learner acceptance prediction for ranking
            score = meta.predict_acceptance(name, prefs=prefs, user_id=user_id)
            candidates.append((score, name))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        # Pick from top-5 randomly to add diversity even within good candidates
        top = candidates[:5]
        return random.choice(top)[1]

    # ─────────────────────────────────────────────────────────────────────────

    def _plan_destination_research(
        self,
        destinations: List[str],
        prefs: Dict[str, Any],
    ) -> Dict[str, Any]:
        planned_destinations = list(dict.fromkeys(destinations or []))[: self.config.max_destinations]
        prediction_map: Dict[str, Dict[str, Any]] = {}
        depth_map: Dict[str, str] = {}
        knowledge_confidence: Dict[str, float] = {}
        user_id = (
            (self.current_session.user_id if self.current_session else None)
            or prefs.get("user_id")
        )

        learner = None
        if self.config.learning_enabled:
            try:
                from app.utils.learning_agent import get_learner

                learner = get_learner()
            except Exception as exc:
                logger.debug(f"Acceptance prediction unavailable: {exc}")

        for destination in planned_destinations:
            if learner:
                prediction_map[destination] = learner.predict_acceptance(
                    destination,
                    user_id=user_id,
                    candidate_features=self._destination_focus_tags(destination),
                    preferences=prefs,
                )
            else:
                prediction_map[destination] = {
                    "destination": destination,
                    "predicted_acceptance": 0.5,
                    "confidence": 0.3,
                    "destination_features": self._destination_focus_tags(destination),
                }

        exploration_destination = None
        if (
            prefs.get("destination_source") == "autonomous_discovery"
            and planned_destinations
            and random.random() < 0.10
        ):
            exploration_destination = self._pick_exploration_destination(
                planned_destinations,
                prefs,
                user_id,
            )
            if exploration_destination and exploration_destination not in planned_destinations:
                if len(planned_destinations) >= self.config.max_destinations:
                    removed_destination = planned_destinations[-1]
                    planned_destinations[-1] = exploration_destination
                    prediction_map.pop(removed_destination, None)
                else:
                    planned_destinations.append(exploration_destination)
                if learner:
                    prediction_map[exploration_destination] = learner.predict_acceptance(
                        exploration_destination,
                        user_id=user_id,
                        candidate_features=self._destination_focus_tags(exploration_destination),
                        preferences=prefs,
                    )
                else:
                    prediction_map[exploration_destination] = {
                        "destination": exploration_destination,
                        "predicted_acceptance": 0.45,
                        "confidence": 0.25,
                        "destination_features": self._destination_focus_tags(exploration_destination),
                    }
                prediction_map[exploration_destination]["exploration_candidate"] = True

        # ── Phase 3 (epsilon-greedy): wildcard injection ──────────────────
        wildcard_destination = None
        if not exploration_destination:
            wildcard_destination = self._maybe_inject_wildcard(planned_destinations, prefs, user_id)
        if wildcard_destination and wildcard_destination not in planned_destinations:
            if len(planned_destinations) >= self.config.max_destinations:
                # Replace the last destination with the wildcard
                removed_wildcard = planned_destinations[-1]
                planned_destinations[-1] = wildcard_destination
                prediction_map.pop(removed_wildcard, None)
                logger.info(f"Epsilon-greedy wildcard: replaced {removed_wildcard!r} with {wildcard_destination!r}")
            else:
                planned_destinations.append(wildcard_destination)
                logger.info(f"Epsilon-greedy wildcard: injected {wildcard_destination!r}")
            meta_acceptance = get_meta_learner().predict_acceptance(
                wildcard_destination, prefs=prefs, user_id=user_id
            )
            prediction_map[wildcard_destination] = {
                "destination": wildcard_destination,
                "predicted_acceptance": meta_acceptance,
                "confidence": 0.3,
                "destination_features": self._destination_focus_tags(wildcard_destination),
                "is_wildcard": True,
            }

        # ── Phase 2: rank planned_destinations by predicted acceptance ────
        try:
            planned_destinations = get_meta_learner().rank_candidates(
                planned_destinations, prefs=prefs, user_id=user_id
            )
        except Exception as _rank_exc:
            logger.debug(f"MetaLearner.rank_candidates failed (non-fatal): {_rank_exc}")

        # Blend MetaLearner rank with UserLearner prediction_map into single score
        if prediction_map:
            meta_order = {d: i for i, d in enumerate(planned_destinations)}
            n = max(len(planned_destinations), 1)
            planned_destinations = sorted(
                planned_destinations,
                key=lambda d: (
                    0.6 * (1 - meta_order.get(d, n) / n) +
                    0.4 * float(prediction_map.get(d, {}).get("predicted_acceptance", 0.5))
                ),
                reverse=True,
            )

        kb = get_knowledge_base()
        _meta = get_meta_learner()
        for destination in planned_destinations:
            snapshot = kb.get_destination_knowledge(destination) or {}
            confidence = float(snapshot.get("confidence", 0.0) or 0.0)
            needs_refresh = bool(snapshot.get("needs_refresh", True))
            predicted_acceptance = float(
                (prediction_map.get(destination) or {}).get("predicted_acceptance", 0.5) or 0.5
            )
            knowledge_confidence[destination] = round(confidence, 2)

            # ── Phase 3: per-destination depth tuning (KB confidence + acceptance) ──
            # Override with meta-learner's acceptance prediction for better signal
            meta_acceptance = _meta.predict_acceptance(destination, prefs=prefs, user_id=user_id)
            # Use the higher of the two signals (learner vs meta)
            effective_acceptance = max(predicted_acceptance, meta_acceptance)

            depth = self.config.research_depth.value
            if confidence >= 0.80 and not needs_refresh:
                # We know this destination well — quick lookup suffices
                depth = ResearchDepth.QUICK.value
            elif effective_acceptance < 0.30:
                # Low acceptance likelihood — not worth deep research
                depth = ResearchDepth.QUICK.value
            elif effective_acceptance >= 0.70 and confidence >= 0.50:
                # High interest + decent knowledge — go deep
                depth = ResearchDepth.DEEP.value
            elif confidence >= 0.72 and effective_acceptance >= 0.70 and not needs_refresh:
                depth = ResearchDepth.QUICK.value
            elif needs_refresh or confidence < 0.45 or 0.40 <= effective_acceptance <= 0.65:
                depth = ResearchDepth.DEEP.value
            elif self.config.research_depth == ResearchDepth.DEEP:
                depth = ResearchDepth.DEEP.value
            elif self.config.research_depth == ResearchDepth.QUICK:
                depth = ResearchDepth.QUICK.value
            else:
                depth = ResearchDepth.STANDARD.value

            depth_map[destination] = depth

        return {
            "destinations": planned_destinations,
            "prediction_map": prediction_map,
            "destination_depth_map": depth_map,
            "knowledge_confidence": knowledge_confidence,
            "exploration_destination": exploration_destination,
            "exploration_applied": bool(
                exploration_destination and exploration_destination in planned_destinations
            ),
            "wildcard_destination": wildcard_destination,
            "wildcard_applied": bool(
                wildcard_destination and wildcard_destination in planned_destinations
            ),
        }

    def _fallback_queries_for_task(self, task_type: str, destination: str) -> List[str]:
        year = date.today().year
        mapping = {
            "flights": [f"{destination} flight prices {year}", f"best airports for {destination}"],
            "hotels": [f"best neighborhoods to stay in {destination}", f"{destination} hotel guide {year}"],
            "events": [f"{destination} events {year}", f"{destination} festival calendar"],
            "visa": [f"{destination} visa requirements {year}", f"entry rules for {destination}"],
            "attractions": [f"best things to do in {destination}", f"{destination} top attractions"],
            "weather": [f"{destination} weather by month", f"best time to visit {destination}"],
        }
        return mapping.get(task_type, [])

    async def _apply_pending_reactions(
        self,
        pending_tasks: List[ResearchTask],
        completed_count: int,
        total: int,
    ) -> None:
        """Consume ``pending_reactions`` stored by the real-time reaction endpoint.

        For each **negative** reaction on a destination, cancel all remaining
        pending tasks for that destination.  For **positive** reactions, boost
        remaining tasks by one priority step so they run sooner.

        Reactions are consumed (deleted from session) once processed so the
        same reaction is never applied twice.
        """
        session = self.current_session
        if not session:
            return
        reactions = session.planning_data.get("pending_reactions")
        if not reactions:
            return

        # Consume all pending reactions
        session.planning_data["pending_reactions"] = []

        _negated_dests: set = set()

        for reaction in reactions:
            dest = reaction.get("destination", "").lower()
            sentiment = reaction.get("sentiment")
            if not dest or not sentiment:
                continue

            for task in pending_tasks:
                if task.status != "pending":
                    continue
                if (task.destination or "").lower() != dest:
                    continue

                if sentiment == "negative":
                    task.status = "cancelled"
                    self._run_metrics["cancelled_tasks"] = int(
                        self._run_metrics.get("cancelled_tasks") or 0
                    ) + 1
                    if task not in self.completed_tasks:
                        self.completed_tasks.append(task)
                    _negated_dests.add(dest)
                    logger.info(
                        f"Reaction: cancelled task {task.id} "
                        f"(user disliked {dest})"
                    )
                elif sentiment == "positive":
                    task.priority = self._boost_priority(task.priority, steps=1)
                    logger.info(
                        f"Reaction: boosted task {task.id} "
                        f"(user likes {dest}) → {task.priority.value}"
                    )

        # Redistribute freed capacity: boost remaining destinations' tasks
        # when a destination was negatively reacted to.
        if _negated_dests:
            for task in pending_tasks:
                if task.status != "pending":
                    continue
                if (task.destination or "").lower() in _negated_dests:
                    continue
                # Boost by one step so surviving destinations get researched sooner
                task.priority = self._boost_priority(task.priority, steps=1)
            logger.info(
                f"Reaction: redistributed capacity from {_negated_dests} "
                f"to remaining destinations"
            )

        # ── Persist reactions to the learning system ────────────────────
        # So future sessions know this user liked/disliked these destinations.
        user_id = session.user_id
        if user_id and self.config.learning_enabled:
            try:
                from app.utils.learning_agent import get_learner
                _learner = get_learner()
                for reaction in reactions:
                    dest = reaction.get("destination", "").strip()
                    sentiment = reaction.get("sentiment")
                    if not dest or not sentiment:
                        continue
                    _learner.learn_from_interaction(
                        user_id=user_id,
                        interaction_type="dislike" if sentiment == "negative" else "like",
                        destination=dest,
                        accepted=sentiment == "positive",
                        feedback_data={
                            "features": list(self._preferences.get("interests", [])),
                            "weight": 0.5,  # strong signal — explicit mid-research reaction
                            "source": "live_reaction",
                        },
                    )
                logger.info(
                    f"Persisted {len(reactions)} live reaction(s) to learning system"
                )
            except Exception as _learn_exc:
                logger.debug(f"Live reaction learning failed (non-fatal): {_learn_exc}")

        # Persist updated session
        try:
            await self.chat_service._save_session(session)
        except Exception:
            pass

    def _strategy_name(self, prefs: Dict[str, Any]) -> str:
        if prefs.get("destination_source") == "autonomous_discovery":
            return "destination_discovery"
        if not prefs.get("travel_dates"):
            return "date_flexible"
        if prefs.get("learned_interests"):
            return "personalized_priority"
        return "default"

    def _set_preference_confidence(self, session: ChatSession, prefs: Dict[str, Any]) -> None:
        confidence = dict(session.planning_data.get("preference_confidence") or {})
        defaults = {
            "destinations": 0.95,
            "travel_dates": 0.9,
            "origin": 0.9,
            "duration": 0.9,
            "budget_level": 0.85,
            "budget_amount": 0.85,
            "interests": 0.9,
            "traveling_with": 0.9,
            "passport_country": 0.9,
            "dietary_restrictions": 0.9,
        }
        for key, default in defaults.items():
            if key in prefs and confidence.get(key) is None:
                confidence[key] = default
        if confidence:
            session.planning_data["preference_confidence"] = confidence

    def _initialize_research_metrics(self, total_tasks: int) -> None:
        self._research_started_at = datetime.now()
        self._run_metrics = {
            "total_tasks": total_tasks,
            "prefetched_tasks": 0,
            "runtime_cache_hits": 0,
            "live_completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
        }

    def _research_metrics_snapshot(self) -> Dict[str, Any]:
        total_tasks = int(self._run_metrics.get("total_tasks") or len(self.research_tasks) or 0)
        prefetched = int(self._run_metrics.get("prefetched_tasks") or 0)
        runtime_cache_hits = int(self._run_metrics.get("runtime_cache_hits") or 0)
        failed_tasks = int(self._run_metrics.get("failed_tasks") or 0)
        cancelled_tasks = int(self._run_metrics.get("cancelled_tasks") or 0)
        live_completed = int(self._run_metrics.get("live_completed_tasks") or 0)
        cache_hits = prefetched + runtime_cache_hits
        completed_tasks = min(total_tasks, cache_hits + live_completed)
        live_tasks_remaining = max(0, total_tasks - cache_hits - live_completed - failed_tasks - cancelled_tasks)
        elapsed_ms = 0
        if self._research_started_at:
            elapsed_ms = max(0, int((datetime.now() - self._research_started_at).total_seconds() * 1000))

        return {
            "total_tasks": total_tasks,
            "prefetched_tasks": prefetched,
            "runtime_cache_hits": runtime_cache_hits,
            "cache_hits": cache_hits,
            "cache_hit_rate": round((cache_hits / total_tasks), 2) if total_tasks else 0.0,
            "live_completed_tasks": live_completed,
            "live_execution_rate": round((live_completed / total_tasks), 2) if total_tasks else 0.0,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "cancelled_tasks": cancelled_tasks,
            "live_tasks_remaining": live_tasks_remaining,
            "elapsed_ms": elapsed_ms,
        }

    async def _emit_partial_plan_event(
        self,
        task: ResearchTask,
        completed_count: int,
    ) -> Optional[Dict[str, Any]]:
        if not self.research_results:
            return None
        partial_plan = await self._synthesize_plan(self.current_session, partial=True)
        partial_plan["completed_tasks"] = completed_count
        partial_plan["total_tasks"] = len(self.research_tasks)
        partial_plan["research_metrics"] = self._research_metrics_snapshot()
        await self._persist_runtime_state(plan=partial_plan)
        return {
            "type": "partial_plan",
            "plan": partial_plan,
            "progress": int(self.progress_percentage),
            "updated_destination": task.destination,
            "updated_section": task.type,
            "message": f"Updated {task.destination} with {task.type.replace('_', ' ')} research.",
        }

    def _can_prefetch_from_knowledge(self, task: ResearchTask) -> bool:
        # visa/transport/safety are fast KB lookups — prefetch them too
        return task.type in {"weather", "attractions", "flights", "hotels", "visa", "transport", "safety"}

    async def _preload_cached_tasks(self, tasks: List[ResearchTask]) -> List[ResearchTask]:
        prefetched: List[ResearchTask] = []
        for task in tasks:
            if not self._can_prefetch_from_knowledge(task):
                continue
            cached = await self._check_knowledge_cache(task)
            if not cached:
                continue
            task.result = cached
            task.status = "completed"
            self.research_results[task.id] = cached
            if task not in self.completed_tasks:
                self.completed_tasks.append(task)
            prefetched.append(task)
        return prefetched

    def _is_cancel_requested(self) -> bool:
        return bool(self._execution_control and self._execution_control.cancel_event.is_set())

    async def _build_cancelled_plan(self) -> Optional[Dict[str, Any]]:
        session = self.current_session
        if not session:
            return None

        runtime_plan = (session.planning_data.get("autonomous_runtime") or {}).get("plan")
        if isinstance(runtime_plan, dict):
            runtime_plan = dict(runtime_plan)
            runtime_plan["is_partial"] = True
            runtime_plan["research_metrics"] = self._research_metrics_snapshot()
            return runtime_plan

        if not self.research_results:
            return None

        partial_plan = await self._synthesize_plan(session, partial=True)
        partial_plan["completed_tasks"] = sum(
            1 for task in self.completed_tasks if task.status == "completed"
        )
        partial_plan["total_tasks"] = len(self.research_tasks)
        partial_plan["research_metrics"] = self._research_metrics_snapshot()
        return partial_plan

    async def _handle_cancellation(self) -> Dict[str, Any]:
        self.state = AgentState.CANCELLED
        self.current_task = None
        cancelled_now = 0

        for task in self.research_tasks:
            if task.status in {"pending", "in_progress"}:
                task.status = "cancelled"
                cancelled_now += 1
                if task not in self.completed_tasks:
                    self.completed_tasks.append(task)

        if cancelled_now:
            self._run_metrics["cancelled_tasks"] = int(self._run_metrics.get("cancelled_tasks") or 0) + cancelled_now

        cancelled_plan = await self._build_cancelled_plan()
        await self._persist_runtime_state(plan=cancelled_plan)
        return {
            "type": "cancelled",
            "state": self.state.value,
            "progress": int(self.progress_percentage),
            "message": "Research cancelled. Keeping the findings gathered so far.",
            "plan": cancelled_plan,
            "research_metrics": self._research_metrics_snapshot(),
        }

    async def _run_task_worker(
        self,
        task: ResearchTask,
        queue: "asyncio.Queue[Dict[str, Any]]",
        semaphore: asyncio.Semaphore,
    ) -> None:
        worker_task = asyncio.current_task()
        control = self._execution_control
        if control and worker_task:
            control.running_tasks.add(worker_task)

        try:
            if control and control.cancel_event.is_set():
                queue.put_nowait({"task": task, "kind": "task_cancelled"})
                return

            async with semaphore:
                if control and control.cancel_event.is_set():
                    queue.put_nowait({"task": task, "kind": "task_cancelled"})
                    return

                cached = await self._check_knowledge_cache(task)
                if cached:
                    await queue.put({"task": task, "kind": "knowledge_cache_hit", "result": cached})
                    return

                # ── Error pattern pre-check ──────────────────────
                # If this task_type+destination has failed repeatedly,
                # skip it or swap to the recommended fallback.
                try:
                    _epl = get_error_pattern_learner()
                    _profile = _epl.get_failure_profile(
                        task_type=task.type,
                        destination=task.destination,
                    )
                    if _profile.get("high_risk"):
                        _fallback = _profile.get("recommended_fallback")
                        if _fallback and _fallback != task.type:
                            logger.info(
                                f"ErrorPattern: swapping {task.type} → {_fallback} "
                                f"for {task.destination} (high_risk, "
                                f"{_profile.get('task_failures', 0)} prior failures)"
                            )
                            task.type = _fallback
                        elif not _fallback:
                            # No fallback available — skip entirely
                            logger.info(
                                f"ErrorPattern: skipping {task.type} for "
                                f"{task.destination} (high_risk, no fallback)"
                            )
                            await queue.put({
                                "task": task,
                                "kind": "task_skipped",
                                "reason": "high_risk_error_pattern",
                            })
                            return
                except Exception:
                    pass  # Non-fatal — proceed normally
                # ─────────────────────────────────────────────────

                result = await self._execute(task)
                await queue.put({"task": task, "kind": "task_completed", "result": result})
        except asyncio.CancelledError:
            queue.put_nowait({"task": task, "kind": "task_cancelled"})
        except Exception as exc:
            await queue.put({"task": task, "kind": "task_failed", "error": str(exc)})
        finally:
            if control and worker_task:
                control.running_tasks.discard(worker_task)

    async def _run_task_batch(
        self,
        tasks: List[ResearchTask],
        queue: "asyncio.Queue[Dict[str, Any]]",
        semaphore: asyncio.Semaphore,
    ) -> None:
        if self._execution_control and self._execution_control.cancel_event.is_set():
            for task in tasks:
                queue.put_nowait({"task": task, "kind": "task_cancelled"})
            return
        await asyncio.gather(*(self._run_task_worker(task, queue, semaphore) for task in tasks))

    # ── LLM preference extraction ─────────────────────────────────────────────

    async def _llm_extract_preferences(self, user_message: str) -> Dict[str, Any]:
        """Use LLM to extract structured travel preferences from natural language.

        Falls back to empty dict on any error so the regex path is never blocked.
        The LLM fills gaps that regex misses (e.g. "honeymoon" → couple, luxury).
        """
        import asyncio as _asyncio
        try:
            from app.services.ai_providers import AIFactory
            provider = AIFactory.create_from_settings()
            if not provider:
                return {}

            prompt = (
                "Extract travel preferences from this user message as JSON.\n"
                "Possible fields (include only those you can confidently extract):\n"
                "  destinations (list of city/place names),\n"
                "  travel_dates (string like 'June 2026'),\n"
                "  origin (departure city),\n"
                "  duration (string like '7 days'),\n"
                "  budget_level (one of: budget, moderate, luxury),\n"
                "  traveling_with (one of: solo, couple, family, friends),\n"
                "  interests (list from: beaches, culture, food, adventure, nightlife,\n"
                "             nature, shopping, history, relaxation, photography).\n\n"
                "Return ONLY raw JSON, no markdown fences, no explanation.\n\n"
                f'Message: "{user_message}"'
            )

            raw = await _asyncio.wait_for(provider.generate(prompt), timeout=8.0)
            if not raw:
                return {}
            # Strip markdown code fences if LLM wraps output
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            result = json.loads(cleaned)
            if isinstance(result, dict):
                logger.info("LLM preference extraction succeeded", fields=list(result.keys()))
                return result
            return {}
        except Exception as exc:
            logger.debug(f"LLM preference extraction failed (non-fatal): {exc}")
            return {}

    # ── Phase 4: session continuity helper ───────────────────────────────────

    def _is_new_trip_intent(self, message: str, current_prefs: Dict[str, Any]) -> bool:
        """Return True when *message* signals a new destination the agent hasn't
        researched yet — so we should reset state rather than merge.

        Checks:
        1. Explicit new-trip signal phrases (e.g. "start over", "forget bali").
        2. A recognized destination in the message that is NOT already in
           current_prefs["destinations"].
        """
        lower = message.lower()

        # 1. Hard-coded reset phrases
        if any(signal in lower for signal in _NEW_TRIP_SIGNALS):
            return True

        # 2. A broad region keyword → always treat as new trip context so the
        #    agent clears the old destination and asks for a city in the region.
        for _region_kw in _REGION_KEYWORDS.values():
            if any(kw in lower for kw in _region_kw):
                return True

        # 3. A specific destination that differs from current ones
        current_dests_lower = {str(d).strip().lower() for d in (current_prefs.get("destinations") or [])}
        if not current_dests_lower:
            return False  # no previous destination — nothing to reset

        # Check aliases
        for alias, canonical in _DEST_ALIASES.items():
            if re.search(r"\b" + re.escape(alias) + r"\b", lower):
                if canonical.strip().lower() not in current_dests_lower:
                    return True
        # Check known destination map
        for key, rec in _DEST_MAP.items():
            if len(key) >= 4 and re.search(r"\b" + re.escape(key) + r"\b", lower):
                if key not in current_dests_lower and str(rec.get("name") or "").strip().lower() not in current_dests_lower:
                    return True
        # Check extra coords
        for key in _EXTRA_COORDS:
            if len(key) >= 4 and re.search(r"\b" + re.escape(key) + r"\b", lower):
                if key not in current_dests_lower and key.title().lower() not in current_dests_lower:
                    return True

        return False

    # ── Public API ────────────────────────────────────────────────────────────

    async def start_conversation(
        self,
        session_id: str,
        user_message: str,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Main entry point — yields SSE events for the streaming endpoint.

        On a follow-up message (same session, already has preferences) the new
        message is merged into existing preferences so the user can say things
        like "actually make it 3 weeks" without losing previous context.
        """

        session: Optional[ChatSession] = None
        self._execution_control = _start_execution(session_id)

        try:
            # Reset research pipeline but preserve any existing prefs for merging
            self.state = AgentState.LISTENING
            self.current_task = None
            self.completed_tasks = []
            self.research_tasks = []
            self.research_results = {}
            self.progress_percentage = 0.0
            self._partial_results_sent = False
            self._research_started_at = None
            self._run_metrics = {}

            # Load or create session
            session = await self.chat_service._load_session(session_id)
            is_followup = bool(
                session and session.extracted_preferences and
                session.extracted_preferences.get("destinations")
            )

            # ── Phase 4: session continuity — detect new-trip intent ──────────
            # If the session previously reached a completed/presenting state AND
            # the user now asks about a different destination, reset cleanly so
            # the agent treats this as a fresh trip rather than a follow-up.
            if session and is_followup:
                _prev_runtime_state = (
                    (session.planning_data.get("autonomous_runtime") or {}).get("state", "")
                )
                _is_terminal = _prev_runtime_state in {
                    AgentState.COMPLETED.value,
                    AgentState.PRESENTING.value,
                    AgentState.CANCELLED.value,
                }
                _current_session_prefs = session.extracted_preferences or {}
                if _is_terminal and self._is_new_trip_intent(user_message, _current_session_prefs):
                    logger.info(
                        f"New trip intent detected for session {session_id} "
                        f"(was {_prev_runtime_state!r}); resetting agent state."
                    )
                    # Clear destination-specific prefs but keep personal prefs
                    _reset_keys = {"destinations", "region_intent", "destination_source",
                                   "destination_prediction_map", "destination_depth_map",
                                   "destination_knowledge_confidence", "exploration_destination",
                                   "exploration_applied", "wildcard_destination", "wildcard_applied"}
                    for _k in _reset_keys:
                        session.extracted_preferences.pop(_k, None)
                    session.planning_data.pop("autonomous_runtime", None)
                    session.planning_data.pop("destination_research_plan", None)
                    session.planning_data.pop("destination_discovery", None)
                    is_followup = False
            # ─────────────────────────────────────────────────────────────────

            if not session:
                session = ChatSession(session_id=session_id, user_id=user_id)
            await self._hydrate_session_memory(session, user_id)
            self.current_session = session
            session.messages.append(
                ChatMessage(role="user", content=user_message, timestamp=datetime.now())
            )

            yield {
                "type": "status", "state": "listening",
                "message": (
                    "Got it! Updating your trip details..." if is_followup
                    else "Got it! Let me understand your travel needs..."
                ),
            }

            # Preference extraction — always merge on top of existing prefs
            self.state = AgentState.PLANNING
            base_prefs = self._merge_preferences_with_memory(session)
            extracted = self.interpreter.extract_preferences_heuristic(user_message, session)
            # Merge: existing prefs → interpreter output → our regex (later overrides earlier)
            merged = _extract_preferences(user_message, {**base_prefs, **extracted})

            # LLM-powered extraction fills gaps regex missed (e.g. "honeymoon" → couple)
            llm_prefs = self._normalize_preferences(await self._llm_extract_preferences(user_message))
            for key, value in llm_prefs.items():
                if value and (key not in merged or not merged[key]):
                    merged[key] = value

            merged = self._normalize_preferences(merged)
            self.interpreter.merge_extracted_preferences(session, merged)
            self._set_preference_confidence(session, merged)
            self._preferences = self._apply_learning_bias(
                session,
                self._merge_preferences_with_memory(session),
            )
            session.extracted_preferences = dict(self._preferences)
            await self.chat_service.memory.persist_session_preferences(session)
            await self._persist_runtime_state()
            await self._record_style_query_interaction(session, user_message)

            # ── Inject learned interests + emit personalized welcome ─────────
            if user_id:
                try:
                    from app.utils.learning_agent import get_learner
                    _learner = get_learner()
                    prior_profile = _learner.get_user_profile(user_id)
                    if prior_profile:
                        prior_prefs = prior_profile.get("preferences", {})
                        learned_interests = (
                            prior_prefs.get("preferred_features")
                            or prior_prefs.get("accepted_features")
                            or []
                        )
                        if learned_interests and not self._preferences.get("interests"):
                            self._preferences.setdefault("learned_interests", learned_interests[:5])
                        preferred_dests = prior_prefs.get("preferred_destinations")
                        if preferred_dests and not self._preferences.get("destinations"):
                            if isinstance(preferred_dests, str):
                                preferred_dests = [preferred_dests]
                            self._preferences["prior_preferred_destinations"] = preferred_dests[:3]
                        # Emit personalized acknowledgement if we know their interests
                        if learned_interests:
                            top = ", ".join(str(i).replace("_", " ") for i in learned_interests[:3])
                            yield {
                                "type": "status",
                                "state": "planning",
                                "message": f"Welcome back! Based on your previous trips I know you enjoy **{top}** — I'll prioritise those in my research.",
                                "personalized": True,
                            }
                except Exception:
                    pass
            # ─────────────────────────────────────────────────────────────────

            # ── Region intent without a specific city ────────────────────────
            # The user said "europe" / "asia" etc. but no city was extracted.
            # Ask for clarification rather than researching the old destination.
            region_intent = self._preferences.get("region_intent")
            if region_intent and not self._preferences.get("destinations"):
                self.state = AgentState.LISTENING
                yield {
                    "type": "clarification",
                    "state": "listening",
                    "message": (
                        f"Great — {region_intent} has so many amazing places! "
                        f"Which city or destination in {region_intent} are you thinking of? "
                        f"For example, Paris, Barcelona, Rome, Amsterdam..."
                    ),
                }
                return
            # ─────────────────────────────────────────────────────────────────

            # ── Per-user meta-learner depth/strategy override ────────────────
            # If we have enough session history for this specific user, the
            # meta-learner returns a personalised depth recommendation that
            # overrides the global default set in __init__.
            try:
                _user_recs = get_meta_learner().get_recommendations(
                    user_id=session.user_id or user_id,
                )
                if _user_recs.get("per_user"):
                    _per_user_depth = _user_recs.get("optimal_research_depth")
                    if _per_user_depth:
                        try:
                            self.config.research_depth = ResearchDepth(_per_user_depth)
                            logger.info(
                                f"Per-user meta-learner override: "
                                f"depth={_per_user_depth} for {session.user_id}"
                            )
                        except ValueError:
                            pass
                _best_strategy = _user_recs.get("best_strategy")
                if _best_strategy:
                    self._meta_strategy = _best_strategy
            except Exception:
                pass
            # ─────────────────────────────────────────────────────────────────

            yield {"type": "status", "state": "planning",
                   "message": "Planning research strategy...",
                   "extracted_preferences": self._preferences}

            if _has_min_requirements(self._preferences):
                # Have destination — start research immediately.
                # Emit optional enrichment hints as non-blocking status, then proceed.
                soft_missing = _get_missing_fields(self._preferences)
                soft_missing_names = [m["field"] for m in soft_missing]
                if soft_missing:
                    dests = ", ".join(self._preferences.get("destinations") or [])
                    hint_lines = "".join(f"• {m['question']}\n" for m in soft_missing[:3])
                    yield {
                        "type": "status",
                        "state": "planning",
                        "message": (
                            f"Starting research on **{dests}** now! "
                            f"You can also tell me more details as I work:\n\n{hint_lines}"
                        ),
                        "soft_missing_fields": soft_missing_names,
                    }
                async for event in self._research_loop():
                    yield event
            else:
                # No destination at all — ask for it
                async for event in self._discover_or_ask_destination():
                    yield event

            # Record session for meta-learning.
            # user_accepted starts unlabeled until the feedback endpoint records
            # a real accept/reject signal for this session.
            try:
                meta_learner = get_meta_learner()
                research_completed = self.state in (
                    AgentState.COMPLETED, AgentState.PRESENTING, AgentState.SYNTHESIZING
                )
                runtime_plan = (
                    (self.current_session.planning_data.get("autonomous_runtime") or {}).get("plan")
                    if self.current_session else None
                )
                await meta_learner.record_session_outcome({
                    "session_id": session_id,
                    "user_id": user_id,
                    "research_depth": self.config.research_depth.value,
                    "strategy": self._strategy_name(self._preferences),
                    "task_count": len(self.completed_tasks),
                    "user_accepted": None,
                    "engagement_seconds": (
                        (datetime.now() - self._research_started_at).total_seconds()
                        if self._research_started_at else 0
                    ),
                    "destinations_shown": self._preferences.get("destinations", []),
                    "destination_chosen": None,
                    "decision_context": self._build_decision_feedback_context(runtime_plan),
                    "research_completed": research_completed,
                    "is_exploration": self._is_exploration_session,
                    "exploration_depth": self._exploration_depth,
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.warning(f"Meta-learning recording failed: {e}")

        finally:
            if session is not None:
                try:
                    await self.chat_service._save_session(session)
                except Exception as exc:
                    logger.warning(f"Failed to save autonomous session {session_id}: {exc}")
            _clear_execution(session_id, self._execution_control)
            self._execution_control = None

    # ── Destination discovery (when user hasn't specified a destination) ───────

    async def _discover_or_ask_destination(self) -> AsyncGenerator[Dict[str, Any], None]:
        """When no destination is provided, try to suggest destinations based on
        interests/budget/travel style found in the user message.  Falls back to
        a friendly ask if we can't generate suggestions.
        """
        prefs = self._preferences
        interests = prefs.get("interests") or []
        budget = prefs.get("budget_level", "moderate")
        traveling_with = prefs.get("traveling_with", "solo")
        duration = prefs.get("duration")

        if interests or prefs.get("budget_level") or prefs.get("traveling_with"):
            yield {
                "type": "status",
                "state": "planning",
                "message": "You did not name a destination, so I am discovering a few strong matches first...",
            }
            try:
                discovery = await self.research_agent.discover_destinations(
                    prefs,
                    max_candidates=self.config.max_destinations,
                )
            except Exception as exc:
                logger.warning(f"Destination discovery failed: {exc}")
                discovery = {}

            candidates = [
                str(candidate).strip()
                for candidate in (discovery.get("candidates") or [])
                if str(candidate).strip()
            ][: self.config.max_destinations]
            if candidates:
                self._preferences["destinations"] = candidates
                self._preferences["destination_source"] = "autonomous_discovery"
                if self.current_session:
                    self.current_session.planning_data["destination_discovery"] = {
                        "candidates": candidates,
                        "candidate_evidence": discovery.get("candidate_evidence") or [],
                        "source_summary": discovery.get("source_summary") or {},
                    }
                    self.current_session.extracted_preferences = dict(self._preferences)
                    await self._persist_runtime_state()

                yield {
                    "type": "destination_discovery",
                    "state": "planning",
                    "message": (
                        f"I found a few strong matches for you: {', '.join(candidates)}. "
                        "I’m starting research on the best options now."
                    ),
                    "destinations": candidates,
                    "destination_suggestions": [{"name": c, "reason": ""} for c in candidates],
                    "candidate_evidence": discovery.get("candidate_evidence") or [],
                    "source_summary": discovery.get("source_summary") or {},
                    "extracted_so_far": self._preferences,
                }
                async for event in self._research_loop():
                    yield event
                return

        # Try LLM-based discovery first
        suggestions = await self._llm_suggest_destinations(interests, budget, traveling_with, duration)

        if suggestions:
            lines = "\n".join(
                f"**{i + 1}. {s['name']}** — {s['reason']}"
                for i, s in enumerate(suggestions)
            )
            msg = (
                "I'd love to help you plan the perfect trip! Based on what you've told me, "
                "here are three destinations that could be a great fit:\n\n"
                f"{lines}\n\n"
                "Which one speaks to you? Or tell me a different destination you have in mind!"
            )
            yield {
                "type": "response",
                "state": "waiting_for_input",
                "message": msg,
                "needs_more_info": True,
                "missing_fields": ["destinations"],
                "destination_suggestions": suggestions,
                "extracted_so_far": prefs,
            }
        else:
            yield {
                "type": "response",
                "state": "waiting_for_input",
                "message": (
                    "I'd love to help you plan a trip! To get started, could you tell me:\n\n"
                    "• **Where would you like to go?**\n"
                    "• What kind of experience are you after? (beach, culture, adventure, city…)\n"
                    "• Roughly when, and for how long?\n\n"
                    "The more you share, the better I can tailor everything for you!"
                ),
                "needs_more_info": True,
                "missing_fields": ["destinations"],
                "extracted_so_far": prefs,
            }
        self.state = AgentState.WAITING_FOR_INPUT
        await self._persist_runtime_state()

    async def _llm_suggest_destinations(
        self,
        interests: List[str],
        budget: str,
        traveling_with: str,
        duration: Optional[int],
    ) -> List[Dict[str, str]]:
        """Ask the LLM for 3 destination suggestions given user context."""
        try:
            provider = self.chat_service.ai_provider
            if not provider:
                return []

            interest_str = ", ".join(interests) if interests else "general sightseeing"
            dur_str = f"{duration} days" if duration else "a week or so"
            prompt = (
                f"Suggest exactly 3 travel destinations for a {traveling_with} traveller "
                f"with a {budget} budget, interested in {interest_str}, travelling for {dur_str}. "
                "For each destination give a short (max 15 word) reason why it suits them. "
                "Respond ONLY with valid JSON in this exact format:\n"
                '[{"name": "City, Country", "reason": "..."},'
                ' {"name": "City, Country", "reason": "..."},'
                ' {"name": "City, Country", "reason": "..."}]'
            )

            response = await asyncio.wait_for(
                provider.generate_response(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.7,
                ),
                timeout=10.0,
            )
            text = str(response or "").strip()
            # Extract JSON array from the response
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                if isinstance(parsed, list):
                    return [
                        {"name": str(d.get("name", "")), "reason": str(d.get("reason", ""))}
                        for d in parsed[:3]
                        if d.get("name")
                    ]
        except Exception as exc:
            logger.debug(f"LLM destination suggestion failed: {exc}")
        return []

    # ── Research pipeline ─────────────────────────────────────────────────────

    async def _research_loop(self) -> AsyncGenerator[Dict[str, Any], None]:
        self.state = AgentState.RESEARCHING
        prefs = self._preferences
        planning_context = self._plan_destination_research(
            (prefs.get("destinations") or [])[: self.config.max_destinations],
            prefs,
        )
        destinations = planning_context["destinations"]
        prefs["destinations"] = destinations
        prefs["destination_prediction_map"] = planning_context["prediction_map"]
        prefs["destination_depth_map"] = planning_context["destination_depth_map"]
        prefs["destination_knowledge_confidence"] = planning_context["knowledge_confidence"]
        if planning_context.get("exploration_applied"):
            prefs["exploration_destination"] = planning_context.get("exploration_destination")
            prefs["exploration_applied"] = True
        self._preferences = prefs
        if self.current_session:
            self.current_session.extracted_preferences = dict(self._preferences)
            self.current_session.planning_data["destination_research_plan"] = planning_context

        self.research_tasks = self._create_tasks(destinations, prefs)
        total = len(self.research_tasks)
        self._initialize_research_metrics(total)
        prefetched_tasks = await self._preload_cached_tasks(self.research_tasks)
        self._run_metrics["prefetched_tasks"] = len(prefetched_tasks)
        pending_tasks = [task for task in self.research_tasks if task.status != "completed"]
        completed_count = len(prefetched_tasks)
        self.progress_percentage = (completed_count / total * 100) if total else 0.0
        await self._persist_runtime_state()

        # ── Phase 1 & 5: executive controller + goal tracker ─────────────────
        from app.services.executive_controller import ExecutiveController, classify_error, should_retry, get_retry_delay
        from app.services.goal_tracker import GoalTracker

        executive = ExecutiveController(prefs, destinations)
        goal_tracker = GoalTracker(destinations, prefs)
        error_learner = get_error_pattern_learner()
        _task_retry_counts: Dict[str, int] = {}   # task_id → attempt count
        # ─────────────────────────────────────────────────────────────────────

        yield {
            "type": "research_started",
            "plan": [task.model_dump(mode="json") for task in self.research_tasks],
            "message": f"Starting autonomous research on {', '.join(destinations)}...",
            "destinations": destinations,
            "destination_predictions": planning_context["prediction_map"],
            "destination_depths": planning_context["destination_depth_map"],
            "exploration_destination": planning_context.get("exploration_destination"),
            "total_tasks": total,
            "prefetched_tasks": completed_count,
            "live_tasks": len(pending_tasks),
            "research_metrics": self._research_metrics_snapshot(),
        }

        for index, task in enumerate(prefetched_tasks, start=1):
            yield {
                "type": "knowledge_cache_hit",
                "task": task.model_dump(mode="json"),
                "progress": int(self.progress_percentage),
                "result_summary": self._brief(task),
                "result_preview": _preview(task.result or {}),
                "message": f"Loaded fresh destination knowledge for {task.destination}",
                "prefetched": True,
                "research_metrics": self._research_metrics_snapshot(),
            }
            partial_event = await self._emit_partial_plan_event(task, index)
            if partial_event:
                yield partial_event

        semaphore = asyncio.Semaphore(max(1, int(self.config.max_concurrent_tasks)))

        # Compute priority set dynamically — executive may add tasks between batches
        def _pending_priorities() -> List[int]:
            return sorted({
                _priority_num(t.priority)
                for t in pending_tasks
                if t.status == "pending"
            })  # critical/high -> low

        processed_priorities: set = set()

        while True:
            remaining_prios = [p for p in _pending_priorities() if p not in processed_priorities]
            if not remaining_prios:
                break

            priority_value = remaining_prios[0]
            processed_priorities.add(priority_value)

            if self._is_cancel_requested():
                yield await self._handle_cancellation()
                return

            batch = [
                task
                for task in pending_tasks
                if _priority_num(task.priority) == priority_value and task.status == "pending"
            ]
            if not batch:
                continue
            batch.sort(
                key=lambda task: float(getattr(task, "priority_score", 0.0)),
                reverse=True,
            )

            queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()

            for task in batch:
                self.current_task = task
                task.status = "in_progress"
                yield {
                    "type": "task_started",
                    "task": task.model_dump(mode="json"),
                    "progress": int(completed_count / max(1, total) * 100),
                    "message": self._task_label(task),
                    "queries": task.params.get("queries", []) if task.type == "web_search" else [],
                }

            await self._persist_runtime_state()

            producer = asyncio.create_task(self._run_task_batch(batch, queue, semaphore))

            batch_completed = 0
            while batch_completed < len(batch):
                outcome = await queue.get()
                task = outcome["task"]
                kind = outcome["kind"]
                batch_completed += 1
                completed_count += 1
                self.progress_percentage = completed_count / max(1, total) * 100

                if kind in {"task_completed", "knowledge_cache_hit"}:
                    result = outcome["result"]
                    task.result = result
                    task.status = "completed"
                    self.research_results[task.id] = result
                    self.completed_tasks.append(task)
                    if kind == "knowledge_cache_hit":
                        self._run_metrics["runtime_cache_hits"] = int(self._run_metrics.get("runtime_cache_hits") or 0) + 1
                    else:
                        self._run_metrics["live_completed_tasks"] = int(self._run_metrics.get("live_completed_tasks") or 0) + 1
                    if kind == "task_completed" and self._is_degraded_result(task, result):
                        await error_learner.record_failure(
                            task_type=task.type,
                            destination=task.destination,
                            error_kind="degraded_result",
                            message=str(result.get("summary") or "degraded result"),
                        )

                    # ── Error recovery feedback ─────────────────────────
                    # If this was a compensatory task (spawned by executive
                    # controller because the primary task failed), evaluate
                    # whether the fallback actually helped.
                    if kind == "task_completed" and task.params.get("compensatory"):
                        _is_good = not self._is_degraded_result(task, result)
                        try:
                            if _is_good:
                                # Compensatory web_search worked — record success
                                await error_learner.record_failure(
                                    task_type=f"{task.type}_compensatory",
                                    destination=task.destination or "",
                                    error_kind="recovery_success",
                                    message="Compensatory task provided useful data",
                                )
                                self._run_metrics["successful_recoveries"] = (
                                    int(self._run_metrics.get("successful_recoveries") or 0) + 1
                                )
                            else:
                                await error_learner.record_failure(
                                    task_type=f"{task.type}_compensatory",
                                    destination=task.destination or "",
                                    error_kind="recovery_failed",
                                    message="Compensatory task did not improve data quality",
                                )
                                self._run_metrics["failed_recoveries"] = (
                                    int(self._run_metrics.get("failed_recoveries") or 0) + 1
                                )
                        except Exception:
                            pass
                    # ────────────────────────────────────────────────────

                    yield {
                        "type": kind,
                        "task": task.model_dump(mode="json"),
                        "progress": int(self.progress_percentage),
                        "result_summary": self._brief(task),
                        "result_preview": _preview(result),
                        "research_metrics": self._research_metrics_snapshot(),
                        "message": (
                            f"Found cached knowledge for {task.destination}"
                            if kind == "knowledge_cache_hit"
                            else None
                        ),
                    }
                    partial_event = await self._emit_partial_plan_event(task, completed_count)
                    if partial_event:
                        yield partial_event

                elif kind == "task_cancelled":
                    task.status = "cancelled"
                    self._run_metrics["cancelled_tasks"] = int(self._run_metrics.get("cancelled_tasks") or 0) + 1
                    if task not in self.completed_tasks:
                        self.completed_tasks.append(task)

                elif kind == "task_skipped":
                    task.status = "cancelled"
                    self._run_metrics["skipped_tasks"] = int(self._run_metrics.get("skipped_tasks") or 0) + 1
                    if task not in self.completed_tasks:
                        self.completed_tasks.append(task)
                    yield {
                        "type": "task_skipped",
                        "task": task.model_dump(mode="json"),
                        "progress": int(self.progress_percentage),
                        "reason": outcome.get("reason", "error_pattern"),
                        "message": f"Skipped {task.type} for {task.destination} (learned failure pattern)",
                    }

                else:
                    # ── Phase 4: classified error handling ────────────────────
                    error = outcome["error"]
                    error_kind = classify_error(error)
                    attempt = _task_retry_counts.get(task.id, 0) + 1
                    _task_retry_counts[task.id] = attempt

                    if should_retry(error_kind, attempt):
                        delay = get_retry_delay(error_kind, attempt) or 0
                        logger.info(
                            f"Task {task.id} failed ({error_kind}), "
                            f"retrying in {delay:.1f}s (attempt {attempt})"
                        )
                        task.status = "pending"
                        task.error = None
                        if delay > 0:
                            await asyncio.sleep(delay)
                        # Re-queue: add back to pending at same priority
                        pending_tasks.append(task)
                        processed_priorities.discard(priority_value)
                        completed_count -= 1  # undo the increment
                        batch_completed -= 1  # undo batch count so loop stays correct
                        self.progress_percentage = completed_count / max(1, total) * 100
                        continue
                    # ─────────────────────────────────────────────────────────

                    logger.warning(f"Task {task.id} failed ({error_kind}): {error}")
                    task.status = "failed"
                    task.error = error
                    self._run_metrics["failed_tasks"] = int(self._run_metrics.get("failed_tasks") or 0) + 1
                    self.completed_tasks.append(task)
                    await error_learner.record_failure(
                        task_type=task.type,
                        destination=task.destination,
                        error_kind=error_kind,
                        message=error,
                    )
                    yield {
                        "type": "task_failed",
                        "task": task.model_dump(mode="json"),
                        "progress": int(self.progress_percentage),
                        "error": error,
                        "error_kind": error_kind,
                        "research_metrics": self._research_metrics_snapshot(),
                    }

                await self._persist_runtime_state()

                if self._is_cancel_requested():
                    producer.cancel()
                    await asyncio.gather(producer, return_exceptions=True)
                    yield await self._handle_cancellation()
                    return

            await producer

            # ── Phase 1: executive evaluation after every batch ───────────────
            try:
                eval_result = await executive.evaluate_after_batch(
                    completed_tasks=self.completed_tasks,
                    pending_tasks=pending_tasks,
                    completed_count=completed_count,
                    agent_instance=self,
                )

                # Apply cancellations from executive
                if eval_result.tasks_to_cancel:
                    for pt in pending_tasks:
                        if pt.id in eval_result.tasks_to_cancel and pt.status == "pending":
                            pt.status = "cancelled"
                            self._run_metrics["cancelled_tasks"] = int(self._run_metrics.get("cancelled_tasks") or 0) + 1
                            if pt not in self.completed_tasks:
                                self.completed_tasks.append(pt)

                # Integrate new compensatory tasks
                for new_task in eval_result.new_tasks:
                    pending_tasks.append(new_task)
                    self.research_tasks.append(new_task)
                    total += 1
                    # Ensure its priority gets picked up in the next iteration
                    prio = _priority_num(new_task.priority)
                    if prio in processed_priorities:
                        processed_priorities.discard(prio)

                # Apply fresh preferences (meta-learner drift)
                if eval_result.updated_prefs:
                    self._preferences = eval_result.updated_prefs
                    executive.update_prefs(eval_result.updated_prefs)

                # Stream executive insights as status events
                for insight in eval_result.insights:
                    yield {
                        "type": "executive_insight",
                        "state": "researching",
                        "message": insight,
                        "quality_report": eval_result.quality_report,
                    }
            except Exception as exc:
                logger.warning(f"Executive evaluation failed (non-fatal): {exc}")
            # ─────────────────────────────────────────────────────────────────

            # ── Phase 6: consume real-time reactions from the frontend ────────
            try:
                await self._apply_pending_reactions(pending_tasks, completed_count, total)
            except Exception as exc:
                logger.warning(f"Reaction processing failed (non-fatal): {exc}")
            # ─────────────────────────────────────────────────────────────────

            # ── Phase 5: goal tracker — fill critical gaps ────────────────────
            try:
                progress_summary = goal_tracker.progress_summary(self.completed_tasks)
                if not progress_summary["all_met"]:
                    gap_tasks = goal_tracker.gap_tasks(self.completed_tasks, self)
                    for gap_task in gap_tasks:
                        # Only add if not already covered by a pending or completed task
                        covered = any(
                            t.destination == gap_task.destination and t.type == gap_task.type
                            for t in self.research_tasks
                        )
                        if not covered:
                            pending_tasks.append(gap_task)
                            self.research_tasks.append(gap_task)
                            total += 1
                            prio = _priority_num(gap_task.priority)
                            if prio in processed_priorities:
                                processed_priorities.discard(prio)
                            logger.info(
                                f"GoalTracker: queued gap task "
                                f"{gap_task.type} for {gap_task.destination}"
                            )
                elif progress_summary["all_met"]:
                    # All strategic goals met — stop early
                    yield {
                        "type": "goals_met",
                        "state": "synthesizing",
                        "message": "All research goals achieved. Preparing your plan...",
                        "goal_progress": progress_summary,
                    }
                    break
            except Exception as exc:
                logger.warning(f"Goal tracking failed (non-fatal): {exc}")
            # ─────────────────────────────────────────────────────────────────

            # ── Phase 7: dynamic depth adjustment ───────────────────────────
            # Monitor elapsed time + engagement signals.  If we've been
            # researching for a while with no user engagement, downshift
            # depth to wrap up faster.  Conversely, if the user is actively
            # engaged, maintain or increase depth.
            try:
                _elapsed_s = (datetime.now() - self._research_started_at).total_seconds() if self._research_started_at else 0
                _eng_events = (
                    self.current_session.planning_data.get("engagement_log", [])
                    if self.current_session else []
                )
                _reaction_count = len(
                    self.current_session.planning_data.get("pending_reactions", [])
                    if self.current_session else []
                )
                _user_is_active = len(_eng_events) > 0 or _reaction_count > 0
                _remaining_pending = sum(1 for t in pending_tasks if t.status == "pending")

                if _elapsed_s > 90 and not _user_is_active and _remaining_pending > 3:
                    # User hasn't engaged after 90s — downshift to QUICK
                    if self.config.research_depth != ResearchDepth.QUICK:
                        old_depth = self.config.research_depth
                        self.config.research_depth = ResearchDepth.QUICK
                        # Cancel LOW-priority pending tasks to finish faster
                        _cancelled_count = 0
                        for _pt in pending_tasks:
                            if _pt.status == "pending" and _pt.priority == ResearchPriority.LOW:
                                _pt.status = "cancelled"
                                if _pt not in self.completed_tasks:
                                    self.completed_tasks.append(_pt)
                                _cancelled_count += 1
                        logger.info(
                            f"Dynamic depth: {old_depth.value} → QUICK "
                            f"(no engagement after {_elapsed_s:.0f}s, "
                            f"cancelled {_cancelled_count} low-priority tasks)"
                        )
                        yield {
                            "type": "depth_adjustment",
                            "state": "researching",
                            "message": "Speeding up — focusing on top results for you.",
                            "old_depth": old_depth.value,
                            "new_depth": "quick",
                        }
                elif _elapsed_s > 60 and _user_is_active and self.config.research_depth == ResearchDepth.QUICK:
                    # User IS engaged but we're on QUICK — upgrade to STANDARD
                    self.config.research_depth = ResearchDepth.STANDARD
                    logger.info("Dynamic depth: QUICK → STANDARD (user is actively engaged)")
                    yield {
                        "type": "depth_adjustment",
                        "state": "researching",
                        "message": "You're interested — let me dig deeper on these destinations.",
                        "old_depth": "quick",
                        "new_depth": "standard",
                    }
            except Exception as _depth_exc:
                logger.debug(f"Dynamic depth adjustment failed (non-fatal): {_depth_exc}")
            # ─────────────────────────────────────────────────────────────────

        if self._is_cancel_requested():
            yield await self._handle_cancellation()
            return

        # Synthesise
        self.state = AgentState.SYNTHESIZING
        yield {"type": "status", "state": "synthesizing",
               "message": "Compiling your personalised travel plan..."}

        # Generate proactive alerts
        proactive_alert_payload: List[Dict[str, Any]] = []
        try:
            proactive_agent = get_proactive_agent()
            alerts = await proactive_agent.monitor_and_alert(
                session_id=self.current_session.session_id,
                user_id=self.current_session.user_id,
                preferences=self._preferences,
                research_data=self.research_results
            )

            if alerts:
                proactive_alert_payload = [alert.to_dict() for alert in alerts]
                self.current_session.planning_data["proactive_alerts"] = proactive_alert_payload
                yield {
                    "type": "proactive_alerts",
                    "alerts": proactive_alert_payload,
                    "message": f"Generated {len(alerts)} smart alerts for you!",
                }
        except Exception as e:
            logger.warning(f"Proactive alerts failed: {e}")

        plan = await self._synthesize_plan(self.current_session)
        if proactive_alert_payload:
            plan["proactive_alerts"] = proactive_alert_payload
        await self.chat_service.memory.persist_session_preferences(self.current_session)

        # Feed research results into the knowledge base for future queries
        try:
            learn_result = await self._learn_from_research_results()
            if learn_result.get("destinations_learned"):
                yield {
                    "type": "learning_update",
                    "message": f"Saved knowledge for {', '.join(learn_result['destinations_learned'])}",
                    "destinations_learned": learn_result["destinations_learned"],
                }
        except Exception as exc:
            logger.warning(f"Post-research learning failed: {exc}")

        self.state = AgentState.PRESENTING
        self.progress_percentage = 100.0
        await self._persist_runtime_state(plan=plan)

        yield {
            "type": "plan_presented",
            "plan": plan,
            "progress": 100,
            "research_metrics": self._research_metrics_snapshot(),
            "message": "Your comprehensive travel plan is ready! 🎉",
        }
        self.state = AgentState.COMPLETED
        await self._persist_runtime_state(plan=plan)

    # ── Task builder ──────────────────────────────────────────────────────────

    def _weighted_priority(
        self,
        base: ResearchPriority,
        *feature_names: str,
        feature_weights: Optional[Dict[str, float]] = None,
        interest_boost: bool = False,
    ) -> tuple[ResearchPriority, float]:
        """Return both a discrete priority and a continuous task score.

        The enum priority preserves the existing batch scheduler, while the
        score gives us extra discrimination inside the same priority band.
        """
        base_rank = {
            ResearchPriority.LOW: 1.0,
            ResearchPriority.MEDIUM: 2.0,
            ResearchPriority.HIGH: 3.0,
            ResearchPriority.CRITICAL: 4.0,
        }[base]
        fw = feature_weights or {}
        max_weight = 0.0
        for name in feature_names:
            try:
                max_weight = max(max_weight, float(fw.get(name, 0.0)))
            except (TypeError, ValueError):
                pass

        normalized_weight = min(1.0, max(0.0, max_weight))
        interest_bonus = 0.75 if interest_boost else 0.0
        score_boost = (normalized_weight * 2.1) + interest_bonus
        priority_score = round(base_rank + score_boost, 2)

        if score_boost >= 1.45:
            return self._boost_priority(base, steps=2), priority_score
        if score_boost >= 0.65:
            return self._boost_priority(base, steps=1), priority_score
        return base, priority_score

    def _create_tasks(self, destinations: List[str], prefs: Dict) -> List[ResearchTask]:
        tasks: List[ResearchTask] = []
        tid = 0
        has_travel_dates = bool(prefs.get("travel_dates"))
        interests = _merge_unique_list(
            prefs.get("interests"),
            prefs.get("learned_interests"),
        )
        interest_set = {interest.lower() for interest in interests}
        feature_weights = prefs.get("learned_feature_weights") if isinstance(prefs.get("learned_feature_weights"), dict) else {}
        destination_prediction_map = (
            prefs.get("destination_prediction_map")
            if isinstance(prefs.get("destination_prediction_map"), dict)
            else {}
        )
        destination_depth_map = (
            prefs.get("destination_depth_map")
            if isinstance(prefs.get("destination_depth_map"), dict)
            else {}
        )
        dietary_restrictions = _merge_unique_list(prefs.get("dietary_restrictions"))
        error_learner = get_error_pattern_learner()

        # ── Pre-score destinations with the decision engine ──────────
        # Use any cached knowledge base data to rank destinations BEFORE
        # creating tasks.  Destinations scored higher are researched first
        # because their tasks get a priority boost.
        try:
            de = get_decision_engine()
            dest_pre_scores: Dict[str, float] = {}
            for _d in destinations:
                try:
                    kb_data: Dict[str, Any] = {}
                    try:
                        from app.utils.destination_knowledge_base import get_knowledge_base
                        kb = get_knowledge_base()
                        kb_data = kb.get_destination_knowledge(_d) or {}
                    except Exception:
                        pass
                    ev = de.evaluate_destination(_d, prefs, kb_data)
                    dest_pre_scores[_d] = ev.get("total_score", 0.0)
                except Exception:
                    dest_pre_scores[_d] = 0.0
            # Re-order: highest pre-score first (researched earlier)
            destinations = sorted(
                destinations,
                key=lambda d: dest_pre_scores.get(d, 0.0),
                reverse=True,
            )
        except Exception:
            pass  # decision engine unavailable — keep original order

        def fw(name: str) -> float:
            try:
                return float(feature_weights.get(name, 0.0))
            except (TypeError, ValueError):
                return 0.0

        food_interested = "food" in interest_set or bool(dietary_restrictions)
        attraction_interested = bool(
            interest_set.intersection({"culture", "history", "art", "adventure", "nature", "beach", "photography"})
        )
        event_interested = bool(interest_set.intersection({"nightlife", "family"}))
        hotel_interested = (
            bool(interest_set.intersection({"relaxation", "luxury"}))
            or prefs.get("budget_level") == "luxury"
        )

        # ── Destination success rates ────────────────────────────────
        # Fetch historical acceptance rates so we can deprioritise destinations
        # that previous users (or this user) have consistently rejected.
        dest_success: Dict[str, float] = {}
        try:
            from app.utils.learning_agent import get_learner
            _learner = get_learner()
            for _d in destinations:
                dest_success[_d] = _learner.get_destination_success_rate(_d)
        except Exception:
            pass

        for dest in destinations:
            depth_value = str(destination_depth_map.get(dest) or self.config.research_depth.value)
            try:
                depth = ResearchDepth(depth_value)
            except ValueError:
                depth = self.config.research_depth
                depth_value = depth.value

            destination_prediction = destination_prediction_map.get(dest) or {}
            predicted_acceptance = float(destination_prediction.get("predicted_acceptance", 0.5) or 0.5)
            prediction_confidence = float(destination_prediction.get("confidence", 0.0) or 0.0)
            error_fallback_profiles = {
                task_type: error_learner.get_failure_profile(task_type=task_type, destination=dest)
                for task_type in ("weather", "visa", "attractions", "flights", "hotels", "events", "restaurants")
            }
            fallback_task_types = [
                task_type
                for task_type, profile in error_fallback_profiles.items()
                if profile.get("high_risk")
            ]
            # Destination-level success rate adjustment:
            # - Neutral (0.5 / unknown) → no change
            # - High acceptance (0.8+) → boost score by up to +1.0
            # - Low acceptance (<0.3) → penalise score by up to -1.5
            _sr = dest_success.get(dest, 0.5)
            _acceptance_adj = (predicted_acceptance - 0.5) * 2.4
            _dest_score_adj = round(((_sr - 0.5) * 3.0) + _acceptance_adj, 2)

            def mk(type_: str, priority: ResearchPriority, priority_score: float = 0.0, **params) -> ResearchTask:
                nonlocal tid
                task = ResearchTask(
                    id=f"{type_}_{dest}_{tid}",
                    type=type_,
                    priority=priority,
                    priority_score=round(priority_score + _dest_score_adj, 2),
                    destination=dest,
                    params={
                        **dict(params),
                        "research_depth": depth_value,
                        "predicted_acceptance": round(predicted_acceptance, 2),
                        "prediction_confidence": round(prediction_confidence, 2),
                        "exploration_candidate": bool(destination_prediction.get("exploration_candidate")),
                        "error_fallback_risk": error_fallback_profiles.get(type_, {}).get("high_risk", False),
                    },
                )
                tid += 1
                return task

            weather_priority, weather_score = self._weighted_priority(
                ResearchPriority.HIGH,
                "weather",
                feature_weights=feature_weights,
            )
            tasks.append(mk(
                "weather",
                weather_priority,
                priority_score=weather_score,
                dates=prefs.get("travel_dates"),
                seasonal_only=not has_travel_dates,
            ))

            visa_priority, visa_score = self._weighted_priority(
                ResearchPriority.HIGH,
                "visa_ease", "safety",
                feature_weights=feature_weights,
            )
            tasks.append(mk(
                "visa",
                visa_priority,
                priority_score=visa_score,
                passport_country=prefs.get("passport_country", "US"),
            ))

            attractions_priority, attractions_score = self._weighted_priority(
                ResearchPriority.MEDIUM,
                "attractions", "culture", "beach", "nature",
                feature_weights=feature_weights,
                interest_boost=attraction_interested,
            )
            tasks.append(mk(
                "attractions",
                attractions_priority,
                priority_score=attractions_score,
                interests=interests,
            ))

            if has_travel_dates and prefs.get("origin"):
                flights_priority, flights_score = self._weighted_priority(
                    ResearchPriority.MEDIUM,
                    "flight_time", "price", "budget", "luxury",
                    feature_weights=feature_weights,
                )
                tasks.append(mk(
                    "flights",
                    flights_priority,
                    priority_score=flights_score,
                    origin=prefs["origin"],
                    dates=prefs.get("travel_dates"),
                ))

            if has_travel_dates:
                hotels_priority, hotels_score = self._weighted_priority(
                    ResearchPriority.MEDIUM,
                    "price", "budget", "luxury",
                    feature_weights=feature_weights,
                    interest_boost=hotel_interested,
                )
                tasks.append(mk(
                    "hotels",
                    hotels_priority,
                    priority_score=hotels_score,
                    budget_level=prefs.get("budget_level", "moderate"),
                    dates=prefs.get("travel_dates"),
                ))

                if depth != ResearchDepth.QUICK or event_interested or fw("nightlife") >= 0.4 or fw("family") >= 0.4:
                    events_priority, events_score = self._weighted_priority(
                        ResearchPriority.LOW,
                        "nightlife", "family",
                        feature_weights=feature_weights,
                        interest_boost=event_interested,
                    )
                    tasks.append(mk(
                        "events",
                        events_priority,
                        priority_score=events_score,
                        dates=prefs.get("travel_dates"),
                    ))

            if food_interested or fw("food") >= 0.40:
                dining_style = "fine_dining" if prefs.get("budget_level") == "luxury" else "street_food" if prefs.get("budget_level") == "budget" else "any"
                restaurants_priority, restaurants_score = self._weighted_priority(
                    ResearchPriority.MEDIUM,
                    "food",
                    feature_weights=feature_weights,
                    interest_boost=food_interested,
                )
                tasks.append(mk(
                    "restaurants",
                    restaurants_priority,
                    priority_score=restaurants_score,
                    budget_level=prefs.get("budget_level", "moderate"),
                    dietary_restrictions=dietary_restrictions,
                    cuisine_types=interests[:3],
                    dining_style=dining_style,
                ))

            # Transport + safety: only live-research when KB is stale/missing
            try:
                from app.utils.destination_knowledge_base import get_knowledge_base as _get_kb
                _snap = (_get_kb().get_destination_knowledge(dest) or {})
                _transport_stale = not _snap.get("transport_tips")
                _safety_stale = not _snap.get("safety_rating")
            except Exception:
                _transport_stale, _safety_stale = True, True

            if _transport_stale and depth != ResearchDepth.QUICK:
                tp, ts = self._weighted_priority(ResearchPriority.LOW, "safety", feature_weights=feature_weights)
                tasks.append(mk("transport", tp, priority_score=ts))

            if _safety_stale:
                sp, ss = self._weighted_priority(ResearchPriority.MEDIUM, "safety", feature_weights=feature_weights)
                tasks.append(mk("safety", sp, priority_score=ss))

            if self.config.enable_web_browsing:
                yr = date.today().year
                if has_travel_dates:
                    queries = [
                        f"{dest} travel guide {yr}",
                        f"best things to do in {dest}",
                        f"{dest} travel tips {yr}",
                    ]
                else:
                    queries = [
                        f"best time to visit {dest}",
                        f"{dest} weather by month",
                        f"{dest} travel seasons",
                        f"best areas to stay in {dest}",
                    ]
                if food_interested or fw("food") >= 0.40:
                    queries = [
                        f"best restaurants in {dest}",
                        f"{dest} food guide {yr}",
                        f"{dest} local cuisine",
                    ] + queries
                for interest in interests[:3]:
                    queries.append(f"{dest} {interest}")
                if depth == ResearchDepth.DEEP:
                    queries.extend([
                        f"hidden gems in {dest}",
                        f"{dest} neighborhoods guide",
                        f"{dest} sample itinerary",
                    ])
                if depth == ResearchDepth.QUICK:
                    queries = queries[:3]

                web_priority, web_score = self._weighted_priority(
                    ResearchPriority.MEDIUM,
                    "food", "weather", "attractions", "culture", "beach", "nature",
                    feature_weights=feature_weights,
                    interest_boost=food_interested or attraction_interested,
                )
                tasks.append(mk(
                    "web_search",
                    web_priority,
                    priority_score=web_score,
                    queries=list(dict.fromkeys(queries)),
                    fallback_task_types=fallback_task_types,
                ))

        # Inject dedicated fallback search tasks for historically high-risk APIs.
        # Keep these separate from the primary personalized web task so we do not
        # pollute the user's main research intent with recovery queries.
        try:
            backup_tasks: List[ResearchTask] = []
            for dest in destinations:
                profiles = {
                    task_type: error_learner.get_failure_profile(task_type=task_type, destination=dest)
                    for task_type in ("weather", "visa", "attractions", "flights", "hotels", "events", "restaurants")
                }
                for task_type, profile in profiles.items():
                    if not (profile and profile.get("high_risk") and profile.get("recommended_fallback") == "web_search"):
                        continue
                    queries = self._fallback_queries_for_task(task_type, dest)
                    if not queries:
                        continue
                    already_has_backup = any(
                        t.type == "web_search"
                        and t.destination == dest
                        and t.params.get("backup_for") == task_type
                        for t in tasks + backup_tasks
                    )
                    if already_has_backup:
                        continue
                    backup_priority = ResearchPriority.LOW
                    backup_score = round(1.35 + max(0.0, float(dest_success.get(dest, 0.5) - 0.5)), 2)
                    backup_tasks.append(
                        ResearchTask(
                            id=f"web_search_backup_{task_type}_{dest}_{len(backup_tasks)}",
                            type="web_search",
                            destination=dest,
                            priority=backup_priority,
                            priority_score=backup_score,
                            params={
                                "queries": queries,
                                "backup_for": task_type,
                                "fallback_reason": "high_risk_api",
                                "top_error_kind": profile.get("top_error_kind"),
                                "research_depth": destination_depth_map.get(dest, self.config.research_depth.value),
                                "error_fallback_risk": True,
                            },
                        )
                    )
            tasks.extend(backup_tasks)
        except Exception as _err:
            logger.debug(f"Error pattern backup task creation failed: {_err}")
        # ────────────────────────────────────────────────────────────────────

        tasks.sort(
            key=lambda task: (
                _priority_num(task.priority),
                -float(getattr(task, "priority_score", 0.0)),
            ),
        )
        return tasks

    def _is_degraded_result(self, task: ResearchTask, result: Dict[str, Any]) -> bool:
        summary = str((result or {}).get("summary") or "").lower()
        if not result:
            return True
        if "unavailable" in summary or "unknown destination" in summary:
            return True

        content_keys = {
            "weather": ["weather"],
            "visa": ["visa"],
            "attractions": ["top_picks", "attractions"],
            "flights": ["flights", "best_option"],
            "hotels": ["top_picks", "hotels"],
            "events": ["highlights", "events"],
            "restaurants": ["top_picks", "restaurants"],
            "web_search": ["sources", "web_results"],
        }.get(task.type, [])
        return bool(content_keys) and not any(result.get(key) for key in content_keys)

    # Task executors ────────────────────────────────────────────────────────

    async def _execute(self, task: ResearchTask) -> Dict[str, Any]:
        handlers = {
            "weather": self._do_weather,
            "visa": self._do_visa,
            "attractions": self._do_attractions,
            "flights": self._do_flights,
            "hotels": self._do_hotels,
            "events": self._do_events,
            "restaurants": self._do_restaurants,
            "web_search": self._do_web,
        }
        handler = handlers.get(task.type)
        if not handler:
            raise ValueError(f"Unknown task type: {task.type}")
        return await handler(task)

    async def _do_weather(self, task: ResearchTask) -> Dict:
        from app.services.weather_service import WeatherService
        from datetime import date as _date
        coords = _get_coords(task.destination)
        if not coords:
            return {"destination": task.destination, "summary": "Weather unavailable (unknown destination)"}
        try:
            dates = task.params.get("dates") or {}
            start_str = dates.get("start")
            if task.params.get("seasonal_only") or not start_str:
                best_time = await get_knowledge_base().get_best_time_to_visit(task.destination or "")
                if best_time.get("source") == "learned_knowledge":
                    summary = best_time.get("best_time") or "Seasonal guidance available"
                    return {
                        "destination": task.destination,
                        "weather": {
                            "best_time": best_time.get("best_time", ""),
                            "best_months": best_time.get("best_months") or [],
                        },
                        "summary": f"Best time to visit: {summary}",
                        "seasonal_only": True,
                    }
            try:
                date_obj = _date.fromisoformat(start_str) if start_str else _date.today()
            except (ValueError, TypeError):
                date_obj = _date.today()
            data = await WeatherService().get_weather(coords[0], coords[1], date_obj)
            temp = data.get("temperature", "N/A")
            cond = data.get("condition", "")
            return {"destination": task.destination, "weather": data,
                    "summary": f"{temp}°C, {cond}" if cond else f"{temp}°C"}
        except Exception as e:
            return {"destination": task.destination, "summary": f"Weather unavailable ({e})"}

    async def _do_visa(self, task: ResearchTask) -> Dict:
        from app.services.visa_service import VisaService
        passport = task.params.get("passport_country", "US")
        destination_country = self._resolve_country_code(task.destination or "")
        if not destination_country:
            return {
                "destination": task.destination,
                "summary": "Visa info unavailable (unknown destination country)",
                "passport": passport,
            }
        try:
            service = VisaService()
            data = await service.get_visa_requirements(passport, destination_country)
            summary = service.get_visa_summary(data)
            return {
                "destination": task.destination,
                "visa": data,
                "summary": summary,
                "passport": passport,
                "country_code": destination_country,
            }
        except Exception as e:
            return {"destination": task.destination, "summary": f"Visa info unavailable ({e})"}

    async def _do_attractions(self, task: ResearchTask) -> Dict:
        from app.services.attractions_service import AttractionsService
        coords = _get_coords(task.destination)
        if not coords:
            return {"destination": task.destination, "top_picks": [], "summary": "Attractions unavailable"}
        try:
            svc = AttractionsService()
            all_attractions = await svc.get_all_attractions(coords[0], coords[1], limit=15)
            # Score and sort by interest relevance if interests are provided
            interests = task.params.get("interests", [])
            if interests and hasattr(svc, "calculate_attractions_score"):
                svc.calculate_attractions_score(all_attractions, interests)
            picks = all_attractions[:5]
            return {"destination": task.destination, "attractions": all_attractions,
                    "top_picks": picks,
                    "summary": f"Found {len(picks)} top attractions"}
        except Exception as e:
            return {"destination": task.destination, "top_picks": [], "summary": f"Attractions unavailable ({e})"}

    async def _do_flights(self, task: ResearchTask) -> Dict:
        try:
            from app.services.flight_service import FlightService
            from datetime import date as _date
            origin = task.params.get("origin", "")
            dates = task.params.get("dates") or {}

            def _parse(s: Optional[str]) -> Optional[_date]:
                try:
                    return _date.fromisoformat(s) if s else None
                except (ValueError, TypeError):
                    return None

            dep = _parse(dates.get("start")) or _date.today()
            ret = _parse(dates.get("end"))

            service = FlightService()
            origin_code = await self._resolve_airport_code(service, origin)
            destination_code = await self._resolve_airport_code(service, task.destination or "")

            missing_parts = []
            if not origin_code:
                missing_parts.append(f"origin airport for {origin or 'departure city'}")
            if not destination_code:
                missing_parts.append(f"destination airport for {task.destination}")
            if missing_parts:
                return {
                    "destination": task.destination,
                    "flights": [],
                    "summary": f"Flight search unavailable (could not resolve {' and '.join(missing_parts)})",
                }

            flights = await service.search_flights(origin_code, destination_code, dep, ret)
            best = flights[0] if flights else None
            price = f"from ${best.price:.0f}" if best else "prices unavailable"
            return {
                "destination": task.destination,
                "origin_airport": origin_code,
                "destination_airport": destination_code,
                "flights": [f.model_dump(mode="json") for f in flights],
                "best_option": best.model_dump(mode="json") if best else None,
                "summary": f"Flights {price}",
            }
        except Exception as e:
            return {"destination": task.destination, "flights": [], "summary": f"Flight search unavailable ({e})"}

    async def _do_hotels(self, task: ResearchTask) -> Dict:
        try:
            from app.services.hotel_service import HotelService
            from datetime import date as _date
            dates = task.params.get("dates") or {}

            def _parse(s: Optional[str]) -> Optional[_date]:
                try:
                    return _date.fromisoformat(s) if s else None
                except (ValueError, TypeError):
                    return None

            check_in = _parse(dates.get("start")) or _date.today()
            check_out = _parse(dates.get("end")) or (_date.today().replace(day=min(_date.today().day + 7, 28)))
            budget_level = task.params.get("budget_level", "moderate")
            max_price = self.HOTEL_CAP.get(budget_level, self.HOTEL_CAP["moderate"])

            hotels = await HotelService().search_hotels(
                task.destination, check_in, check_out, max_price=max_price
            )
            picks = hotels[:4]
            return {
                "destination": task.destination,
                "hotels": [h.dict() for h in hotels],
                "top_picks": [h.dict() for h in picks],
                "summary": f"Found {len(picks)} hotels",
            }
        except Exception as e:
            return {"destination": task.destination, "hotels": [], "top_picks": [], "summary": f"Hotel search unavailable ({e})"}

    async def _do_events(self, task: ResearchTask) -> Dict:
        from app.services.events_service import EventsService
        from datetime import date as _date
        dates = task.params.get("dates") or {}
        try:
            # EventsService.get_events(city, start_date, end_date, country_code)
            # requires date objects, not strings or floats
            def _parse(s: Optional[str]) -> Optional[_date]:
                try:
                    return _date.fromisoformat(s) if s else None
                except (ValueError, TypeError):
                    return None

            start_date = _parse(dates.get("start")) or _date.today()
            end_date = _parse(dates.get("end")) or start_date.replace(
                day=min(start_date.day + 7, 28)
            )
            city = _get_destination_city(task.destination or "")
            country_code = self._resolve_country_code(task.destination or "")
            events = await EventsService().get_events(
                city, start_date, end_date, country_code
            )
            # events is a list of Event objects
            highlights = events[:5] if isinstance(events, list) else []
            highlight_dicts = []
            for ev in highlights:
                if hasattr(ev, "dict"):
                    highlight_dicts.append(ev.dict())
                elif isinstance(ev, dict):
                    highlight_dicts.append(ev)
            return {
                "destination": task.destination,
                "events": highlight_dicts,
                "highlights": highlight_dicts,
                "summary": f"Found {len(highlight_dicts)} events",
                "country_code": country_code,
            }
        except Exception as e:
            return {"destination": task.destination, "events": [], "summary": f"Events unavailable ({e})"}

    async def _do_restaurants(self, task: ResearchTask) -> Dict:
        from app.services.restaurants_service import RestaurantsService

        def _load_restaurant_data() -> Dict[str, Any]:
            service = RestaurantsService()
            restaurants = service.get_restaurants(
                task.destination,
                cuisine_types=task.params.get("cuisine_types") or None,
                budget_level=task.params.get("budget_level", "moderate"),
                dining_style=task.params.get("dining_style", "any"),
            )
            food_scene = service.get_food_scene(task.destination)
            dietary_restrictions = task.params.get("dietary_restrictions") or []
            dietary = (
                service.get_dietary_options(task.destination, dietary_restrictions)
                if dietary_restrictions
                else {}
            )
            return {
                "restaurants": restaurants,
                "food_scene": food_scene,
                "dietary": dietary,
            }

        try:
            data = await asyncio.to_thread(_load_restaurant_data)
            top_picks = data["restaurants"][:5]
            food_scene = data.get("food_scene", {}).get("food_scene", {})
            must_try = food_scene.get("must_try")
            summary = f"Found {len(top_picks)} dining picks"
            if must_try:
                summary = f"{summary}; must-try: {must_try}"
            return {
                "destination": task.destination,
                "restaurants": data["restaurants"],
                "top_picks": top_picks,
                "food_scene": data.get("food_scene"),
                "dietary": data.get("dietary"),
                "summary": summary,
            }
        except Exception as exc:
            return {"destination": task.destination, "restaurants": [], "top_picks": [], "summary": f"Dining research unavailable ({exc})"}

    async def _do_web(self, task: ResearchTask) -> Dict:
        queries = (task.params.get("queries") or [])[:3]
        all_results: List[Dict] = []
        for q in queries:
            try:
                results = await self.research_agent.search_web(q, max_results=5)
                all_results.extend(results)
            except Exception as exc:
                logger.warning(f"Web search failed for '{q}': {exc}")

        # Deduplicate by URL
        seen: set = set()
        unique: List[Dict] = []
        for r in all_results:
            url = r.get("href", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(r)

        sources = [
            {"title": r.get("title", ""), "url": r.get("href", ""),
             "snippet": (r.get("body") or "")[:200]}
            for r in unique[:6]
        ]
        page_highlights = [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "summary": (r.get("body") or "")[:320],
            }
            for r in unique
            if r.get("scraped") and r.get("href")
        ][:3]
        scraped_pages = sum(1 for result in unique if result.get("scraped"))
        return {
            "destination": task.destination,
            "web_results": unique[:10],
            "sources": sources,
            "page_highlights": page_highlights,
            "scraped_pages": scraped_pages,
            "queries_run": queries,
            "summary": (
                f"Found {len(unique)} web sources and read {scraped_pages} live pages"
                if scraped_pages
                else f"Found {len(unique)} web sources"
            ),
        }

    # ── Plan synthesis ────────────────────────────────────────────────────────

    def _group_results_by_destination(self, prefs: Optional[Dict[str, Any]] = None) -> Dict[str, Dict]:
        active_prefs = prefs or self._preferences
        destinations = (active_prefs.get("destinations") or [])[:self.config.max_destinations]
        by_dest: Dict[str, Dict] = {destination: {} for destination in destinations}
        for task_id, result in self.research_results.items():
            if not result:
                continue
            destination = result.get("destination")
            if destination and destination in by_dest:
                task_type = task_id.split("_")[0]
                by_dest[destination][task_type] = result
        return by_dest

    def _destination_personalization_bonus(
        self,
        destination_data: Dict[str, Any],
        prefs: Dict[str, Any],
    ) -> Dict[str, Any]:
        feature_weights = prefs.get("learned_feature_weights")
        if not isinstance(feature_weights, dict):
            return {"bonus": 0.0, "matched_priorities": []}

        matched_priorities: List[str] = []
        bonus = 0.0

        def weight(name: str) -> float:
            try:
                return float(feature_weights.get(name, 0.0))
            except (TypeError, ValueError):
                return 0.0

        if weight("food") >= 0.65 and destination_data.get("restaurants"):
            picks = destination_data["restaurants"].get("top_picks") or []
            bonus += min(0.1, 0.04 + len(picks[:4]) * 0.01)
            matched_priorities.append("food")

        if weight("weather") >= 0.65 and destination_data.get("weather"):
            bonus += 0.05
            matched_priorities.append("weather")

        if max(weight("attractions"), weight("culture"), weight("beach"), weight("nature")) >= 0.65 and destination_data.get("attractions"):
            picks = destination_data["attractions"].get("top_picks") or []
            bonus += min(0.09, 0.03 + len(picks[:4]) * 0.01)
            matched_priorities.append("attractions")

        if max(weight("price"), weight("budget"), weight("luxury")) >= 0.65 and (
            destination_data.get("hotels") or destination_data.get("flights")
        ):
            bonus += 0.05
            matched_priorities.append("price")

        if max(weight("nightlife"), weight("family")) >= 0.65 and destination_data.get("events"):
            bonus += 0.04
            matched_priorities.append("events")

        visa_summary = str((destination_data.get("visa") or {}).get("summary") or "").lower()
        if weight("visa_ease") >= 0.65 and any(term in visa_summary for term in ("visa-free", "visa free", "on arrival", "e-visa", "evisa")):
            bonus += 0.04
            matched_priorities.append("visa")

        deduped = list(dict.fromkeys(matched_priorities))
        return {"bonus": round(min(0.2, bonus), 2), "matched_priorities": deduped}

    def _destination_style_bonus(
        self,
        destination: str,
        destination_data: Dict[str, Any],
        evaluation: Dict[str, Any],
        prefs: Dict[str, Any],
    ) -> Dict[str, Any]:
        style_profile = prefs.get("user_style_profile")
        if not isinstance(style_profile, dict):
            return {"bonus": 0.0, "dominant_style": None, "style_confidence": 0.0, "signals": []}

        try:
            confidence = float(style_profile.get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        try:
            interactions = int(style_profile.get("interactions", 0) or 0)
        except (TypeError, ValueError):
            interactions = 0

        if interactions < 2 or confidence < 0.2:
            return {
                "bonus": 0.0,
                "dominant_style": style_profile.get("dominant_style"),
                "style_confidence": round(confidence, 3),
                "signals": [],
            }

        dominant_style = str(style_profile.get("dominant_style") or "").strip().lower()
        if not dominant_style:
            return {"bonus": 0.0, "dominant_style": None, "style_confidence": round(confidence, 3), "signals": []}

        focus_tags = {tag.lower() for tag in self._destination_focus_tags(destination)}
        available_sections = {
            str(section).strip().lower()
            for section, payload in destination_data.items()
            if payload
        }
        criteria_scores = evaluation.get("criteria_scores") or {}

        bonus = 0.0
        signals: List[str] = []

        def add(amount: float, label: str) -> None:
            nonlocal bonus
            bonus += amount
            signals.append(label)

        if dominant_style == "explorer":
            if len(focus_tags) >= 3 or "web_search" in available_sections:
                add(0.025, "discovery_depth")
            if focus_tags & {"culture", "food", "nature", "photography"}:
                add(0.025, "novelty_fit")
        elif dominant_style == "optimizer":
            if float(criteria_scores.get("cost", 0.0) or 0.0) >= 0.65:
                add(0.04, "value_fit")
            if {"flights", "hotels"} & available_sections:
                add(0.02, "comparison_ready")
        elif dominant_style == "relaxer":
            if float(criteria_scores.get("weather", 0.0) or 0.0) >= 0.65:
                add(0.03, "comfort_weather")
            if focus_tags & {"beach", "relaxation", "luxury"} or "hotels" in available_sections:
                add(0.03, "comfort_fit")
        elif dominant_style == "adventurer":
            if focus_tags & {"nature", "adventure", "hiking", "outdoors", "beach"}:
                add(0.04, "activity_fit")
            if float(criteria_scores.get("attractions", 0.0) or 0.0) >= 0.6:
                add(0.02, "activity_density")
        elif dominant_style == "culturist":
            if focus_tags & {"culture", "history", "food", "architecture", "art"}:
                add(0.04, "cultural_fit")
            if "attractions" in available_sections:
                add(0.02, "depth_available")
        elif dominant_style == "socializer":
            if focus_tags & {"nightlife", "food", "events"}:
                add(0.04, "social_scene")
            if "events" in available_sections or "restaurants" in available_sections:
                add(0.02, "social_options")

        if not signals:
            return {
                "bonus": 0.0,
                "dominant_style": dominant_style,
                "style_confidence": round(confidence, 3),
                "signals": [],
            }

        confidence_scale = min(1.0, max(0.4, confidence / 0.35))
        scaled_bonus = min(0.08, bonus * confidence_scale)
        return {
            "bonus": round(scaled_bonus, 3),
            "dominant_style": dominant_style,
            "style_confidence": round(confidence, 3),
            "signals": list(dict.fromkeys(signals)),
        }

    def _destination_hypothesis_bonus(
        self,
        destination: str,
        destination_data: Dict[str, Any],
        evaluation: Dict[str, Any],
        prefs: Dict[str, Any],
    ) -> Dict[str, Any]:
        active_hypotheses = prefs.get("active_hypotheses")
        hypothesis_recommendations = prefs.get("hypothesis_recommendations")
        if not isinstance(active_hypotheses, list) or not isinstance(hypothesis_recommendations, dict):
            return {"bonus": 0.0, "signals": [], "supporting_hypotheses": [], "hypothesis_count": 0}

        filters = hypothesis_recommendations.get("filters") or {}
        boosts = hypothesis_recommendations.get("boosts") or {}
        if not isinstance(filters, dict):
            filters = {}
        if not isinstance(boosts, dict):
            boosts = {}

        focus_tags = {tag.lower() for tag in self._destination_focus_tags(destination)}
        available_sections = {
            str(section).strip().lower()
            for section, payload in destination_data.items()
            if payload
        }
        criteria_scores = evaluation.get("criteria_scores") or {}
        visa_summary = str((destination_data.get("visa") or {}).get("summary") or "").lower()
        flight_summary = str((destination_data.get("flights") or {}).get("summary") or "").lower()

        hypotheses_by_template: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        confidence_values: List[float] = []
        for hypothesis in active_hypotheses:
            if not isinstance(hypothesis, dict):
                continue
            template_name = str(hypothesis.get("template_name") or "").strip().lower()
            if template_name:
                hypotheses_by_template[template_name].append(hypothesis)
            try:
                confidence_values.append(float(hypothesis.get("confidence", 0.0) or 0.0))
            except (TypeError, ValueError):
                continue

        bonus = 0.0
        signals: List[str] = []
        supporting_hypotheses: List[str] = []

        def add(amount: float, label: str, template_names: Optional[List[str]] = None) -> None:
            nonlocal bonus
            bonus += amount
            signals.append(label)
            for template_name in template_names or []:
                for hypothesis in hypotheses_by_template.get(template_name, []):
                    text = str(hypothesis.get("hypothesis") or "").strip()
                    if text and text not in supporting_hypotheses:
                        supporting_hypotheses.append(text)

        if filters.get("climate_match") and float(criteria_scores.get("weather", 0.0) or 0.0) >= 0.65:
            add(0.035, "climate_match", ["weather_preference"])

        if filters.get("max_price") == "strict" and float(criteria_scores.get("cost", 0.0) or 0.0) >= 0.65:
            add(0.045, "budget_fit", ["budget_constraint"])

        if filters.get("visa_free_only") and any(
            term in visa_summary for term in ("visa-free", "visa free", "on arrival", "e-visa", "evisa")
        ):
            add(0.04, "visa_fit", ["visa_sensitivity"])

        if filters.get("max_flight_hours") and "flights" in available_sections and any(
            term in flight_summary for term in ("direct", "nonstop", "short", "6h", "7h", "8h", "9h", "10h")
        ):
            add(0.03, "flight_time_fit", ["flight_time_sensitivity"])

        if boosts.get("culture_score") and (
            focus_tags & {"culture", "history", "food", "architecture", "art"}
            or {"attractions", "restaurants"} & available_sections
        ):
            add(0.05, "culture_focus", ["interest_focus"])

        if boosts.get("adventure_score") and (
            focus_tags & {"nature", "adventure", "hiking", "outdoors", "beach"}
            or float(criteria_scores.get("attractions", 0.0) or 0.0) >= 0.7
        ):
            add(0.05, "adventure_focus", ["interest_focus", "travel_style_match", "destination_type_preference"])

        if boosts.get("beach_score") and (
            focus_tags & {"beach", "relaxation", "coastal", "tropical"}
            or "weather" in available_sections
        ):
            add(0.05, "beach_focus", ["interest_focus", "destination_type_preference"])

        if not signals:
            return {
                "bonus": 0.0,
                "signals": [],
                "supporting_hypotheses": [],
                "hypothesis_count": len(hypotheses_by_template),
            }

        avg_confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.7
        )
        confidence_scale = min(1.2, max(0.65, avg_confidence / 0.7))
        scaled_bonus = min(0.1, bonus * confidence_scale)
        return {
            "bonus": round(scaled_bonus, 3),
            "signals": list(dict.fromkeys(signals)),
            "supporting_hypotheses": supporting_hypotheses[:3],
            "hypothesis_count": len(hypotheses_by_template),
        }

    def _destination_affinity_bonus(
        self,
        destination: str,
        destination_data: Dict[str, Any],
        evaluation: Dict[str, Any],
        prefs: Dict[str, Any],
    ) -> Dict[str, Any]:
        affinity_payload = prefs.get("destination_affinity_recommendations")
        if not isinstance(affinity_payload, dict):
            return {
                "bonus": 0.0,
                "predicted_rating": 0.0,
                "acceptance_rate": None,
                "signals": [],
                "methods": [],
                "similar_destinations": [],
            }

        by_destination = affinity_payload.get("by_destination") or {}
        destination_details = affinity_payload.get("destination_details") or {}
        if not isinstance(by_destination, dict):
            by_destination = {}
        if not isinstance(destination_details, dict):
            destination_details = {}

        recommendation = by_destination.get(destination) or {}
        details = destination_details.get(destination) or {}
        if not isinstance(recommendation, dict):
            recommendation = {}
        if not isinstance(details, dict):
            details = {}

        try:
            predicted_rating = float(recommendation.get("predicted_rating", 0.0) or 0.0)
        except (TypeError, ValueError):
            predicted_rating = 0.0
        acceptance_rate = recommendation.get("acceptance_rate")
        try:
            acceptance_rate_value = (
                float(acceptance_rate)
                if acceptance_rate is not None
                else (
                    float(details.get("acceptance_rate"))
                    if details.get("acceptance_rate") is not None
                    else None
                )
            )
        except (TypeError, ValueError):
            acceptance_rate_value = None

        explanation = recommendation.get("explanation") or {}
        methods_used = explanation.get("methods_used") if isinstance(explanation, dict) else []
        if not isinstance(methods_used, list):
            methods_used = []

        bonus = 0.0
        signals: List[str] = []
        methods: List[str] = []

        def add(amount: float, label: str) -> None:
            nonlocal bonus
            bonus += amount
            signals.append(label)

        if predicted_rating >= 0.82:
            add(0.06, "strong_affinity_match")
        elif predicted_rating >= 0.7:
            add(0.045, "affinity_match")
        elif predicted_rating >= 0.6:
            add(0.025, "weak_affinity_match")

        if acceptance_rate_value is not None and acceptance_rate_value >= 0.7:
            add(0.02, "high_acceptance_affinity")

        for method in methods_used:
            if not isinstance(method, dict):
                continue
            method_name = str(method.get("method") or "").strip().lower()
            if not method_name:
                continue
            methods.append(method_name)
            if method_name == "item_based_cf":
                add(0.02, "similar_destination_overlap")
            elif method_name == "user_based_cf":
                add(0.02, "similar_user_overlap")

        similar_destinations = []
        for similar in details.get("similar_destinations") or []:
            if not isinstance(similar, dict):
                continue
            name = str(similar.get("destination") or "").strip()
            if name:
                similar_destinations.append(name)

        if not signals and not similar_destinations:
            return {
                "bonus": 0.0,
                "predicted_rating": round(predicted_rating, 3),
                "acceptance_rate": round(acceptance_rate_value, 3) if isinstance(acceptance_rate_value, float) else None,
                "signals": [],
                "methods": list(dict.fromkeys(methods)),
                "similar_destinations": similar_destinations[:3],
            }

        return {
            "bonus": round(min(0.09, bonus), 3),
            "predicted_rating": round(predicted_rating, 3),
            "acceptance_rate": round(acceptance_rate_value, 3) if isinstance(acceptance_rate_value, float) else None,
            "signals": list(dict.fromkeys(signals)),
            "methods": list(dict.fromkeys(methods)),
            "similar_destinations": similar_destinations[:3],
        }

    def _summarize_engagement(
        self,
        session: Optional[ChatSession],
    ) -> Dict[str, Dict[str, Any]]:
        if not session:
            return {}

        raw_events = session.planning_data.get("engagement_log") or session.planning_data.get("engagement_events")
        if not isinstance(raw_events, list):
            return {}

        summary: Dict[str, Dict[str, Any]] = {}
        for event in raw_events:
            if not isinstance(event, dict):
                continue

            destination = str(event.get("destination") or "").strip()
            if not destination:
                continue

            try:
                time_spent_ms = int(event.get("time_spent_ms", event.get("duration_ms", 0)) or 0)
            except (TypeError, ValueError):
                time_spent_ms = 0
            if time_spent_ms <= 0:
                continue

            bounded_ms = min(time_spent_ms, 300000)
            section = str(event.get("section") or "general").strip() or "general"
            bucket = summary.setdefault(
                destination,
                {
                    "time_spent_ms": 0,
                    "events": 0,
                    "sections": {},
                    "top_sections": [],
                    "engagement_boost": 0.0,
                },
            )
            bucket["time_spent_ms"] += bounded_ms
            bucket["events"] += 1
            bucket["sections"][section] = int(bucket["sections"].get(section, 0)) + bounded_ms

        max_time_ms = max(
            (int(bucket.get("time_spent_ms", 0)) for bucket in summary.values()),
            default=0,
        )
        for bucket in summary.values():
            ordered_sections = sorted(
                bucket["sections"].items(),
                key=lambda item: item[1],
                reverse=True,
            )
            bucket["sections"] = {name: ms for name, ms in ordered_sections}
            bucket["top_sections"] = [name for name, _ms in ordered_sections[:3]]

            time_spent_ms = int(bucket.get("time_spent_ms", 0))
            if time_spent_ms < 5000 or max_time_ms <= 0:
                bucket["engagement_boost"] = 0.0
                continue

            normalized = min(1.0, time_spent_ms / 30000.0)
            relative_share = time_spent_ms / max_time_ms
            bucket["engagement_boost"] = round(
                min(0.12, (0.08 * normalized) + (0.04 * relative_share)),
                2,
            )

        return summary

    def _compact_decision_feedback_evaluation(
        self,
        evaluation: Dict[str, Any],
    ) -> Dict[str, Any]:
        compact: Dict[str, Any] = {
            "destination": str(evaluation.get("destination") or "").strip(),
        }

        for key in (
            "total_score",
            "personalized_total_score",
            "final_total_score",
            "confidence",
            "personalization_bonus",
            "engagement_boost",
        ):
            value = evaluation.get(key)
            if isinstance(value, (int, float)):
                compact[key] = round(float(value), 3)

        try:
            engagement_time_ms = int(evaluation.get("engagement_time_ms", 0) or 0)
        except (TypeError, ValueError):
            engagement_time_ms = 0
        if engagement_time_ms > 0:
            compact["engagement_time_ms"] = engagement_time_ms

        criteria_scores = {}
        for criterion, score in (evaluation.get("criteria_scores") or {}).items():
            if isinstance(score, (int, float)):
                criteria_scores[str(criterion)] = round(float(score), 3)
        if criteria_scores:
            compact["criteria_scores"] = criteria_scores

        criteria_weights = {}
        for criterion, weight in (evaluation.get("criteria_weights") or {}).items():
            if isinstance(weight, (int, float)):
                criteria_weights[str(criterion)] = round(float(weight), 3)
        if criteria_weights:
            compact["criteria_weights"] = criteria_weights

        matched_priorities = [
            str(item).strip()
            for item in (evaluation.get("matched_priorities") or [])
            if str(item).strip()
        ]
        if matched_priorities:
            compact["matched_priorities"] = matched_priorities[:6]

        engagement_sections = [
            str(item).strip()
            for item in (evaluation.get("engagement_sections") or [])
            if str(item).strip()
        ]
        if engagement_sections:
            compact["engagement_sections"] = engagement_sections[:4]

        return compact

    def _build_decision_feedback_context(
        self,
        plan: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(plan, dict):
            return None

        decision_analysis = plan.get("decision_analysis")
        if not isinstance(decision_analysis, dict):
            return None

        evaluations = [
            self._compact_decision_feedback_evaluation(evaluation)
            for evaluation in (decision_analysis.get("evaluations") or [])
            if isinstance(evaluation, dict)
        ]
        evaluations = [evaluation for evaluation in evaluations if evaluation.get("destination")]
        if not evaluations:
            return None

        context: Dict[str, Any] = {
            "ranking_basis": str(decision_analysis.get("ranking_basis") or "default"),
            "best_destination": str(
                decision_analysis.get("best_destination") or evaluations[0]["destination"]
            ),
            "evaluations": evaluations[: self.config.max_destinations],
        }

        best_score = decision_analysis.get("best_score")
        if isinstance(best_score, (int, float)):
            context["best_score"] = round(float(best_score), 3)

        return context

    def _rank_destination_evaluations(
        self,
        evaluations: List[Dict[str, Any]],
        by_dest: Dict[str, Dict[str, Any]],
        prefs: Dict[str, Any],
        engagement_summary: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []
        for evaluation in evaluations:
            personalization = self._destination_personalization_bonus(
                by_dest.get(evaluation["destination"], {}),
                prefs,
            )
            engagement = (engagement_summary or {}).get(evaluation["destination"], {})
            style_adjustment = self._destination_style_bonus(
                evaluation["destination"],
                by_dest.get(evaluation["destination"], {}),
                evaluation,
                prefs,
            )
            hypothesis_adjustment = self._destination_hypothesis_bonus(
                evaluation["destination"],
                by_dest.get(evaluation["destination"], {}),
                evaluation,
                prefs,
            )
            affinity_adjustment = self._destination_affinity_bonus(
                evaluation["destination"],
                by_dest.get(evaluation["destination"], {}),
                evaluation,
                prefs,
            )
            personalized_total = min(
                1.0,
                float(evaluation.get("total_score", 0.0)) + personalization["bonus"],
            )
            final_total = min(
                1.0,
                personalized_total
                + float(engagement.get("engagement_boost", 0.0))
                + float(style_adjustment.get("bonus", 0.0))
                + float(hypothesis_adjustment.get("bonus", 0.0))
                + float(affinity_adjustment.get("bonus", 0.0))
            )
            ranked.append(
                {
                    **evaluation,
                    "personalization_bonus": personalization["bonus"],
                    "matched_priorities": personalization["matched_priorities"],
                    "personalized_total_score": round(personalized_total, 2),
                    "engagement_boost": round(float(engagement.get("engagement_boost", 0.0)), 2),
                    "engagement_time_ms": int(engagement.get("time_spent_ms", 0) or 0),
                    "engagement_sections": list(engagement.get("top_sections") or []),
                    "engagement_events": int(engagement.get("events", 0) or 0),
                    "style_bonus": round(float(style_adjustment.get("bonus", 0.0) or 0.0), 3),
                    "dominant_style": style_adjustment.get("dominant_style"),
                    "style_confidence": round(float(style_adjustment.get("style_confidence", 0.0) or 0.0), 3),
                    "style_signals": list(style_adjustment.get("signals") or []),
                    "hypothesis_bonus": round(float(hypothesis_adjustment.get("bonus", 0.0) or 0.0), 3),
                    "hypothesis_signals": list(hypothesis_adjustment.get("signals") or []),
                    "supporting_hypotheses": list(hypothesis_adjustment.get("supporting_hypotheses") or []),
                    "hypothesis_count": int(hypothesis_adjustment.get("hypothesis_count", 0) or 0),
                    "affinity_bonus": round(float(affinity_adjustment.get("bonus", 0.0) or 0.0), 3),
                    "affinity_predicted_rating": round(float(affinity_adjustment.get("predicted_rating", 0.0) or 0.0), 3),
                    "affinity_acceptance_rate": affinity_adjustment.get("acceptance_rate"),
                    "affinity_signals": list(affinity_adjustment.get("signals") or []),
                    "affinity_methods": list(affinity_adjustment.get("methods") or []),
                    "affinity_similar_destinations": list(affinity_adjustment.get("similar_destinations") or []),
                    "final_total_score": round(final_total, 2),
                }
            )

        ranked.sort(
            key=lambda item: (
                item.get("final_total_score", item.get("personalized_total_score", item.get("total_score", 0.0))),
                item.get("personalized_total_score", item.get("total_score", 0.0)),
                item.get("total_score", 0.0),
            ),
            reverse=True,
        )
        return ranked

    async def _synthesize_plan(
        self,
        session: Optional[ChatSession] = None,
        partial: bool = False,
    ) -> Dict[str, Any]:
        prefs = dict(self._preferences)  # copy so we can enrich without mutating

        # Enrich prefs with per-user learned weights from the learning system
        user_id = (session.user_id if session else None) or prefs.get("user_id")
        if user_id:
            try:
                from app.utils.learning_agent import get_learner
                learner = get_learner()
                profile = learner.get_user_profile(user_id) or {}
                profile_prefs = profile.get("preferences", {}) if isinstance(profile, dict) else {}
                if profile_prefs and not isinstance(prefs.get("learned_feature_weights"), dict):
                    learned_weights = learner.get_personalized_weights(user_id)
                    if learned_weights:
                        prefs["learned_feature_weights"] = learned_weights
                learned_interests = (
                    profile_prefs.get("top_features")
                    or profile_prefs.get("preferred_features")
                    or []
                )
                if learned_interests:
                    prefs.setdefault("learned_interests", learned_interests[:5])
            except Exception as _exc:
                logger.debug(f"Could not load learned profile for {user_id}: {_exc}")

        if not isinstance(prefs.get("adaptive_criteria_weights"), dict):
            adaptive_criteria_weights = self._get_adaptive_criteria_weights(session)
            if adaptive_criteria_weights:
                prefs["adaptive_criteria_weights"] = adaptive_criteria_weights
        if not isinstance(prefs.get("user_style_profile"), dict):
            style_profile = self._get_user_style_profile(session)
            if style_profile:
                prefs["user_style_profile"] = style_profile
                prefs["dominant_style"] = style_profile.get("dominant_style")
        if not isinstance(prefs.get("active_hypotheses"), list):
            active_hypotheses = self._get_active_hypotheses(session)
            if active_hypotheses:
                prefs["active_hypotheses"] = active_hypotheses
        if not isinstance(prefs.get("hypothesis_recommendations"), dict):
            hypothesis_recommendations = self._get_hypothesis_recommendations(session)
            if hypothesis_recommendations:
                prefs["hypothesis_recommendations"] = hypothesis_recommendations

        by_dest = self._group_results_by_destination(prefs)
        if not isinstance(prefs.get("destination_affinity_recommendations"), dict):
            destination_affinity_recommendations = self._get_destination_affinity_recommendations(
                session,
                list(by_dest.keys()),
            )
            if destination_affinity_recommendations:
                prefs["destination_affinity_recommendations"] = destination_affinity_recommendations
        successful_tasks = sum(1 for task in self.completed_tasks if task.status == "completed")
        engagement_summary = self._summarize_engagement(session)

        # Add decision analysis
        try:
            decision_engine = get_decision_engine()
            evaluations = [
                decision_engine.evaluate_destination(
                    destination=dest,
                    preferences=prefs,
                    research_data=by_dest.get(dest, {})
                )
                for dest in by_dest.keys()
            ]
            evaluations = self._rank_destination_evaluations(
                evaluations,
                by_dest,
                prefs,
                engagement_summary=engagement_summary,
            )
        except Exception as e:
            logger.warning(f"Decision engine failed: {e}")
            evaluations = []

        ranked_destinations = [evaluation["destination"] for evaluation in evaluations] if evaluations else list(by_dest.keys())
        ranked_destinations.extend(
            destination for destination in by_dest.keys() if destination not in ranked_destinations
        )
        ranked_by_dest = {destination: by_dest[destination] for destination in ranked_destinations if destination in by_dest}
        proactive_alerts = []
        if session:
            stored_alerts = session.planning_data.get("proactive_alerts") or []
            if isinstance(stored_alerts, list):
                proactive_alerts = stored_alerts

        plan_text = await self._ai_plan(ranked_by_dest, prefs, partial=partial)
        has_personalization = bool(evaluations and any(e.get("personalization_bonus") for e in evaluations))
        has_engagement = bool(evaluations and any(e.get("engagement_boost") for e in evaluations))
        has_style = bool(evaluations and any(e.get("style_bonus") for e in evaluations))
        has_hypothesis = bool(evaluations and any(e.get("hypothesis_bonus") for e in evaluations))
        has_affinity = bool(evaluations and any(e.get("affinity_bonus") for e in evaluations))
        ranking_components = []
        if has_personalization:
            ranking_components.append("personalized")
        if has_engagement:
            ranking_components.append("engagement")
        if has_style:
            ranking_components.append("style")
        if has_hypothesis:
            ranking_components.append("hypothesis")
        if has_affinity:
            ranking_components.append("affinity")
        ranking_basis = "+".join(ranking_components) if ranking_components else "default"

        # ── Post-synthesis learning: record implicit signals ──────────
        # The top-ranked destination is an implicit "soft acceptance" and
        # the bottom-ranked ones are implicit "soft rejections".  Recording
        # these lets the learning system improve even without explicit user
        # feedback.  We use a lighter weight (0.3) compared to explicit
        # feedback (1.0) so the signal doesn't over-power real reactions.
        if user_id and ranked_destinations and not partial:
            try:
                from app.utils.learning_agent import learn_from_interaction
                _top_dest = ranked_destinations[0]
                _top_eval = evaluations[0] if evaluations else {}
                # Extract which criteria drove the top destination
                _top_features = []
                criteria_scores = _top_eval.get("criteria_scores") or _top_eval.get("scores") or {}
                for crit, sc in criteria_scores.items():
                    if isinstance(sc, (int, float)) and sc >= 0.6:
                        _top_features.append(crit)
                if _top_features:
                    await learn_from_interaction(
                        user_id=user_id,
                        interaction_type="implicit_recommendation",
                        destination=_top_dest,
                        feedback_data={
                            "features": _top_features,
                            "weight": 0.3,
                            "source": "synthesis_ranking",
                        },
                    )
                    append_learning_signal(
                        session.planning_data if session else None,
                        signal_type="implicit_recommendation",
                        destination=_top_dest,
                        source="synthesis_ranking",
                        weight=0.3,
                        features=_top_features,
                        metadata={
                            "criteria_count": len(_top_features),
                        },
                    )
                # ── Soft rejection for bottom-ranked destinations ─────
                # The lowest-ranked destinations are implicit "soft rejections".
                # We record which criteria scored LOWEST — these are the features
                # that likely caused the destination to rank poorly for this user.
                # Weight is lighter (0.15) than the positive signal (0.3).
                if len(ranked_destinations) >= 3:
                    _bottom_dests = ranked_destinations[-2:]  # bottom 2
                    for _bot_idx, _bot_dest in enumerate(_bottom_dests):
                        _bot_eval_idx = len(evaluations) - len(_bottom_dests) + _bot_idx
                        _bot_eval = evaluations[_bot_eval_idx] if 0 <= _bot_eval_idx < len(evaluations) else {}
                        _bot_scores = _bot_eval.get("criteria_scores") or _bot_eval.get("scores") or {}
                        # Extract the weakest criteria (scored < 0.4)
                        _weak_features = [
                            crit for crit, sc in _bot_scores.items()
                            if isinstance(sc, (int, float)) and sc < 0.4
                        ]
                        if _weak_features:
                            await learn_from_interaction(
                                user_id=user_id,
                                interaction_type="implicit_dislike",
                                destination=_bot_dest,
                                feedback_data={
                                    "features": _weak_features,
                                    "weight": 0.15,
                                    "source": "synthesis_ranking_bottom",
                                },
                            )
                            append_learning_signal(
                                session.planning_data if session else None,
                                signal_type="implicit_rejection",
                                destination=_bot_dest,
                                source="synthesis_ranking_bottom",
                                weight=0.15,
                                features=_weak_features,
                                metadata={
                                    "rank": len(ranked_destinations) - len(_bottom_dests) + _bot_idx + 1,
                                    "weak_criteria_count": len(_weak_features),
                                },
                            )

            except Exception as _learn_exc:
                logger.debug(f"Post-synthesis learning failed (non-fatal): {_learn_exc}")

        # ── Engagement-based feature learning ────────────────────────
        # Convert per-destination engagement time into feature weight
        # updates.  If the user spent 20s on Tokyo's "attractions" section
        # we infer they care about attractions → nudge the weight up.
        if user_id and engagement_summary and not partial:
            try:
                from app.utils.learning_agent import learn_from_interaction
                # Map section names to learner feature names
                _section_to_feature = {
                    "attractions": "attractions",
                    "weather": "weather",
                    "visa": "visa_ease",
                    "hotels": "budget",
                    "flights": "flight_time",
                    "restaurants": "food",
                    "events": "nightlife",
                    "culture": "culture",
                    "nature": "nature",
                    "beach": "beach",
                    "safety": "safety",
                }
                for _eng_dest, _eng_data in engagement_summary.items():
                    top_sections = _eng_data.get("top_sections", [])
                    total_ms = _eng_data.get("time_spent_ms", 0)
                    if total_ms < 5000 or not top_sections:
                        continue  # skip minimal engagement
                    engaged_features = [
                        _section_to_feature[s]
                        for s in top_sections
                        if s in _section_to_feature
                    ]
                    if engaged_features:
                        await learn_from_interaction(
                            user_id=user_id,
                            interaction_type="passive_engagement",
                            destination=_eng_dest,
                            feedback_data={
                                "features": engaged_features,
                                "weight": 0.15,  # lighter than implicit recommendation (0.3)
                                "source": "engagement_tracking",
                                "time_spent_ms": total_ms,
                            },
                        )
                        append_learning_signal(
                            session.planning_data if session else None,
                            signal_type="passive_engagement",
                            destination=_eng_dest,
                            source="engagement_tracking",
                            weight=0.15,
                            features=engaged_features,
                            metadata={
                                "time_spent_ms": total_ms,
                                "sections": top_sections[:3],
                            },
                        )
            except Exception as _eng_exc:
                logger.debug(f"Engagement-based learning failed (non-fatal): {_eng_exc}")

        return {
            "plan_text": plan_text,
            "destinations": ranked_destinations,
            "destination_data": ranked_by_dest,
            "destination_predictions": prefs.get("destination_prediction_map"),
            "destination_depths": prefs.get("destination_depth_map"),
            "preferences": prefs,
            "sources": self._collect_sources(),
            "generated_at": datetime.now().isoformat(),
            "confidence": (
                "building"
                if partial
                else "high" if successful_tasks >= max(1, len(self.research_tasks)) * 0.6 else "medium"
            ),
            "is_partial": partial,
            "proactive_alerts": proactive_alerts,
            "decision_analysis": {
                "evaluations": evaluations,
                "best_destination": evaluations[0]["destination"] if evaluations else None,
                "best_score": (
                    evaluations[0].get(
                        "final_total_score",
                        evaluations[0].get("personalized_total_score", evaluations[0].get("total_score")),
                    )
                    if evaluations else None
                ),
                "ranking_basis": ranking_basis,
                "engagement_summary": engagement_summary or None,
                "active_hypotheses": list(prefs.get("active_hypotheses") or []),
                "hypothesis_recommendations": (
                    dict(prefs.get("hypothesis_recommendations") or {})
                    if isinstance(prefs.get("hypothesis_recommendations"), dict)
                    else None
                ),
                "destination_affinity_recommendations": (
                    list((prefs.get("destination_affinity_recommendations") or {}).get("recommendations") or [])
                    if isinstance(prefs.get("destination_affinity_recommendations"), dict)
                    else None
                ),
            } if evaluations else None,
        }

    async def _ai_plan(self, by_dest: Dict, prefs: Dict, partial: bool = False) -> str:
        """Try LLM synthesis; fall back to structured markdown."""
        try:
            from app.services.ai_providers import AIFactory
            provider = AIFactory.create_from_settings()
            if partial or not provider:
                return self._markdown_plan(by_dest, prefs, partial=partial)

            context_parts = []
            for dest, data in by_dest.items():
                part = [f"\n### {dest}"]
                if "weather" in data:
                    w = data["weather"]
                    summary = w.get("summary") or w.get("weather", {}).get("best_time") or "N/A"
                    part.append(f"- Weather: {summary}")
                    best_months = w.get("best_months") or (w.get("weather") or {}).get("best_months") or []
                    if best_months:
                        part.append(f"- Best months to visit: {', '.join(best_months[:4])}")
                    weather_by_month = (w.get("weather") or {}).get("weather_by_month") or {}
                    if weather_by_month:
                        sample = []
                        for m in ["January", "April", "July", "October"]:
                            if m in weather_by_month:
                                mw = weather_by_month[m]
                                sample.append(f"{m[:3]}: {mw.get('min_c','')}–{mw.get('max_c','')}°C, {mw.get('condition','')}")
                        if sample:
                            part.append(f"- Monthly weather: {'; '.join(sample)}")
                if "visa" in data:
                    v = data["visa"]
                    vs = v.get("visa", {}) if isinstance(v.get("visa"), dict) else {}
                    part.append(f"- Visa: {vs.get('summary') or v.get('summary', 'N/A')}")
                    currency_code = vs.get("currency_code") or v.get("currency_code", "")
                    currency_name = vs.get("currency_name") or v.get("currency_name", "")
                    if currency_code:
                        part.append(f"- Currency: {currency_name} ({currency_code})")
                    languages = vs.get("primary_languages") or v.get("primary_languages") or []
                    if languages:
                        part.append(f"- Language(s): {', '.join(languages[:3])}")
                if "transport" in data:
                    t = data["transport"]
                    transport = t.get("transport", {}) if isinstance(t.get("transport"), dict) else {}
                    overview = transport.get("overview") or t.get("summary", "")
                    if overview:
                        part.append(f"- Getting around: {overview}")
                    metro = transport.get("metro", "")
                    if metro:
                        part.append(f"- Metro/rail tip: {metro}")
                    neighborhoods = transport.get("best_neighborhoods") or []
                    if neighborhoods:
                        hood_names = [n.get("name") for n in neighborhoods[:3] if n.get("name")]
                        if hood_names:
                            part.append(f"- Best neighbourhoods to stay: {', '.join(hood_names)}")
                if "safety" in data:
                    s = data["safety"]
                    safety = s.get("safety", {}) if isinstance(s.get("safety"), dict) else {}
                    rating = safety.get("rating") or s.get("safety_rating")
                    if rating:
                        part.append(f"- Safety rating: {rating}/10")
                if "attractions" in data:
                    picks = data["attractions"].get("top_picks") or data["attractions"].get("attractions") or []
                    names = [p.get("name") or p.get("title") for p in picks[:5] if p.get("name") or p.get("title")]
                    if names:
                        part.append(f"- Top sights: {', '.join(names)}")
                if "hotels" in data:
                    part.append(f"- Hotels: {data['hotels'].get('summary', 'N/A')}")
                if "flights" in data:
                    part.append(f"- Flights: {data['flights'].get('summary', 'N/A')}")
                if "restaurants" in data:
                    part.append(f"- Food: {data['restaurants'].get('summary', 'N/A')}")
                if "web" in data:
                    n = len(data["web"].get("sources") or [])
                    if n:
                        part.append(f"- Web research: {n} sources reviewed")
                context_parts.append("\n".join(part))

            duration = prefs.get("duration", 7)
            budget = prefs.get("budget_level", "moderate")
            interests = ", ".join(prefs.get("interests") or ["general sightseeing"])
            traveling = prefs.get("traveling_with", "traveller(s)")

            # Apply meta-strategy to prefs before building prompt
            strategy = self._meta_strategy or self._strategy_name(prefs)
            if strategy == "personalized_priority":
                weights = prefs.get("learned_feature_weights", {})
                if isinstance(weights, dict):
                    top_features = sorted(weights.items(), key=lambda x: -x[1])[:3]
                    if top_features:
                        prefs.setdefault("strategy_emphasis", [f[0] for f in top_features])
            elif strategy == "destination_discovery":
                prefs.setdefault("strategy_emphasis", ["variety", "exploration"])
            elif strategy == "date_flexible":
                prefs.setdefault("strategy_emphasis", ["value", "weather", "availability"])

            # Build personalization hint from learned profile
            personalization_lines: List[str] = []
            learned_interests = prefs.get("learned_interests") or []
            if learned_interests:
                personalization_lines.append(
                    f"- This traveller has previously shown strong interest in: {', '.join(learned_interests[:4])}."
                )
            feature_weights: Dict[str, float] = prefs.get("learned_feature_weights") or {}
            high_priority = [
                feat for feat, w in feature_weights.items() if isinstance(w, (int, float)) and w >= 0.65
            ]
            low_priority = [
                feat for feat, w in feature_weights.items() if isinstance(w, (int, float)) and w <= 0.25
            ]
            if high_priority:
                personalization_lines.append(
                    f"- Emphasise these aspects in the plan: {', '.join(high_priority[:5])}."
                )
            if low_priority:
                personalization_lines.append(
                    f"- De-emphasise (keep brief): {', '.join(low_priority[:3])}."
                )
            if prefs.get("strategy_emphasis"):
                personalization_lines.append(f"  - Strategy emphasis: {', '.join(prefs['strategy_emphasis'])}")
            personalization_block = (
                f"\n**Personalisation (based on this user's history):**\n"
                + "\n".join(personalization_lines)
                if personalization_lines
                else ""
            )

            prompt = (
                "You are a professional travel planner. Write a comprehensive travel plan.\n\n"
                f"**Trip profile:**\n"
                f"- Destination(s): {', '.join(by_dest)}\n"
                f"- Duration: {duration} days\n"
                f"- Budget: {budget}\n"
                f"- Interests: {interests}\n"
                f"- Travelling as: {traveling}\n"
                f"{personalization_block}\n\n"
                f"**Research findings:**\n{''.join(context_parts)}\n\n"
                "Write a detailed travel plan with these sections (use markdown):\n"
                "1. Executive Summary\n"
                "2. Best Time to Visit & Weather\n"
                "3. Visa & Entry Requirements\n"
                "4. Getting There (flights/transport)\n"
                "5. Where to Stay\n"
                "6. Top Experiences & Attractions\n"
                "7. Food & Dining Highlights\n"
                f"8. Day-by-Day Itinerary ({duration} days)\n"
                "9. Budget Estimate\n"
                "10. Practical Tips\n\n"
                "Tailor recommendations to this traveller's preferences. Be specific and actionable."
            )

            ai_text = await provider.generate(prompt)
            if ai_text and ai_text.strip():
                return ai_text
            return self._markdown_plan(by_dest, prefs, partial=partial)

        except Exception as exc:
            logger.warning(f"AI synthesis failed: {exc}")
            return self._markdown_plan(by_dest, prefs, partial=partial)

    # ── Learning & Knowledge ────────────────────────────────────────────────

    async def _learn_from_research_results(self) -> Dict[str, Any]:
        """Feed completed research results into the DestinationKnowledgeBase."""
        kb = get_knowledge_base()
        learned: List[str] = []
        grouped_results = self._group_results_by_destination(self._preferences)
        for destination, result_group in grouped_results.items():
            payload = self._build_learning_payload(destination, result_group)
            if not any(key in (payload.get("data") or {}) for key in ("weather", "attractions", "flights", "hotels")):
                continue
            try:
                catalog_entry = _DEST_MAP.get(str(destination).strip().lower(), {})
                await kb.learn_from_research(
                    destination=destination,
                    research_result=payload,
                    country=catalog_entry.get("country"),
                    city=_get_destination_city(destination),
                )
                learned.append(destination)
            except Exception as exc:
                logger.warning(f"Learning failed for {destination}: {exc}")
        if learned:
            logger.info(f"Knowledge base updated for: {', '.join(learned)}")
        return {"destinations_learned": learned}

    def _build_learning_payload(self, destination: str, result_group: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"data": {}, "sources": []}

        weather_result = result_group.get("weather") or {}
        raw_weather = weather_result.get("weather") or {}
        if raw_weather:
            payload["data"]["weather"] = {
                "temperature_c": raw_weather.get("temperature_c", raw_weather.get("temperature")),
                "condition": raw_weather.get("condition"),
                "humidity": raw_weather.get("humidity"),
                "recommendation": weather_result.get("summary") or raw_weather.get("recommendation"),
            }

        attractions_result = result_group.get("attractions") or {}
        attractions = attractions_result.get("attractions") or attractions_result.get("top_picks") or []
        if attractions:
            payload["data"]["attractions"] = attractions

        flights_result = result_group.get("flights") or {}
        flights = flights_result.get("flights") or []
        if flights_result.get("best_option") and flights_result["best_option"] not in flights:
            flights = [flights_result["best_option"], *flights]
        if flights:
            payload["data"]["flights"] = flights

        hotels_result = result_group.get("hotels") or {}
        hotels = hotels_result.get("hotels") or hotels_result.get("top_picks") or []
        if hotels:
            normalized_hotels = []
            for hotel in hotels:
                if isinstance(hotel, dict):
                    normalized_hotels.append(
                        {
                            **hotel,
                            "price_per_night": hotel.get("price_per_night", hotel.get("price")),
                        }
                    )
            payload["data"]["hotels"] = normalized_hotels

        payload["data"]["context"] = {
            "destination": destination,
            "interests": list(self._preferences.get("interests") or []),
            "budget_level": self._preferences.get("budget_level"),
        }
        payload["sources"] = list(self._collect_sources())
        return payload

    async def _check_knowledge_cache(self, task: ResearchTask) -> Optional[Dict[str, Any]]:
        """Check if DestinationKnowledgeBase has fresh data for this task."""
        if not task.destination:
            return None
        try:
            kb = get_knowledge_base()
            refresh_status = await kb.needs_refresh(task.destination, task.type)
            if refresh_status.get("needs_refresh"):
                return None
            knowledge = await kb.get_complete_knowledge(task.destination)
            if not knowledge.get("available"):
                return None
            confidence = knowledge.get("confidence", 0)
            if confidence < 0.5:
                return None
            data = knowledge.get("data", {})
            if not data:
                return None

            # Map task type to cached knowledge fields
            if task.type == "weather" and (data.get("best_time_to_visit") or data.get("best_months")):
                best_months = data.get("best_months") or []
                summary = data.get("best_time_to_visit") or (
                    f"Best months: {', '.join(best_months[:4])}" if best_months else "Cached seasonal guidance available"
                )
                return {
                    "destination": task.destination,
                    "weather": {
                        "best_time": data.get("best_time_to_visit", ""),
                        "best_months": best_months,
                        "weather_by_month": data.get("weather_by_month") or {},
                    },
                    "summary": summary,
                    "from_cache": True,
                }
            if task.type == "attractions" and data.get("popular_attractions"):
                picks = data["popular_attractions"] if isinstance(data["popular_attractions"], list) else []
                if picks:
                    return {
                        "destination": task.destination,
                        "attractions": picks,
                        "top_picks": picks[:5],
                        "summary": f"{len(picks[:5])} top attractions in {task.destination}",
                        "from_cache": True,
                    }
            if task.type == "flights" and data.get("avg_flight_price"):
                return {
                    "destination": task.destination,
                    "flights": [{"price": data["avg_flight_price"], "currency": "USD"}],
                    "best_option": {"price": data["avg_flight_price"], "currency": "USD"},
                    "summary": f"Typical flights around ${float(data['avg_flight_price']):.0f}",
                    "from_cache": True,
                }
            if task.type == "hotels" and data.get("avg_hotel_price"):
                return {
                    "destination": task.destination,
                    "hotels": [{"price_per_night": data["avg_hotel_price"], "currency": "USD"}],
                    "top_picks": [],
                    "summary": f"Typical hotels around ${float(data['avg_hotel_price']):.0f}/night",
                    "from_cache": True,
                }
            if task.type == "visa" and data.get("visa_summary"):
                visa_requirement = "visa_on_arrival" if data.get("visa_on_arrival") else (
                    "visa_free" if data.get("visa_free_countries") else "advance_check_required"
                )
                return {
                    "destination": task.destination,
                    "country": data.get("country"),
                    "visa": {
                        "requirement": visa_requirement,
                        "visa_on_arrival": bool(data.get("visa_on_arrival")),
                        "visa_free_countries": data.get("visa_free_countries") or [],
                        "summary": data.get("visa_summary"),
                        "currency_code": data.get("currency_code", ""),
                        "currency_name": data.get("currency_name", ""),
                        "primary_languages": data.get("primary_languages") or [],
                    },
                    "summary": data["visa_summary"],
                    "from_cache": True,
                }
            if task.type == "transport" and data.get("transport_tips"):
                tips = data["transport_tips"] if isinstance(data["transport_tips"], dict) else {}
                neighborhoods = data.get("best_neighborhoods") or []
                return {
                    "destination": task.destination,
                    "transport": {
                        "overview": tips.get("overview", ""),
                        "metro": tips.get("metro", ""),
                        "taxi": tips.get("taxi", ""),
                        "airport_transfer": tips.get("airport_transfer", ""),
                        "best_neighborhoods": neighborhoods,
                    },
                    "summary": f"Transport & neighborhoods for {task.destination}",
                    "from_cache": True,
                }
            if task.type == "safety" and (data.get("safety_rating") or data.get("safety_notes")):
                rating = data.get("safety_rating")
                return {
                    "destination": task.destination,
                    "safety": {
                        "rating": rating,
                        "notes": data.get("safety_notes", ""),
                    },
                    "summary": f"Safety rating {rating}/10 for {task.destination}" if rating else f"Safety info for {task.destination}",
                    "from_cache": True,
                }
            return None
        except Exception as exc:
            logger.debug(f"Knowledge cache check failed for {task.destination}: {exc}")
            return None

    def _markdown_plan(self, by_dest: Dict, prefs: Dict, partial: bool = False) -> str:
        lines = ["# Live Travel Plan\n" if partial else "# Your Personalised Travel Plan\n"]
        duration = prefs.get("duration", 7)
        budget = prefs.get("budget_level", "moderate")
        lines.append(f"**Duration:** {duration} days | **Budget:** {budget.title()}\n")
        if partial:
            lines.append("*This plan is still being assembled as new research completes.*\n")

        for dest, data in by_dest.items():
            lines.append(f"\n---\n## {dest}\n")

            for section, key, label in [
                ("weather", "summary", "Weather"),
                ("visa", "summary", "Visa Requirements"),
                ("flights", "summary", "Flights"),
            ]:
                if section in data:
                    lines.append(f"### {label}\n{data[section].get(key, 'N/A')}\n")

            for section, key, label in [
                ("attractions", "top_picks", "Top Attractions"),
                ("hotels", "top_picks", "Where to Stay"),
                ("restaurants", "top_picks", "Food & Dining"),
                ("events", "highlights", "Local Events"),
            ]:
                if section in data:
                    picks = data[section].get(key) or []
                    if picks:
                        lines.append(f"### {label}")
                        for item in picks[:5]:
                            name = item.get("name") or item.get("title") or "–"
                            lines.append(f"- {name}")
                        lines.append("")

            if "transport" in data:
                t = data["transport"]
                transport = t.get("transport", {}) if isinstance(t.get("transport"), dict) else {}
                overview = transport.get("overview") or t.get("summary", "")
                if overview:
                    lines.append(f"### Getting Around\n{overview}\n")
                neighborhoods = transport.get("best_neighborhoods") or []
                if neighborhoods:
                    lines.append("### Neighbourhoods")
                    for n in neighborhoods[:3]:
                        lines.append(f"- **{n.get('name', '')}** — {n.get('best_for', '')}")
                    lines.append("")

            if "safety" in data:
                s = data["safety"]
                safety = s.get("safety", {}) if isinstance(s.get("safety"), dict) else {}
                rating = safety.get("rating") or s.get("safety_rating")
                notes = safety.get("notes") or s.get("safety_notes", "")
                if rating or notes:
                    lines.append(f"### Safety\nRating: {rating}/10\n{notes}\n")

            if "web" in data:
                sources = data["web"].get("sources") or []
                if sources:
                    lines.append("### Research Sources")
                    for s in sources[:4]:
                        t, u = s.get("title", ""), s.get("url", "")
                        lines.append(f"- [{t}]({u})" if t and u else f"- {t or u}")
                    lines.append("")

        lines.append("\n---\n*Always verify visa requirements with official embassy sources.*")
        return "\n".join(lines)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _task_label(self, task: ResearchTask) -> str:
        if task.type == "web_search":
            queries = task.params.get("queries") or []
            q = f'"{queries[0]}"' if queries else task.destination
            return f"Searching web: {q}"
        return {
            "weather": f"Checking weather for {task.destination}",
            "visa": f"Looking up visa requirements for {task.destination}",
            "attractions": f"Finding attractions in {task.destination}",
            "flights": f"Searching flights to {task.destination}",
            "hotels": f"Finding hotels in {task.destination}",
            "events": f"Checking events in {task.destination}",
            "restaurants": f"Finding food and dining in {task.destination}",
        }.get(task.type, f"Researching {task.destination}")

    def _brief(self, task: ResearchTask) -> str:
        r = task.result or {}
        return r.get("summary", "Completed" if task.status == "completed" else "Failed")

    def _collect_sources(self) -> List[Dict]:
        seen: set = set()
        out: List[Dict] = []
        for result in self.research_results.values():
            if isinstance(result, dict):
                for s in (result.get("sources") or []):
                    url = s.get("url", "")
                    if url and url not in seen:
                        seen.add(url)
                        out.append(s)
        return out[:10]


# ── Utilities ────────────────────────────────────────────────────────────────

def _priority_num(p: ResearchPriority) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(p.value, 99)


def _preview(result: Dict) -> Dict:
    """Return a lightweight dict safe for JSON streaming."""
    keys = (
        "summary",
        "destination",
        "top_picks",
        "sources",
        "highlights",
        "queries_run",
        "food_scene",
    )
    return {k: result[k] for k in keys if k in result}
