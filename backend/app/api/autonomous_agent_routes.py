"""
Autonomous Agent API Routes
===========================

RESTful API endpoints for the autonomous AI travel agent.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import time
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import PersistedChatSession
from app.utils.destination_affinity_graph import get_destination_affinity_graph
from app.utils.logging_config import get_logger
from app.utils.datetime_utils import utcnow_naive
from app.utils.hypothesis_engine import get_hypothesis_engine
from app.utils.meta_learner import get_meta_learner
from app.services.proactive_agent import get_proactive_agent
from app.utils.user_style_classifier import get_user_style_classifier
from app.services.autonomous_agent import (
    AgentState,
    AutonomousAgent,
    append_learning_signal,
    cancel_execution,
    get_autonomous_agent,
    summarize_learning_signals,
)
from app.utils.destination_knowledge_base import get_knowledge_base

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/autonomous-agent", tags=["Autonomous Agent"])

# ── Simple in-process rate limiter ───────────────────────────────────────────
# Allows MAX_REQUESTS per WINDOW_SECONDS per IP address.
_RATE_MAX = 10        # requests
_RATE_WINDOW = 60     # seconds
_rate_store: Dict[str, list] = defaultdict(list)


def _check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - _RATE_WINDOW
    # Drop timestamps outside the current window
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]
    if len(_rate_store[ip]) >= _RATE_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {_RATE_MAX} requests per {_RATE_WINDOW}s."
        )
    _rate_store[ip].append(now)


class AutonomousAgentRequest:
    """Request model for autonomous agent."""
    
    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.session_id = session_id or f"session_{datetime.now().timestamp()}"
        self.user_id = user_id
        self.config = config or {}


def _new_agent() -> AutonomousAgent:
    """Create a fresh agent per request to prevent cross-session state bleed."""
    return AutonomousAgent()


def _get_session_runtime(session: Any) -> Dict[str, Any]:
    runtime = session.planning_data.get("autonomous_runtime") or {}
    return runtime if isinstance(runtime, dict) else {}


def _get_runtime_metrics(runtime: Dict[str, Any]) -> Dict[str, Any]:
    metrics = runtime.get("research_metrics") or {}
    if isinstance(metrics, dict):
        return metrics
    plan = runtime.get("plan") or {}
    if isinstance(plan, dict):
        fallback = plan.get("research_metrics") or {}
        if isinstance(fallback, dict):
            return fallback
    return {}


def _safe_average(total: float, count: int) -> float:
    if count <= 0:
        return 0.0
    return round(total / count, 2)


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _alert_signature(alert: Dict[str, Any], created_at: str, session_id: str) -> str:
    return "|".join([
        session_id,
        created_at,
        str(alert.get("title") or "").strip().lower(),
        str(alert.get("message") or "").strip().lower(),
        str(alert.get("destination") or "").strip().lower(),
        str(alert.get("source") or "").strip().lower(),
    ])


def _extract_autonomous_notifications(
    *,
    session_id: str,
    session_updated_at: Optional[datetime],
    planning_data: Dict[str, Any],
    runtime: Dict[str, Any],
) -> list[Dict[str, Any]]:
    notifications: list[Dict[str, Any]] = []
    seen_signatures: set[str] = set()

    monitoring = planning_data.get("autonomous_monitoring") or {}
    monitoring = monitoring if isinstance(monitoring, dict) else {}
    last_viewed_at = _parse_iso_datetime(monitoring.get("last_viewed_at"))
    state = str(runtime.get("state") or "idle")
    plan = runtime.get("plan") or {}
    plan = plan if isinstance(plan, dict) else {}
    default_destinations = plan.get("destinations") or runtime.get("preferences", {}).get("destinations") or []
    if not isinstance(default_destinations, list):
        default_destinations = []

    def append_alert(alert: Any, checked_at: Optional[str] = None) -> None:
        if not isinstance(alert, dict):
            return
        created_at = str(
            alert.get("created_at")
            or checked_at
            or (session_updated_at.isoformat() if session_updated_at else utcnow_naive().isoformat())
        )
        created_dt = _parse_iso_datetime(created_at) or session_updated_at or utcnow_naive()
        signature = _alert_signature(alert, created_at, session_id)
        if signature in seen_signatures:
            return
        seen_signatures.add(signature)

        destination = str(alert.get("destination") or "").strip()
        if not destination and default_destinations:
            destination = str(default_destinations[0]).strip()

        notifications.append(
            {
                "notification_id": signature,
                "session_id": session_id,
                "title": str(alert.get("title") or "Autonomous trip update").strip(),
                "message": str(alert.get("message") or "").strip(),
                "severity": str(alert.get("severity") or "info").strip().lower(),
                "destination": destination,
                "source": str(alert.get("source") or "").strip(),
                "created_at": created_dt.isoformat(),
                "trip_state": state,
                "unread": last_viewed_at is None or created_dt > last_viewed_at,
            }
        )

    history = planning_data.get("proactive_alert_history") or []
    if isinstance(history, list):
        for entry in history:
            if not isinstance(entry, dict):
                continue
            checked_at = str(entry.get("checked_at") or "").strip() or None
            alerts = entry.get("alerts") or []
            if isinstance(alerts, list):
                for alert in alerts:
                    append_alert(alert, checked_at)

    current_alerts = (
        planning_data.get("proactive_alerts")
        or plan.get("proactive_alerts")
        or []
    )
    if isinstance(current_alerts, list):
        for alert in current_alerts:
            append_alert(alert)

    notifications.sort(key=lambda item: item["created_at"], reverse=True)
    return notifications


def _parse_autonomous_session_payload(payload: str) -> Optional[Dict[str, Any]]:
    try:
        raw = json.loads(payload or "{}")
    except json.JSONDecodeError:
        return None

    if not isinstance(raw, dict):
        return None

    planning_data = raw.get("planning_data") or {}
    if not isinstance(planning_data, dict):
        return None

    runtime = planning_data.get("autonomous_runtime") or {}
    if not isinstance(runtime, dict) or not runtime:
        return None

    extracted_preferences = raw.get("extracted_preferences") or {}
    if not isinstance(extracted_preferences, dict):
        extracted_preferences = {}

    runtime_preferences = runtime.get("preferences") or {}
    if not isinstance(runtime_preferences, dict):
        runtime_preferences = {}

    plan = runtime.get("plan") or {}
    if not isinstance(plan, dict):
        plan = {}

    destinations = extracted_preferences.get("destinations") or runtime_preferences.get("destinations") or plan.get("destinations") or []
    if not isinstance(destinations, list):
        destinations = []

    return {
        "runtime": runtime,
        "planning_data": planning_data,
        "metrics": _get_runtime_metrics(runtime),
        "destinations": [str(destination).strip() for destination in destinations if str(destination).strip()],
    }


def _extract_priority_tasks(runtime: Dict[str, Any]) -> List[Dict[str, Any]]:
    seen_ids: set[str] = set()
    extracted: List[Dict[str, Any]] = []

    for collection_name in ("tasks", "completed_tasks"):
        tasks = runtime.get(collection_name) or []
        if not isinstance(tasks, list):
            continue

        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue

            task_id = str(task.get("id") or "").strip() or f"{collection_name}:{index}"
            if task_id in seen_ids:
                continue
            seen_ids.add(task_id)

            try:
                priority_score = round(float(task.get("priority_score") or 0.0), 2)
            except (TypeError, ValueError):
                priority_score = 0.0

            extracted.append(
                {
                    "task_type": str(task.get("type") or "unknown").strip() or "unknown",
                    "destination": str(task.get("destination") or "").strip(),
                    "priority": str(task.get("priority") or "unknown").strip().lower() or "unknown",
                    "priority_score": priority_score,
                    "status": str(task.get("status") or "pending").strip().lower() or "pending",
                    "backup_for": str((task.get("params") or {}).get("backup_for") or "").strip(),
                    "fallback_reason": str((task.get("params") or {}).get("fallback_reason") or "").strip(),
                    "top_error_kind": str((task.get("params") or {}).get("top_error_kind") or "").strip(),
                }
            )

    return extracted


def _recent_learning_signals(planning_data: Dict[str, Any], limit: int = 8) -> List[Dict[str, Any]]:
    raw_signals = planning_data.get("learning_signals") or []
    if not isinstance(raw_signals, list):
        return []

    recent: List[Dict[str, Any]] = []
    for signal in reversed(raw_signals[-limit:]):
        if not isinstance(signal, dict):
            continue
        recent.append(
            {
                "type": str(signal.get("type") or "unknown").strip().lower() or "unknown",
                "destination": str(signal.get("destination") or "").strip(),
                "source": str(signal.get("source") or "unknown").strip().lower() or "unknown",
                "weight": signal.get("weight"),
                "features": signal.get("features") if isinstance(signal.get("features"), list) else [],
                "timestamp": str(signal.get("timestamp") or "").strip(),
            }
        )
    return recent


def _normalize_learning_feature(value: Any) -> Optional[str]:
    text = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
    if not text:
        return None

    keyword_map = {
        "food": ["food", "restaurant", "dining", "cuisine", "street food", "eat"],
        "weather": ["weather", "climate", "sunny", "warm", "cold", "rain"],
        "attractions": ["attraction", "sightseeing", "museum", "landmark", "things to do"],
        "visa_ease": ["visa", "entry", "passport"],
        "flight_time": ["flight", "airport", "layover", "nonstop"],
        "price": ["price", "budget", "cost", "affordable", "hotel"],
        "nightlife": ["nightlife", "bar", "club", "party"],
        "family": ["family", "kids", "children"],
        "culture": ["culture", "history", "art", "architecture"],
        "beach": ["beach", "island", "coast", "seaside"],
        "nature": ["nature", "hiking", "mountain", "park", "outdoors"],
        "luxury": ["luxury", "premium", "resort", "upscale"],
    }
    alias_map = {
        "restaurants": "food",
        "restaurant": "food",
        "dining": "food",
        "events": "nightlife",
        "flights": "flight_time",
        "visa": "visa_ease",
        "hotels": "price",
        "hotel": "price",
        "history": "culture",
        "art": "culture",
    }
    if text in alias_map:
        return alias_map[text]
    if text in keyword_map:
        return text
    for canonical, keywords in keyword_map.items():
        if any(keyword in text for keyword in keywords):
            return canonical
    return None


def _extract_feedback_features(session: Optional[Any], destination: str, comment: str) -> list[str]:
    features: list[str] = []

    def add_feature(value: Any) -> None:
        normalized = _normalize_learning_feature(value)
        if normalized and normalized not in features:
            features.append(normalized)

    if not session:
        if comment:
            add_feature(comment)
        return features

    prefs = session.extracted_preferences if isinstance(session.extracted_preferences, dict) else {}
    runtime = _get_session_runtime(session)
    plan = runtime.get("plan") if isinstance(runtime, dict) else {}
    plan = plan if isinstance(plan, dict) else {}
    destination_data = plan.get("destination_data") if isinstance(plan.get("destination_data"), dict) else {}

    target_key = destination if destination in destination_data else None
    if target_key is None:
        for key in destination_data.keys():
            if str(key).strip().lower() == str(destination).strip().lower():
                target_key = key
                break

    if target_key is not None:
        data = destination_data.get(target_key)
        if isinstance(data, dict):
            for section in data.keys():
                add_feature(section)

    for interest in (prefs.get("interests") or []):
        add_feature(interest)
    for interest in (prefs.get("learned_interests") or []):
        add_feature(interest)

    budget_level = str(prefs.get("budget_level") or "").strip().lower()
    if budget_level in {"budget", "low", "moderate"}:
        add_feature("price")
        add_feature("budget")
    elif budget_level in {"high", "luxury"}:
        add_feature("luxury")

    if comment:
        add_feature(comment)

    return features


def _build_hypothesis_research_snapshot(
    session: Optional[Any],
    destination: str,
    features: list[str],
) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {}
    if not session:
        if features:
            snapshot["features"] = list(dict.fromkeys(features))
        return snapshot

    runtime = _get_session_runtime(session)
    plan = runtime.get("plan") if isinstance(runtime, dict) else {}
    plan = plan if isinstance(plan, dict) else {}
    destination_data = plan.get("destination_data") if isinstance(plan.get("destination_data"), dict) else {}

    target_key = destination if destination in destination_data else None
    if target_key is None:
        for key in destination_data.keys():
            if str(key).strip().lower() == str(destination).strip().lower():
                target_key = key
                break

    if target_key is not None and isinstance(destination_data.get(target_key), dict):
        snapshot.update(destination_data[target_key])

    derived_features: list[str] = []
    for feature in features:
        normalized = _normalize_learning_feature(feature)
        if normalized and normalized not in derived_features:
            derived_features.append(normalized)
    for section in snapshot.keys():
        normalized = _normalize_learning_feature(section)
        if normalized and normalized not in derived_features:
            derived_features.append(normalized)

    if derived_features:
        snapshot["features"] = derived_features

    # ── Inject decision engine criteria scores ──────────────────────
    # These let the hypothesis engine build causal hypotheses like
    # "rejected Bangkok → lowest criterion was safety (0.35)".
    decision_analysis = plan.get("decision_analysis") if isinstance(plan, dict) else None
    if isinstance(decision_analysis, dict):
        evaluations = decision_analysis.get("evaluations") or []
        for ev in evaluations:
            if not isinstance(ev, dict):
                continue
            ev_dest = str(ev.get("destination") or "").strip().lower()
            if ev_dest == str(destination).strip().lower():
                criteria_scores = ev.get("criteria_scores") or ev.get("scores") or {}
                if criteria_scores:
                    snapshot["criteria_scores"] = dict(criteria_scores)
                    # Extract weak criteria (< 0.4) for direct hypothesis use
                    weak_criteria = [
                        k for k, v in criteria_scores.items()
                        if isinstance(v, (int, float)) and v < 0.4
                    ]
                    if weak_criteria:
                        snapshot["weak_criteria"] = weak_criteria
                        # Add them to features so hypothesis engine can pattern-match
                        for wc in weak_criteria:
                            neg_feature = f"low_{wc}"
                            if neg_feature not in derived_features:
                                derived_features.append(neg_feature)
                        snapshot["features"] = derived_features
                break

    return snapshot


def _normalize_feedback_score(rating: Optional[str], score: Optional[Any]) -> int:
    try:
        if score is not None:
            numeric = int(score)
            if 1 <= numeric <= 5:
                return numeric
    except (TypeError, ValueError):
        pass

    normalized_rating = str(rating or "").strip().lower()
    if normalized_rating == "positive":
        return 5
    if normalized_rating == "negative":
        return 1
    if normalized_rating == "neutral":
        return 3
    raise HTTPException(status_code=400, detail="Provide rating=positive|negative|neutral or score=1..5")


def _feedback_signal_weight(score: int, engagement_ms: int = 0) -> float:
    base = {
        1: -1.0,
        2: -0.55,
        3: 0.0,
        4: 0.55,
        5: 0.95,
    }.get(int(score), 0.0)
    engagement_bonus = min(0.2, max(0.0, float(engagement_ms) / 120000.0))
    if base > 0:
        return round(min(1.1, base + engagement_bonus), 2)
    if base < 0:
        return round(max(-1.1, base - engagement_bonus), 2)
    return 0.0


@router.post("/chat")
async def chat_with_agent(
    request: Dict[str, Any],
    http_request: Request,
    agent: AutonomousAgent = Depends(_new_agent),
):
    _check_rate_limit(http_request)
    """
    Send a message to the autonomous agent.
    
    The agent will:
    1. Understand your message
    2. Extract travel preferences
    3. Autonomously research destinations
    4. Present a comprehensive plan
    
    **Request:**
    ```json
    {
        "message": "I want a beach vacation in Thailand for 2 weeks in December",
        "session_id": "optional-session-id",
        "user_id": "optional-user-id"
    }
    ```
    
    **Response:**
    ```json
    {
        "session_id": "session_123",
        "response": "I'll help you plan your Thailand trip...",
        "extracted_preferences": {...},
        "research_status": "in_progress",
        "progress": 45
    }
    ```
    """
    try:
        session_id = request.get("session_id") or f"session_{datetime.now().timestamp()}"
        message = request.get("message", "")
        user_id = request.get("user_id")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Start conversation with agent
        response_chunks = []
        async for chunk in agent.start_conversation(session_id, message, user_id=user_id):
            response_chunks.append(chunk)
        
        # Get last response
        last_response = response_chunks[-1] if response_chunks else {}
        
        return {
            "session_id": session_id,
            "response": last_response.get("content", last_response.get("message", "")),
            "extracted_preferences": agent.current_session.extracted_preferences if agent.current_session else {},
            "research_status": agent.state.value,
            "progress": agent.progress_percentage,
            "research_results": agent.research_results,
            "state": agent.state.value
        }
        
    except Exception as e:
        logger.error(f"Autonomous agent chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_with_agent_stream(
    request: Dict[str, Any],
    http_request: Request,
    agent: AutonomousAgent = Depends(_new_agent),
):
    _check_rate_limit(http_request)
    """
    Stream responses from the autonomous agent (Server-Sent Events).
    
    Provides real-time updates as the agent:
    - Listens to your message
    - Plans research
    - Executes research tasks
    - Synthesizes findings
    - Presents the plan
    
    **Example:**
    ```javascript
    const response = await fetch('/api/v1/autonomous-agent/chat/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            message: "Plan a trip to Japan"
        })
    });
    
    const reader = response.body.getReader();
    // Read SSE events...
    ```
    """
    session_id = request.get("session_id") or f"session_{datetime.now().timestamp()}"
    message = request.get("message", "")
    user_id = request.get("user_id")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    async def generate_stream():
        """Generate SSE stream."""
        try:
            async for chunk in agent.start_conversation(session_id, message, user_id=user_id):
                # Format as SSE event
                event_data = json.dumps(chunk)
                yield f"data: {event_data}\n\n"
            
            # Send completion signal — reflect agent's true final state
            yield f"data: {json.dumps({'type': 'done', 'state': agent.state.value, 'session_id': session_id})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/session/{session_id}")
async def get_session_info(
    session_id: str,
    agent: AutonomousAgent = Depends(_new_agent)
):
    """
    Get current session state and research progress.
    
    **Response:**
    ```json
    {
        "session_id": "session_123",
        "state": "researching",
        "progress": 65,
        "current_task": {...},
        "completed_tasks": [...],
        "research_results": {...}
    }
    ```
    """
    session = await agent.chat_service._load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    runtime = _get_session_runtime(session)
    tasks = runtime.get("tasks") or []
    learning_signal_summary = summarize_learning_signals(session.planning_data)

    return {
        "session_id": session_id,
        "state": runtime.get("state", "idle"),
        "progress": runtime.get("progress", 0),
        "current_task": runtime.get("current_task"),
        "completed_tasks": runtime.get("completed_tasks", []),
        "pending_tasks": [task for task in tasks if task.get("status") == "pending"],
        "research_results": runtime.get("research_results", {}),
        "extracted_preferences": session.extracted_preferences,
        "plan": runtime.get("plan"),
        "proactive_alerts": (runtime.get("plan") or {}).get("proactive_alerts") or session.planning_data.get("proactive_alerts", []),
        "research_metrics": _get_runtime_metrics(runtime),
        "learning_signal_summary": learning_signal_summary,
        "learning_signals": _recent_learning_signals(session.planning_data),
    }


@router.post("/session/{session_id}/continue")
async def continue_research(
    session_id: str,
    request: Dict[str, Any],
    agent: AutonomousAgent = Depends(_new_agent)
):
    """
    Continue research with additional information.
    
    Use this when the agent asked for clarification and you're providing it.
    
    **Request:**
    ```json
    {
        "message": "My budget is moderate and I'm traveling with my family"
    }
    ```
    """
    message = request.get("message", "")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Load existing session
    session = await agent.chat_service._load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent.current_session = session
    
    # Continue conversation
    response_chunks = []
    async for chunk in agent.start_conversation(session_id, message, user_id=session.user_id):
        response_chunks.append(chunk)
    
    last_response = response_chunks[-1] if response_chunks else {}
    
    return {
        "session_id": session_id,
        "response": last_response.get("content", last_response.get("message", "")),
        "state": agent.state.value,
        "progress": agent.progress_percentage,
        "research_results": agent.research_results
    }


@router.get("/session/{session_id}/plan")
async def get_travel_plan(
    session_id: str,
    agent: AutonomousAgent = Depends(_new_agent)
):
    """
    Get the comprehensive travel plan generated by the agent.
    
    Returns the final synthesized plan with all research findings.
    
    **Response:**
    ```json
    {
        "plan": {
            "plan_text": "## Executive Summary\\n\\nYour perfect trip...",
            "destinations": ["Tokyo", "Kyoto"],
            "confidence": "high",
            "generated_at": "2024-03-10T12:00:00"
        },
        "research_data": {...}
    }
    ```
    """
    # Load session
    session = await agent.chat_service._load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent.current_session = session
    runtime = _get_session_runtime(session)
    if runtime.get("plan"):
        return {
            "plan": runtime["plan"],
            "research_data": runtime.get("research_results", {}),
            "session_id": session_id,
            "research_metrics": _get_runtime_metrics(runtime),
        }

    state = runtime.get("state", agent.state.value)
    if state not in ["completed", "presenting", "synthesizing", "cancelled"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Research not yet complete. Current state: {state}"
        )

    agent.research_results = runtime.get("research_results", {})
    agent._preferences = session.extracted_preferences or runtime.get("preferences", {})
    plan = await agent._synthesize_plan(session, partial=state == "cancelled")
    runtime["plan"] = plan
    session.planning_data["autonomous_runtime"] = runtime
    await agent.chat_service._save_session(session)
    
    return {
        "plan": plan,
        "research_data": runtime.get("research_results", agent.research_results),
        "session_id": session_id,
        "research_metrics": _get_runtime_metrics(runtime),
    }


@router.get("/session/{session_id}/proactive-suggestions")
async def get_proactive_suggestions(
    session_id: str,
    agent: AutonomousAgent = Depends(_new_agent),
):
    session = await agent.chat_service._load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    runtime = _get_session_runtime(session)
    preferences = runtime.get("preferences") or session.extracted_preferences or {}
    research_data = runtime.get("research_results") or {}

    proactive_agent = get_proactive_agent()
    alerts = await proactive_agent.monitor_and_alert(
        session_id=session_id,
        user_id=session.user_id,
        preferences=preferences,
        research_data=research_data,
    )
    alert_payload = [alert.to_dict() for alert in alerts]
    session.planning_data["proactive_alerts"] = alert_payload

    plan = runtime.get("plan")
    if isinstance(plan, dict):
        updated_plan = dict(plan)
        updated_plan["proactive_alerts"] = alert_payload
        runtime["plan"] = updated_plan
        session.planning_data["autonomous_runtime"] = runtime

    await agent.chat_service._save_session(session)

    return {
        "session_id": session_id,
        "alerts": alert_payload,
        "count": len(alert_payload),
    }


@router.get("/notifications")
async def get_autonomous_notifications(
    user_id: str = Query(..., min_length=1, description="Durable user identifier"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of alert notifications to return"),
    unread_only: bool = Query(False, description="Only return unread notifications"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PersistedChatSession)
        .filter(PersistedChatSession.user_id == user_id)
        .order_by(PersistedChatSession.updated_at.desc())
        .all()
    )

    notifications: list[Dict[str, Any]] = []
    unread_count = 0

    for row in rows:
        parsed = _parse_autonomous_session_payload(row.payload)
        if not parsed:
            continue
        session_notifications = _extract_autonomous_notifications(
            session_id=row.session_id,
            session_updated_at=row.updated_at,
            planning_data=(json.loads(row.payload).get("planning_data") or {}) if row.payload else {},
            runtime=parsed["runtime"],
        )
        for notification in session_notifications:
            if notification["unread"]:
                unread_count += 1
            if unread_only and not notification["unread"]:
                continue
            notifications.append(notification)

    notifications.sort(key=lambda item: item["created_at"], reverse=True)
    return {
        "user_id": user_id,
        "unread_count": unread_count,
        "total_notifications": len(notifications),
        "notifications": notifications[:limit],
    }


@router.post("/notifications/mark-seen")
async def mark_autonomous_notifications_seen(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    agent: AutonomousAgent = Depends(_new_agent),
):
    user_id = str(request.get("user_id") or "").strip()
    session_id = str(request.get("session_id") or "").strip() or None
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    query = db.query(PersistedChatSession).filter(PersistedChatSession.user_id == user_id)
    if session_id:
        query = query.filter(PersistedChatSession.session_id == session_id)
    rows = query.all()

    marked_at = utcnow_naive().isoformat()
    updated_sessions = 0

    for row in rows:
        session = await agent.chat_service._load_session(row.session_id)
        if not session or session.user_id != user_id:
            continue
        monitoring = session.planning_data.get("autonomous_monitoring") or {}
        monitoring = dict(monitoring) if isinstance(monitoring, dict) else {}
        monitoring["last_viewed_at"] = marked_at
        session.planning_data["autonomous_monitoring"] = monitoring
        await agent.chat_service._save_session(session)
        updated_sessions += 1

    return {
        "user_id": user_id,
        "session_id": session_id,
        "updated_sessions": updated_sessions,
        "marked_at": marked_at,
    }


@router.post("/session/{session_id}/cancel")
async def cancel_research(
    session_id: str,
    agent: AutonomousAgent = Depends(_new_agent)
):
    """
    Cancel ongoing research.
    
    Stops all autonomous research tasks and returns partial results.
    """
    session = await agent.chat_service._load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    runtime = _get_session_runtime(session)
    cancel_requested = cancel_execution(session_id)
    active_states = {"listening", "planning", "researching", "synthesizing", "presenting"}
    current_state = runtime.get("state", "idle")

    if not cancel_requested and current_state not in active_states:
        return {
            "session_id": session_id,
            "status": "not_running",
            "partial_results": runtime.get("research_results", {}),
            "plan": runtime.get("plan"),
        }

    updated_tasks = []
    for task in runtime.get("tasks") or []:
        item = dict(task)
        if item.get("status") in {"pending", "in_progress"}:
            item["status"] = "cancelled"
        updated_tasks.append(item)
    completed_tasks = [
        dict(task)
        for task in updated_tasks
        if task.get("status") in {"completed", "failed", "cancelled"}
    ]

    plan = runtime.get("plan")
    if isinstance(plan, dict):
        plan = dict(plan)
        plan["is_partial"] = True

    agent.state = AgentState.CANCELLED
    agent.current_task = None

    runtime.update({
        "state": AgentState.CANCELLED.value,
        "current_task": None,
        "tasks": updated_tasks,
        "completed_tasks": completed_tasks,
        "plan": plan,
    })
    session.planning_data["autonomous_runtime"] = runtime
    await agent.chat_service._save_session(session)

    return {
        "session_id": session_id,
        "status": "cancelled",
        "partial_results": runtime.get("research_results", {}),
        "plan": plan,
        "cancel_requested": cancel_requested,
        "research_metrics": _get_runtime_metrics(runtime),
    }


@router.post("/session/{session_id}/feedback")
async def submit_plan_feedback(
    session_id: str,
    request: Dict[str, Any],
    http_request: Request,
    agent: AutonomousAgent = Depends(_new_agent),
):
    """
    Submit feedback on a generated travel plan.

    **Request:**
    ```json
    {
        "rating": "positive" | "negative",
        "destination": "Paris",
        "comment": "optional free-text"
    }
    ```
    """
    _check_rate_limit(http_request)
    rating = request.get("rating", "")
    score = request.get("score")
    destination = request.get("destination", "unknown")
    comment = request.get("comment", "")
    feedback_score = _normalize_feedback_score(rating, score)
    normalized_rating = "positive" if feedback_score >= 4 else "negative" if feedback_score <= 2 else "neutral"

    try:
        from app.utils.learning_agent import learn_from_interaction

        session = await agent.chat_service._load_session(session_id)
        learner_id = session.user_id if session and session.user_id else "anonymous"
        features = _extract_feedback_features(session, destination, comment)
        engagement_log = session.planning_data.get("engagement_log") if session else []
        destination_engagement_ms = 0
        if isinstance(engagement_log, list):
            for evt in engagement_log:
                if str(evt.get("destination") or "").strip().lower() != str(destination).strip().lower():
                    continue
                try:
                    destination_engagement_ms += int(evt.get("time_spent_ms", evt.get("duration_ms", 0)) or 0)
                except (TypeError, ValueError):
                    continue

        interaction_type = "like" if feedback_score >= 4 else "dislike" if feedback_score <= 2 else None
        user_accepted = feedback_score >= 4
        feedback_weight = _feedback_signal_weight(feedback_score, destination_engagement_ms)
        feedback_payload = {
            "comment": comment,
            "source": "autonomous_agent",
            "session_id": session_id,
            "rating": normalized_rating,
            "score": feedback_score,
            "weight": feedback_weight,
            "features": features,
            "preferences": session.extracted_preferences if session else {},
            "engagement_time_ms": destination_engagement_ms,
        }

        # 1. Update the user preference learner
        if interaction_type:
            await learn_from_interaction(
                user_id=learner_id,
                interaction_type=interaction_type,
                destination=destination,
                feedback_data=feedback_payload,
            )
            if session:
                append_learning_signal(
                    session.planning_data,
                    signal_type="explicit_feedback",
                    destination=destination,
                    source="autonomous_feedback",
                    weight=feedback_weight,
                    features=features,
                    metadata={
                        "rating": normalized_rating,
                        "score": feedback_score,
                        "engagement_time_ms": destination_engagement_ms,
                    },
                )

        # 2. Update the meta-learner with the real user signal
        meta_learner = get_meta_learner()
        if interaction_type:
            await meta_learner.update_session_feedback(
                session_id=session_id,
                user_accepted=user_accepted,
                destination_chosen=destination if user_accepted else None,
                rating=feedback_score,
            )
            await meta_learner.analyze_and_adapt()

        # 3. Update user style classification from explicit feedback
        style_profile = None
        try:
            style_interaction_type = (
                "acceptance" if user_accepted else "rejection" if interaction_type else "feedback"
            )
            style_message = " ".join(
                part for part in [
                    style_interaction_type,
                    destination,
                    comment,
                    normalized_rating,
                ]
                if str(part or "").strip()
            )
            style_profile = await get_user_style_classifier().record_interaction(
                user_id=learner_id,
                user_message=style_message,
                preferences=session.extracted_preferences if session else {},
                interaction_type=style_interaction_type,
                destination=destination,
                accepted=user_accepted if interaction_type else None,
            )
        except Exception as style_exc:
            logger.debug(f"Style classification update failed (non-fatal): {style_exc}")

        # 4. Update hypothesis engine from explicit acceptance/rejection signals
        hypothesis_summary = None
        affinity_summary = None
        try:
            if interaction_type:
                hypothesis_engine = get_hypothesis_engine()
                research_snapshot = _build_hypothesis_research_snapshot(session, destination, features)
                new_hypotheses = await hypothesis_engine.record_interaction(
                    user_id=learner_id,
                    interaction_type="acceptance" if user_accepted else "rejection",
                    destination=destination,
                    preferences=session.extracted_preferences if session else {},
                    rejection_reason=comment if not user_accepted else None,
                    accepted_features=features if user_accepted else [],
                    research_data=research_snapshot,
                    session_id=session_id,
                )
                active_hypotheses = hypothesis_engine.get_active_hypotheses(learner_id)
                hypothesis_recommendations = hypothesis_engine.get_recommendations_for_user(learner_id)
                hypothesis_summary = {
                    "new_hypotheses": new_hypotheses,
                    "active_hypotheses": active_hypotheses,
                    "recommendations": hypothesis_recommendations,
                }
                affinity_graph = get_destination_affinity_graph()
                affinity_summary = await affinity_graph.record_interaction(
                    user_id=learner_id,
                    destination=destination,
                    rating=(feedback_score / 5.0) if user_accepted else -1.0,
                    preferences=session.extracted_preferences if session else {},
                    research_data=research_snapshot,
                    session_id=session_id,
                )
        except Exception as hypothesis_exc:
            logger.debug(f"Hypothesis/affinity update failed (non-fatal): {hypothesis_exc}")

        if session:
            session.planning_data["autonomous_feedback"] = {
                "rating": normalized_rating,
                "score": feedback_score,
                "weight": feedback_weight,
                "destination": destination,
                "comment": comment,
                "engagement_time_ms": destination_engagement_ms,
                "submitted_at": datetime.now().isoformat(),
            }
            if isinstance(style_profile, dict):
                session.planning_data["user_style_profile"] = style_profile
                session.extracted_preferences = dict(session.extracted_preferences or {})
                session.extracted_preferences["user_style_profile"] = style_profile
                session.extracted_preferences["dominant_style"] = style_profile.get("dominant_style")
            if isinstance(hypothesis_summary, dict):
                session.planning_data["hypothesis_summary"] = hypothesis_summary
                session.extracted_preferences = dict(session.extracted_preferences or {})
                session.extracted_preferences["active_hypotheses"] = hypothesis_summary.get("active_hypotheses") or []
                session.extracted_preferences["hypothesis_recommendations"] = hypothesis_summary.get("recommendations") or {}
            if isinstance(affinity_summary, dict):
                session.planning_data["destination_affinity_feedback"] = affinity_summary
            if feedback_score <= 2:
                session.planning_data["autonomous_feedback"]["knowledge_refresh"] = await get_knowledge_base().mark_feedback_refresh_needed(
                    destination,
                    feedback_score=feedback_score,
                    feedback_reason=comment or normalized_rating,
                    affected_sections=features,
                )

            # ── Aggregate passive engagement into learning signals ───────────
            # If the frontend logged engagement events during research, convert
            # them into implicit acceptance/rejection features so the learner
            # can update weights from *passive* behaviour, not just explicit
            # feedback.
            engagement_log = session.planning_data.get("engagement_log") or []
            if engagement_log and session.user_id:
                try:
                    dest_time: Dict[str, int] = {}
                    dest_sections: Dict[str, set] = {}
                    for evt in engagement_log:
                        d = evt.get("destination", "")
                        ms = int(evt.get("time_spent_ms", evt.get("duration_ms", 0)) or 0)
                        sec = evt.get("section", "general")
                        dest_time[d] = dest_time.get(d, 0) + ms
                        dest_sections.setdefault(d, set()).add(sec)

                    # Destinations with >30s engagement get an implicit
                    # positive signal; <5s get an implicit negative signal.
                    for dest, ms_total in dest_time.items():
                        if not dest:
                            continue
                        seconds = ms_total / 1000
                        if seconds >= 30:
                            await learn_from_interaction(
                                user_id=session.user_id,
                                interaction_type="implicit_like",
                                destination=dest,
                                feedback_data={
                                    "source": "passive_engagement",
                                    "seconds": round(seconds, 1),
                                    "sections": list(dest_sections.get(dest, set())),
                                    "session_id": session_id,
                                },
                            )
                            append_learning_signal(
                                session.planning_data,
                                signal_type="implicit_like",
                                destination=dest,
                                source="passive_engagement",
                                weight=0.35,
                                features=list(dest_sections.get(dest, set())),
                                metadata={
                                    "seconds": round(seconds, 1),
                                },
                            )
                        elif seconds < 5:
                            await learn_from_interaction(
                                user_id=session.user_id,
                                interaction_type="implicit_dislike",
                                destination=dest,
                                feedback_data={
                                    "source": "passive_engagement",
                                    "seconds": round(seconds, 1),
                                    "session_id": session_id,
                                },
                            )
                            append_learning_signal(
                                session.planning_data,
                                signal_type="implicit_dislike",
                                destination=dest,
                                source="passive_engagement",
                                weight=-0.25,
                                metadata={
                                    "seconds": round(seconds, 1),
                                },
                            )
                except Exception as eng_err:
                    logger.debug(f"Engagement aggregation failed (non-fatal): {eng_err}")
            # ─────────────────────────────────────────────────────────────────

            await agent.chat_service._save_session(session)

        logger.info(
            "Plan feedback received",
            session_id=session_id,
            rating=normalized_rating,
            score=feedback_score,
            destination=destination,
        )
        return {
            "status": "ok",
            "message": "Thank you for your feedback!",
            "session_id": session_id,
            "rating": normalized_rating,
            "score": feedback_score,
        }
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        return {
            "status": "ok",
            "message": "Feedback noted, thank you!",
            "session_id": session_id,
        }


# ── Real-time reaction & engagement endpoints ───────────────────────────────
# These let the frontend push signals *during* an active research session so
# the research loop can adapt in real time (cancel low-interest destinations,
# boost high-interest ones, and collect passive engagement data for learning).

@router.post("/session/{session_id}/reaction")
async def submit_live_reaction(
    session_id: str,
    request: Dict[str, Any],
    http_request: Request,
    agent: AutonomousAgent = Depends(_new_agent),
):
    """
    Submit a real-time reaction during active research.

    The research loop checks ``session.planning_data["pending_reactions"]``
    between task batches and adapts accordingly:
    - **negative** → cancel remaining tasks for that destination
    - **positive** → boost remaining tasks for that destination

    **Request:**
    ```json
    {
        "destination": "Tokyo",
        "sentiment": "positive" | "negative",
        "reason": "optional"
    }
    ```
    """
    _check_rate_limit(http_request)
    destination = request.get("destination", "")
    sentiment = request.get("sentiment", "")
    reason = request.get("reason", "")

    if sentiment not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="sentiment must be 'positive' or 'negative'")
    if not destination:
        raise HTTPException(status_code=400, detail="destination is required")

    try:
        session = await agent.chat_service._load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        reactions = session.planning_data.setdefault("pending_reactions", [])
        reactions.append({
            "destination": destination,
            "sentiment": sentiment,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        await agent.chat_service._save_session(session)

        logger.info(
            "Live reaction recorded",
            session_id=session_id,
            destination=destination,
            sentiment=sentiment,
        )
        return {
            "status": "ok",
            "message": f"Reaction recorded for {destination}",
            "pending_reactions": len(reactions),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reaction submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record reaction")


@router.post("/session/{session_id}/engagement")
async def submit_engagement_signal(
    session_id: str,
    request: Dict[str, Any],
    http_request: Request,
    agent: AutonomousAgent = Depends(_new_agent),
):
    """
    Submit passive engagement data (view time, scroll, hover) for learning.

    The agent aggregates these signals during synthesis so destinations with
    more view time can receive a small ranking boost without explicit feedback.

    **Request:**
    ```json
    {
        "destination": "Tokyo",
        "section": "attractions" | "weather" | "hotels" | ...,
        "time_spent_ms": 12000
    }
    ```
    """
    _check_rate_limit(http_request)
    destination = request.get("destination", "")
    section = request.get("section", "general")
    try:
        time_spent_ms = int(request.get("time_spent_ms", request.get("duration_ms", 0)) or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="time_spent_ms must be an integer")

    if not destination:
        raise HTTPException(status_code=400, detail="destination is required")
    if time_spent_ms <= 0:
        raise HTTPException(status_code=400, detail="time_spent_ms must be greater than 0")

    try:
        session = await agent.chat_service._load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        engagement_log = session.planning_data.setdefault("engagement_log", [])
        engagement_log.append({
            "destination": destination,
            "section": section,
            "time_spent_ms": min(time_spent_ms, 300000),
            "timestamp": datetime.now().isoformat(),
        })

        if len(engagement_log) > 200:
            session.planning_data["engagement_log"] = engagement_log[-200:]

        await agent.chat_service._save_session(session)

        return {"status": "ok", "events_recorded": len(engagement_log)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Engagement signal error: {e}")
        raise HTTPException(status_code=500, detail="Failed to record engagement")


@router.get("/metrics/summary")
async def get_autonomous_metrics_summary(
    hours: int = Query(168, ge=1, le=24 * 90, description="How far back to inspect persisted autonomous sessions"),
    top_destinations: int = Query(5, ge=1, le=20, description="How many destinations to include in the summary"),
    db: Session = Depends(get_db),
):
    """Aggregate autonomous-agent execution metrics from persisted chat sessions."""
    cutoff = utcnow_naive() - timedelta(hours=hours)
    rows = (
        db.query(PersistedChatSession)
        .filter(PersistedChatSession.updated_at >= cutoff)
        .all()
    )

    summary = {
        "window_hours": hours,
        "total_sessions": 0,
        "active_sessions": 0,
        "waiting_for_input_sessions": 0,
        "completed_sessions": 0,
        "cancelled_sessions": 0,
        "partial_plan_sessions": 0,
        "final_plan_sessions": 0,
        "cache_reused_sessions": 0,
        "fully_cached_sessions": 0,
        "avg_progress_percent": 0.0,
        "avg_cache_hit_rate": 0.0,
        "avg_live_execution_rate": 0.0,
        "avg_runtime_seconds": 0.0,
        "avg_tasks_per_session": 0.0,
        "completed_task_rate": 0.0,
        "total_tasks": 0,
        "total_completed_tasks": 0,
        "total_cache_hits": 0,
        "total_live_completed_tasks": 0,
        "total_failed_tasks": 0,
        "total_cancelled_tasks": 0,
        "top_destinations": [],
        "priority_summary": {
            "avg_priority_score": 0.0,
            "max_priority_score": 0.0,
            "priority_band_counts": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            },
            "task_type_counts": {},
            "top_weighted_tasks": [],
        },
        "fallback_summary": {
            "total_backup_tasks": 0,
            "backup_targets": {},
            "error_kind_counts": {},
        },
        "learning_signal_summary": {
            "total_signals": 0,
            "positive_signals": 0,
            "negative_signals": 0,
            "avg_abs_weight": 0.0,
            "type_counts": {},
            "source_counts": {},
            "top_destinations": [],
        },
        "knowledge_summary": {},
    }
    destination_counts: Counter[str] = Counter()
    priority_band_counts: Counter[str] = Counter()
    task_type_counts: Counter[str] = Counter()
    fallback_target_counts: Counter[str] = Counter()
    fallback_error_kind_counts: Counter[str] = Counter()
    learning_type_counts: Counter[str] = Counter()
    learning_source_counts: Counter[str] = Counter()
    learning_destination_counts: Counter[str] = Counter()
    active_states = {"listening", "planning", "researching", "synthesizing", "presenting"}

    progress_total = 0.0
    cache_hit_rate_total = 0.0
    live_execution_rate_total = 0.0
    elapsed_seconds_total = 0.0
    priority_score_total = 0.0
    priority_score_count = 0
    max_priority_score = 0.0
    weighted_tasks: List[Dict[str, Any]] = []
    total_backup_tasks = 0
    total_learning_signals = 0
    total_positive_signals = 0
    total_negative_signals = 0
    learning_abs_weight_total = 0.0
    learning_weighted_count = 0

    for row in rows:
        parsed = _parse_autonomous_session_payload(row.payload)
        if not parsed:
            continue

        runtime = parsed["runtime"]
        metrics = parsed["metrics"]
        plan = runtime.get("plan") or {}
        if not isinstance(plan, dict):
            plan = {}

        summary["total_sessions"] += 1
        state = str(runtime.get("state") or "idle")
        if state in active_states:
            summary["active_sessions"] += 1
        elif state == AgentState.WAITING_FOR_INPUT.value:
            summary["waiting_for_input_sessions"] += 1
        elif state == AgentState.COMPLETED.value:
            summary["completed_sessions"] += 1
        elif state == AgentState.CANCELLED.value:
            summary["cancelled_sessions"] += 1

        if plan.get("is_partial"):
            summary["partial_plan_sessions"] += 1
        elif plan:
            summary["final_plan_sessions"] += 1

        total_tasks = int(metrics.get("total_tasks") or len(runtime.get("tasks") or []))
        completed_tasks = int(metrics.get("completed_tasks") or len(runtime.get("completed_tasks") or []))
        cache_hits = int(metrics.get("cache_hits") or 0)
        live_completed = int(metrics.get("live_completed_tasks") or 0)
        failed_tasks = int(metrics.get("failed_tasks") or 0)
        cancelled_tasks = int(metrics.get("cancelled_tasks") or 0)
        cache_hit_rate = float(metrics.get("cache_hit_rate") or 0.0)
        live_execution_rate = float(metrics.get("live_execution_rate") or 0.0)
        elapsed_seconds = round(float(metrics.get("elapsed_ms") or 0) / 1000, 2)

        progress_total += float(runtime.get("progress") or 0)
        cache_hit_rate_total += cache_hit_rate
        live_execution_rate_total += live_execution_rate
        elapsed_seconds_total += elapsed_seconds

        summary["total_tasks"] += total_tasks
        summary["total_completed_tasks"] += completed_tasks
        summary["total_cache_hits"] += cache_hits
        summary["total_live_completed_tasks"] += live_completed
        summary["total_failed_tasks"] += failed_tasks
        summary["total_cancelled_tasks"] += cancelled_tasks

        if cache_hits > 0:
            summary["cache_reused_sessions"] += 1
        if total_tasks > 0 and live_completed == 0 and cache_hits >= total_tasks:
            summary["fully_cached_sessions"] += 1

        destination_counts.update(parsed["destinations"])
        for task in _extract_priority_tasks(runtime):
            priority = str(task.get("priority") or "").lower()
            task_type = str(task.get("task_type") or "unknown").strip().lower() or "unknown"
            if priority in {"critical", "high", "medium", "low"}:
                priority_band_counts[priority] += 1
            task_type_counts[task_type] += 1

            backup_for = str(task.get("backup_for") or "").strip().lower()
            top_error_kind = str(task.get("top_error_kind") or "").strip().lower()
            if backup_for:
                total_backup_tasks += 1
                fallback_target_counts[backup_for] += 1
                if top_error_kind:
                    fallback_error_kind_counts[top_error_kind] += 1

            score = float(task.get("priority_score") or 0.0)
            if score > 0:
                priority_score_total += score
                priority_score_count += 1
                max_priority_score = max(max_priority_score, score)
                weighted_tasks.append(task)

        learning_summary = summarize_learning_signals(parsed["planning_data"])
        total_learning_signals += int(learning_summary.get("total_signals") or 0)
        total_positive_signals += int(learning_summary.get("positive_signals") or 0)
        total_negative_signals += int(learning_summary.get("negative_signals") or 0)
        avg_abs_weight = float(learning_summary.get("avg_abs_weight") or 0.0)
        weighted_signal_count = int(learning_summary.get("positive_signals") or 0) + int(learning_summary.get("negative_signals") or 0)
        learning_abs_weight_total += avg_abs_weight * weighted_signal_count
        learning_weighted_count += weighted_signal_count
        for signal_type, count in (learning_summary.get("type_counts") or {}).items():
            learning_type_counts[str(signal_type)] += int(count or 0)
        for source, count in (learning_summary.get("source_counts") or {}).items():
            learning_source_counts[str(source)] += int(count or 0)
        for item in (learning_summary.get("top_destinations") or []):
            if not isinstance(item, dict):
                continue
            destination = str(item.get("destination") or "").strip()
            if destination:
                learning_destination_counts[destination] += int(item.get("count") or 0)

    session_count = summary["total_sessions"]
    summary["avg_progress_percent"] = _safe_average(progress_total, session_count)
    summary["avg_cache_hit_rate"] = _safe_average(cache_hit_rate_total, session_count)
    summary["avg_live_execution_rate"] = _safe_average(live_execution_rate_total, session_count)
    summary["avg_runtime_seconds"] = _safe_average(elapsed_seconds_total, session_count)
    summary["avg_tasks_per_session"] = _safe_average(summary["total_tasks"], session_count)
    if summary["total_tasks"] > 0:
        summary["completed_task_rate"] = round(summary["total_completed_tasks"] / summary["total_tasks"], 2)
    summary["top_destinations"] = [
        {"destination": destination, "sessions": count}
        for destination, count in destination_counts.most_common(top_destinations)
    ]
    summary["priority_summary"] = {
        "avg_priority_score": _safe_average(priority_score_total, priority_score_count),
        "max_priority_score": round(max_priority_score, 2),
        "priority_band_counts": {
            "critical": int(priority_band_counts.get("critical") or 0),
            "high": int(priority_band_counts.get("high") or 0),
            "medium": int(priority_band_counts.get("medium") or 0),
            "low": int(priority_band_counts.get("low") or 0),
        },
        "task_type_counts": {
            task_type: count
            for task_type, count in sorted(
                task_type_counts.items(),
                key=lambda item: (-int(item[1]), str(item[0])),
            )
        },
        "top_weighted_tasks": sorted(
            weighted_tasks,
            key=lambda task: (
                -float(task.get("priority_score") or 0.0),
                str(task.get("task_type") or ""),
                str(task.get("destination") or ""),
            ),
        )[:10],
    }
    summary["fallback_summary"] = {
        "total_backup_tasks": int(total_backup_tasks),
        "backup_targets": {
            target: count
            for target, count in sorted(
                fallback_target_counts.items(),
                key=lambda item: (-int(item[1]), str(item[0])),
            )
        },
        "error_kind_counts": {
            kind: count
            for kind, count in sorted(
                fallback_error_kind_counts.items(),
                key=lambda item: (-int(item[1]), str(item[0])),
            )
        },
    }
    summary["learning_signal_summary"] = {
        "total_signals": int(total_learning_signals),
        "positive_signals": int(total_positive_signals),
        "negative_signals": int(total_negative_signals),
        "avg_abs_weight": round(learning_abs_weight_total / learning_weighted_count, 2) if learning_weighted_count else 0.0,
        "type_counts": {
            signal_type: count
            for signal_type, count in sorted(
                learning_type_counts.items(),
                key=lambda item: (-int(item[1]), str(item[0])),
            )
        },
        "source_counts": {
            source: count
            for source, count in sorted(
                learning_source_counts.items(),
                key=lambda item: (-int(item[1]), str(item[0])),
            )
        },
        "top_destinations": [
            {"destination": destination, "count": count}
            for destination, count in learning_destination_counts.most_common(5)
        ],
    }

    knowledge_stats = await get_knowledge_base().get_stats_summary()
    if isinstance(knowledge_stats, dict) and "error" not in knowledge_stats:
        summary["knowledge_summary"] = {
            "catalog_total": int(knowledge_stats.get("catalog_total") or 0),
            "catalog_coverage_percent": float(knowledge_stats.get("catalog_coverage_percent") or 0.0),
            "seeded_destinations_count": int(knowledge_stats.get("seeded_destinations_count") or 0),
            "stale_destinations_count": int(knowledge_stats.get("stale_destinations_count") or 0),
            "refresh_recommended_count": int(knowledge_stats.get("refresh_recommended_count") or 0),
        }

    return summary


@router.get("/capabilities")
async def get_agent_capabilities():
    """
    Get autonomous agent capabilities and boundaries.
    
    **Response:**
    ```json
    {
        "can_do": [
            "Search web for destination information",
            "Query travel APIs",
            "Compare destinations",
            ...
        ],
        "cannot_do": [
            "Access personal accounts",
            "Make bookings",
            ...
        ],
        "security_features": [...]
    }
    ```
    """
    return {
        "version": "1.0.0",
        "capabilities": {
            "can_do": [
                "Autonomous web browsing for travel information",
                "Real-time API queries (weather, visa, flights, hotels)",
                "Multi-destination comparison",
                "Personalized itinerary generation",
                "Natural language conversation",
                "Preference extraction from conversation",
                "Progressive research with real-time updates",
                "Comprehensive plan synthesis"
            ],
            "cannot_do": [
                "Access personal accounts (email, banking)",
                "Make actual bookings or payments",
                "Access files outside application",
                "Guarantee visa requirements",
                "Provide legal/medical/financial advice"
            ],
            "security_features": [
                "Session isolation",
                "Rate limiting (60 req/min)",
                "API key management via environment",
                "Circuit breakers for external APIs",
                "No filesystem access"
            ]
        },
        "supported_research_types": [
            "weather",
            "visa",
            "attractions",
            "flights",
            "hotels",
            "restaurants",
            "events",
            "web_search"
        ],
        "research_depths": [
            "quick (30 sec, cached data)",
            "standard (2 min, mixed sources)",
            "deep (5 min, comprehensive)"
        ]
    }


@router.get("/health")
async def health_check():
    """Check if autonomous agent service is healthy."""
    agent = get_autonomous_agent()
    return {
        "status": "healthy",
        "state": agent.state.value,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/debug/learning-state")
async def debug_learning_state():
    """Show current learning state — feature weights, top destinations, session stats."""
    from app.utils.learning_agent import get_learner
    meta = get_meta_learner()
    learner = get_learner()
    style_classifier = get_user_style_classifier()
    hypothesis_engine = get_hypothesis_engine()
    affinity_graph = get_destination_affinity_graph()
    learner._ensure_global_state_loaded_sync()
    style_stats = await style_classifier.get_learning_stats()
    hypothesis_stats = await hypothesis_engine.get_learning_stats()
    affinity_stats = await affinity_graph.get_learning_stats()

    total = len(meta.performance_history)
    labeled = [r for r in meta.performance_history if isinstance(r.get("user_accepted"), bool)]
    real_users = [uid for uid in learner.user_profiles if not uid.startswith("persona_")]
    dominant_style_breakdown = Counter(
        style_classifier.get_user_style(uid).get("dominant_style", "explorer")
        for uid in style_classifier.user_styles
        if not uid.startswith("persona_")
    )

    # Top accepted destinations
    dest_rates = {
        d: round(v["accepted"] / max(v["accepted"] + v["rejected"], 1), 2)
        for d, v in meta.destination_acceptance_rates.items()
        if v["accepted"] + v["rejected"] >= 2
    }
    top_dests = sorted(dest_rates.items(), key=lambda x: -x[1])[:10]

    # Strategy win rates
    strat_scores = {}
    for strat, outcomes in meta.strategy_effectiveness.items():
        if outcomes:
            strat_scores[strat] = round(sum(outcomes) / len(outcomes), 2)

    decision_feedback = meta.get_decision_feedback_insights()

    return {
        "sessions": {"total": total, "labeled": len(labeled), "unlabeled": total - len(labeled)},
        "real_users": len(real_users),
        "feature_weights": dict(sorted(
            learner.global_patterns["feature_importance"].items(),
            key=lambda x: -x[1]
        )),
        "top_destinations_by_acceptance": [
            {"destination": d, "rate": r, "total": meta.destination_acceptance_rates[d]["accepted"] + meta.destination_acceptance_rates[d]["rejected"]}
            for d, r in top_dests
        ],
        "strategy_win_rates": strat_scores,
        "user_style_classifier": {
            "total_users_tracked": style_stats.get("total_users_tracked", 0),
            "classified_users": style_stats.get("classified_users", 0),
            "style_interactions_recorded": style_stats.get("style_interactions_recorded", 0),
            "dominant_style_breakdown": dict(dominant_style_breakdown),
        },
        "hypothesis_engine": {
            "users_with_hypotheses": hypothesis_stats.get("users_with_hypotheses", 0),
            "total_hypotheses": hypothesis_stats.get("total_hypotheses", 0),
            "validated_hypotheses": hypothesis_stats.get("validated_hypotheses", 0),
            "total_evidence_stored": hypothesis_stats.get("total_evidence_stored", 0),
        },
        "destination_affinity_graph": {
            "destinations_tracked": affinity_stats.get("destinations_tracked", 0),
            "users_tracked": affinity_stats.get("users_tracked", 0),
            "interactions_recorded": affinity_stats.get("interactions_recorded", 0),
            "affinity_pairs": affinity_stats.get("affinity_pairs", 0),
            "similarity_pairs": affinity_stats.get("similarity_pairs", 0),
        },
        "decision_feedback": {
            "coverage": decision_feedback.get("coverage", 0.0),
            "sessions_with_decision_context": decision_feedback.get("sessions_with_decision_context", 0),
            "learned_weights": decision_feedback.get("learned_weights", {}),
            "criteria_effectiveness": decision_feedback.get("criteria_effectiveness", [])[:8],
            "ranking_basis_performance": decision_feedback.get("ranking_basis_performance", {}),
        },
        "epsilon": round(max(0.05, 0.15 - 0.01 * (total // 10)), 3),
    }
