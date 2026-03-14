"""
Executive Controller — Phase 1 & 3 & 4
========================================
Mid-research autonomous decision engine that runs after every priority batch.

Responsibilities:
1. Evaluate quality of partial results and detect gaps
2. Spawn compensatory tasks when data is weak
3. Cancel remaining tasks for destinations that are clearly unsuitable (bad visa,
   extreme weather, no attractions data)
4. Re-read meta-learner recommendations every N completions and adapt depth
5. Re-apply learning bias after N tasks to use the freshest feature weights

Error taxonomy (Phase 4):
  TransientError  — network/timeout — retry with backoff
  RateLimitError  — 429 / quota     — delay then retry once
  EmptyResultError — data exists but returned nothing — compensate with web_search
  PermanentError  — bad input / unknown destination — skip, mark not_applicable
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


# ── Error taxonomy ────────────────────────────────────────────────────────────

class ResearchErrorKind:
    TRANSIENT = "transient"          # network / timeout — safe to retry
    RATE_LIMIT = "rate_limit"        # 429 / API quota   — wait then retry once
    EMPTY_RESULT = "empty_result"    # call succeeded but returned no data
    PERMANENT = "permanent"          # bad input, unknown dest — skip


_TRANSIENT_PATTERNS = [
    r"timeout", r"timed.out", r"connection.?reset", r"connection.?refused",
    r"network", r"ssl", r"eof", r"read.error",
]
_RATE_LIMIT_PATTERNS = [
    r"429", r"rate.?limit", r"quota", r"too.many.request",
]
_PERMANENT_PATTERNS = [
    r"unknown.destination", r"not.found", r"invalid", r"missing.required",
    r"no.such", r"does.not.exist",
]


def classify_error(error_text: str) -> str:
    low = (error_text or "").lower()
    for pat in _RATE_LIMIT_PATTERNS:
        if re.search(pat, low):
            return ResearchErrorKind.RATE_LIMIT
    for pat in _TRANSIENT_PATTERNS:
        if re.search(pat, low):
            return ResearchErrorKind.TRANSIENT
    for pat in _PERMANENT_PATTERNS:
        if re.search(pat, low):
            return ResearchErrorKind.PERMANENT
    return ResearchErrorKind.TRANSIENT  # safe default — worth retrying


# ── Evaluation result ─────────────────────────────────────────────────────────

@dataclass
class EvaluationResult:
    """Output from a single executive evaluation pass."""
    new_tasks: List[Any] = field(default_factory=list)       # ResearchTask objects
    tasks_to_cancel: Set[str] = field(default_factory=set)   # task IDs
    tasks_to_retry: List[Tuple[Any, float]] = field(default_factory=list)  # (task, delay_secs)
    updated_prefs: Optional[Dict[str, Any]] = None
    insights: List[str] = field(default_factory=list)        # human-readable SSE messages
    quality_report: Dict[str, float] = field(default_factory=dict)  # dest → 0-1 quality
    stop_early: bool = False                                 # True if all goals met


# ── Quality thresholds ────────────────────────────────────────────────────────

_MIN_ATTRACTION_COUNT = 3
_BAD_WEATHER_PATTERNS = [
    r"monsoon", r"hurricane", r"typhoon", r"flood", r"extreme.heat",
    r"danger", r"unsafe", r"avoid",
]
_VISA_BLOCKED_PATTERNS = [
    r"not.permitted", r"banned", r"prohibited", r"denied", r"refused",
]


def _score_weather(weather_result: Dict[str, Any]) -> Tuple[float, str]:
    """Returns (quality 0-1, reason). 0 = dangerous/missing."""
    summary = str(weather_result.get("summary", "")).lower()
    weather = weather_result.get("weather") or {}
    temp = weather.get("temperature")

    for pat in _BAD_WEATHER_PATTERNS:
        if re.search(pat, summary):
            return 0.2, f"Potentially unfavourable conditions: {summary[:60]}"

    if not weather and not summary:
        return 0.4, "No weather data available"

    if isinstance(temp, (int, float)) and (temp > 42 or temp < -20):
        return 0.3, f"Extreme temperature ({temp}°C)"

    return 0.9, "Weather data looks good"


def _score_visa(visa_result: Dict[str, Any]) -> Tuple[float, str]:
    """Returns (quality 0-1, reason). 0 = entry blocked."""
    summary = str(visa_result.get("summary", "")).lower()
    visa = visa_result.get("visa") or {}
    requirement = str(visa.get("requirement", "")).lower()

    for pat in _VISA_BLOCKED_PATTERNS:
        if re.search(pat, summary) or re.search(pat, requirement):
            return 0.0, f"Entry likely blocked: {summary[:60]}"

    if "visa_free" in requirement or "visa free" in summary or "no visa" in summary:
        return 1.0, "Visa free"
    if "on arrival" in requirement or "on arrival" in summary:
        return 0.85, "Visa on arrival"
    if "required" in summary or "required" in requirement:
        return 0.6, "Visa required but obtainable"

    return 0.7, "Visa status known"


def _score_attractions(attractions_result: Dict[str, Any]) -> Tuple[float, str]:
    picks = attractions_result.get("top_picks") or attractions_result.get("attractions") or []
    count = len(picks)
    if count >= 8:
        return 1.0, f"{count} attractions found"
    if count >= _MIN_ATTRACTION_COUNT:
        return 0.7, f"Only {count} attractions found — may want more data"
    if count > 0:
        return 0.4, f"Very sparse attractions data ({count} items)"
    return 0.2, "No attractions data"


# ── Executive Controller ──────────────────────────────────────────────────────

class ExecutiveController:
    """
    Runs after every priority batch to evaluate partial results and decide:
    - Spawn new compensatory tasks (e.g., extra web_search for sparse attractions)
    - Cancel remaining tasks for clearly unsuitable destinations
    - Re-read meta-learner recommendations every N completions
    - Re-apply personalization weights mid-session
    """

    RECHECK_META_EVERY_N = 5     # re-read meta recommendations every N completed tasks
    MAX_COMPENSATORY_TASKS = 3   # cap extra tasks spawned per evaluation

    def __init__(self, prefs: Dict[str, Any], destinations: List[str]):
        self._prefs = prefs
        self._destinations = destinations
        self._evaluated_batches = 0
        self._dest_scores: Dict[str, float] = {d: 1.0 for d in destinations}
        self._compensated_dests: Set[str] = set()   # already added extra tasks for
        self._cancelled_dests: Set[str] = set()     # already cancelled

    def update_prefs(self, prefs: Dict[str, Any]) -> None:
        self._prefs = prefs

    async def evaluate_after_batch(
        self,
        completed_tasks: List[Any],     # ResearchTask objects
        pending_tasks: List[Any],       # remaining pending
        completed_count: int,
        agent_instance: Any,            # AutonomousAgent instance for helpers
    ) -> EvaluationResult:
        """Called after each priority batch completes. Returns adaptation decisions."""
        self._evaluated_batches += 1
        result = EvaluationResult()

        # Group completed tasks by destination
        by_dest: Dict[str, List[Any]] = {}
        for task in completed_tasks:
            dest = task.destination or "__global__"
            by_dest.setdefault(dest, []).append(task)

        for dest in self._destinations:
            if dest in self._cancelled_dests:
                continue

            dest_tasks = by_dest.get(dest, [])
            decision = await self._evaluate_destination(
                dest, dest_tasks, pending_tasks, result, agent_instance
            )
            if decision == "cancelled":
                self._cancelled_dests.add(dest)

        # Meta-learner re-read (Phase 3 hook)
        if completed_count > 0 and completed_count % self.RECHECK_META_EVERY_N == 0:
            updated_prefs = await self._refresh_meta_recommendations(agent_instance)
            if updated_prefs:
                result.updated_prefs = updated_prefs
                result.insights.append(
                    "Adapted research strategy based on updated learning data."
                )

        # Build quality report
        result.quality_report = dict(self._dest_scores)

        # Emit quality insights
        low_quality = [d for d, s in self._dest_scores.items() if s < 0.4]
        if low_quality:
            result.insights.append(
                f"Note: Limited data quality for {', '.join(low_quality)}. "
                "Compensatory searches have been queued."
            )

        return result

    async def _evaluate_destination(
        self,
        dest: str,
        dest_tasks: List[Any],
        pending_tasks: List[Any],
        result: EvaluationResult,
        agent: Any,
    ) -> str:
        """Evaluate a single destination. Returns 'ok', 'compensated', or 'cancelled'."""
        if not dest_tasks:
            return "ok"

        dest_quality = 1.0
        cancel_reason: Optional[str] = None

        for task in dest_tasks:
            if task.status != "completed" or not task.result:
                continue

            if task.type == "weather":
                score, reason = _score_weather(task.result)
                dest_quality = min(dest_quality, score)
                if score < 0.3:
                    result.insights.append(
                        f"Weather concern for {dest}: {reason}"
                    )
                    # Don't cancel — bad weather is informational, not a blocker

            elif task.type == "visa":
                score, reason = _score_visa(task.result)
                dest_quality = min(dest_quality, score)
                if score == 0.0:
                    cancel_reason = f"Entry blocked for {dest}: {reason}"

            elif task.type == "attractions":
                score, reason = _score_attractions(task.result)
                dest_quality = min(dest_quality, score)
                if score < 0.5 and dest not in self._compensated_dests:
                    # Spawn compensatory web search
                    compensatory = self._build_compensatory_web_search(dest, task.result, agent)
                    if compensatory and len(result.new_tasks) < self.MAX_COMPENSATORY_TASKS:
                        result.new_tasks.append(compensatory)
                        self._compensated_dests.add(dest)
                        result.insights.append(
                            f"Queued extra search for {dest}: {reason}"
                        )

        self._dest_scores[dest] = round(dest_quality, 2)

        if cancel_reason:
            # Cancel all pending tasks for this destination
            for task in pending_tasks:
                if task.destination == dest and task.status == "pending":
                    result.tasks_to_cancel.add(task.id)
            result.insights.append(cancel_reason)
            return "cancelled"

        return "ok"

    def _build_compensatory_web_search(
        self,
        dest: str,
        failed_result: Dict[str, Any],
        agent: Any,
    ) -> Optional[Any]:
        """Build a compensatory web_search ResearchTask for a destination with sparse data."""
        try:
            from app.services.autonomous_agent import ResearchTask, ResearchPriority
            import uuid
            from datetime import date

            yr = date.today().year
            queries = [
                f"top things to do in {dest} {yr}",
                f"{dest} tourist attractions guide",
                f"best experiences in {dest}",
            ]
            return ResearchTask(
                id=f"web_search_{dest}_compensatory_{uuid.uuid4().hex[:6]}",
                type="web_search",
                priority=ResearchPriority.HIGH,
                destination=dest,
                params={"queries": queries, "compensatory": True},
            )
        except Exception as exc:
            logger.debug(f"ExecutiveController: could not build compensatory task: {exc}")
            return None

    async def _refresh_meta_recommendations(
        self, agent: Any
    ) -> Optional[Dict[str, Any]]:
        """Re-read meta-learner and refresh agent preferences/depth if changed."""
        try:
            from app.utils.meta_learner import get_meta_learner
            from app.services.auto_research_agent import ResearchDepth

            ml = get_meta_learner()
            user_id = agent.current_session.user_id if agent.current_session else None
            recs = ml.get_recommendations(user_id=user_id)
            if not recs:
                return None

            optimal_depth_str = recs.get("optimal_research_depth")
            if optimal_depth_str:
                try:
                    new_depth = ResearchDepth(optimal_depth_str)
                    old_depth = agent.config.research_depth
                    if new_depth != old_depth:
                        agent.config.research_depth = new_depth
                        logger.info(
                            f"ExecutiveController: depth {old_depth.value} → "
                            f"{new_depth.value} mid-session"
                        )
                        # ── Adjust task pool based on depth change ───
                        self._adjust_tasks_for_depth_change(
                            old_depth, new_depth, agent
                        )
                except ValueError:
                    pass

            # Re-apply learning bias with latest weights
            if agent.current_session:
                updated = agent._apply_learning_bias(
                    agent.current_session,
                    dict(agent._preferences),
                )
                if updated != agent._preferences:
                    agent._preferences = updated
                    if agent.current_session:
                        agent.current_session.extracted_preferences = dict(updated)
                    return updated

        except Exception as exc:
            logger.debug(f"ExecutiveController: meta refresh failed (non-fatal): {exc}")
        return None

    @staticmethod
    def _adjust_tasks_for_depth_change(
        old_depth: Any,
        new_depth: Any,
        agent: Any,
    ) -> None:
        """Adjust the pending task pool when research depth changes mid-session.

        - Downshift (DEEP→STANDARD, STANDARD→QUICK): cancel LOW-priority
          pending tasks to finish faster.
        - Upshift (QUICK→STANDARD, STANDARD→DEEP): for each destination,
          if optional task types (hotels, restaurants, events) are missing,
          spawn them.
        """
        from app.services.auto_research_agent import ResearchDepth, ResearchPriority

        _DEPTH_ORDER = {
            ResearchDepth.QUICK: 0,
            ResearchDepth.STANDARD: 1,
            ResearchDepth.DEEP: 2,
        }
        old_level = _DEPTH_ORDER.get(old_depth, 1)
        new_level = _DEPTH_ORDER.get(new_depth, 1)

        pending = [
            t for t in agent.research_tasks
            if t.status == "pending"
        ]

        if new_level < old_level:
            # ── Downshift: trim LOW-priority tasks ───────────────────
            cancelled = 0
            for task in pending:
                if task.priority == ResearchPriority.LOW:
                    task.status = "cancelled"
                    if task not in agent.completed_tasks:
                        agent.completed_tasks.append(task)
                    cancelled += 1
            if cancelled:
                logger.info(
                    f"DepthAdj: cancelled {cancelled} LOW-priority tasks "
                    f"(downshift to {new_depth.value})"
                )

        elif new_level > old_level:
            # ── Upshift: spawn missing optional task types ───────────
            from app.services.auto_research_agent import ResearchTask
            import uuid

            _OPTIONAL_TYPES = ["hotels", "restaurants", "events"]
            existing = {
                (t.destination, t.type) for t in agent.research_tasks
            }
            spawned = 0
            for dest in agent._destinations_list:
                for task_type in _OPTIONAL_TYPES:
                    if (dest, task_type) not in existing:
                        new_task = ResearchTask(
                            id=str(uuid.uuid4())[:8],
                            type=task_type,
                            destination=dest,
                            priority=ResearchPriority.MEDIUM,
                            query=f"{task_type} in {dest}",
                            status="pending",
                        )
                        agent.research_tasks.append(new_task)
                        spawned += 1
            if spawned:
                logger.info(
                    f"DepthAdj: spawned {spawned} optional tasks "
                    f"(upshift to {new_depth.value})"
                )


# ── Retry scheduler ───────────────────────────────────────────────────────────

def get_retry_delay(error_kind: str, attempt: int) -> Optional[float]:
    """
    Returns delay in seconds before retry, or None if should not retry.
      attempt: 1-indexed (first retry = attempt 1)
    """
    if error_kind == ResearchErrorKind.PERMANENT:
        return None
    if error_kind == ResearchErrorKind.RATE_LIMIT:
        return min(30.0, 5.0 * (2 ** attempt))   # 10s, 20s, 30s cap
    if error_kind == ResearchErrorKind.TRANSIENT:
        return min(15.0, 2.0 * (2 ** attempt))   # 4s, 8s, 15s cap
    if error_kind == ResearchErrorKind.EMPTY_RESULT:
        return None  # compensatory task handles this
    return None


MAX_RETRIES: Dict[str, int] = {
    ResearchErrorKind.TRANSIENT: 2,
    ResearchErrorKind.RATE_LIMIT: 1,
    ResearchErrorKind.EMPTY_RESULT: 0,
    ResearchErrorKind.PERMANENT: 0,
}


def should_retry(error_kind: str, attempt: int) -> bool:
    return attempt <= MAX_RETRIES.get(error_kind, 0)
