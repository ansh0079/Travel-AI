"""
Learns recurring task failure patterns so the autonomous agent can plan
fallback coverage before expensive APIs fail again.

Enhanced with Error Recovery Feedback:
- Tracks whether compensatory tasks actually improve data quality
- Learns which fallbacks work for which task types
- Avoids recommending fallbacks that don't help
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database.connection import SessionLocal, engine
from app.database.models import LearnedUserProfile
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_SAVE_LOCK = asyncio.Lock()


class ErrorPatternLearner:
    PROFILE_ID = "__error_pattern_learner__"
    MAX_FAILURES = 500
    MAX_RECOVERY_RECORDS = 200
    HIGH_RISK_TASK_FAILURES = 1
    HIGH_RISK_DESTINATION_FAILURES = 1

    def __init__(self) -> None:
        self.failures: List[Dict[str, Any]] = []
        # Recovery tracking: {task_type: [{destination, before_score, after_score, worked}]}
        self.recovery_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._loaded = False
        self._table_ready = False

    def _ensure_table(self) -> None:
        if self._table_ready:
            return
        LearnedUserProfile.__table__.create(bind=engine, checkfirst=True)
        self._table_ready = True

    def _sync_load_state(self) -> Dict[str, Any]:
        self._ensure_table()
        db = SessionLocal()
        try:
            record = (
                db.query(LearnedUserProfile)
                .filter(LearnedUserProfile.user_id == self.PROFILE_ID)
                .first()
            )
            if not record or not record.profile_json:
                return {}
            payload = json.loads(record.profile_json)
            return payload if isinstance(payload, dict) else {}
        except Exception as exc:
            logger.warning("ErrorPatternLearner: load failed", error=str(exc))
            return {}
        finally:
            db.close()

    def _sync_save_state(self, payload: Dict[str, Any]) -> bool:
        self._ensure_table()
        db = SessionLocal()
        try:
            record = (
                db.query(LearnedUserProfile)
                .filter(LearnedUserProfile.user_id == self.PROFILE_ID)
                .first()
            )
            if record is None:
                record = LearnedUserProfile(user_id=self.PROFILE_ID)
                db.add(record)
            record.profile_json = json.dumps(payload)
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            logger.warning("ErrorPatternLearner: save failed", error=str(exc))
            return False
        finally:
            db.close()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        payload = self._sync_load_state()
        failures = payload.get("failures") if isinstance(payload, dict) else []
        if isinstance(failures, list):
            self.failures = failures[-self.MAX_FAILURES :]
        
        # Load recovery records
        recovery_data = payload.get("recovery_records", {}) if isinstance(payload, dict) else {}
        for task_type, records in recovery_data.items():
            if isinstance(records, list):
                self.recovery_records[task_type] = records[-self.MAX_RECOVERY_RECORDS:]

    async def _save_state(self) -> None:
        async with _SAVE_LOCK:
            await asyncio.to_thread(
                self._sync_save_state,
                {
                    "failures": self.failures[-self.MAX_FAILURES :],
                    "recovery_records": {
                        k: v[-self.MAX_RECOVERY_RECORDS:]
                        for k, v in self.recovery_records.items()
                    },
                },
            )

    async def record_failure(
        self,
        *,
        task_type: str,
        destination: Optional[str],
        error_kind: str,
        message: str,
    ) -> None:
        self._ensure_loaded()
        bucket = datetime.now().strftime("%Y-%m-%dT%H")
        self.failures.append(
            {
                "task_type": str(task_type or "unknown"),
                "destination": str(destination or "").strip(),
                "error_kind": str(error_kind or "unknown"),
                "message": str(message or "")[:300],
                "hour_bucket": bucket,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.failures) > self.MAX_FAILURES:
            self.failures = self.failures[-self.MAX_FAILURES :]
        await self._save_state()

    async def record_recovery_outcome(
        self,
        *,
        original_task_type: str,
        destination: str,
        compensatory_task_type: str,
        quality_before: float,
        quality_after: float,
    ) -> Dict[str, Any]:
        """
        Record whether a compensatory task improved data quality.
        
        Args:
            original_task_type: The task that failed (e.g., "attractions")
            destination: Destination being researched
            compensatory_task_type: The fallback task used (e.g., "web_search")
            quality_before: Data quality score before recovery (0-1)
            quality_after: Data quality score after recovery (0-1)
            
        Returns:
            Recovery analysis with recommendation
        """
        self._ensure_loaded()
        
        improvement = quality_after - quality_before
        worked = improvement > 0.1  # Meaningful improvement threshold
        
        recovery_record = {
            "destination": destination.strip().lower(),
            "original_task": original_task_type.strip().lower(),
            "compensatory_task": compensatory_task_type.strip().lower(),
            "quality_before": round(quality_before, 3),
            "quality_after": round(quality_after, 3),
            "improvement": round(improvement, 3),
            "worked": worked,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Store under original task type for lookup
        self.recovery_records[original_task_type.strip().lower()].append(recovery_record)
        
        # Keep only recent records
        if len(self.recovery_records[original_task_type.strip().lower()]) > self.MAX_RECOVERY_RECORDS:
            self.recovery_records[original_task_type.strip().lower()] = \
                self.recovery_records[original_task_type.strip().lower()][-self.MAX_RECOVERY_RECORDS:]
        
        await self._save_state()
        
        logger.info(
            "ErrorPatternLearner: recorded recovery outcome",
            original_task=original_task_type,
            destination=destination,
            worked=worked,
            improvement=improvement,
        )
        
        return {
            "worked": worked,
            "improvement": round(improvement, 3),
            "recommendation": "use_fallback" if worked else "skip_fallback",
        }

    def get_failure_profile(
        self,
        *,
        task_type: str,
        destination: Optional[str] = None,
        at_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        self._ensure_loaded()
        bucket = (at_time or datetime.now()).strftime("%Y-%m-%dT%H")
        normalized_destination = str(destination or "").strip().lower()
        normalized_task = str(task_type or "unknown").strip().lower()

        task_failures = 0
        destination_failures = 0
        hour_failures = 0
        error_kind_counts: Dict[str, int] = defaultdict(int)

        for failure in self.failures:
            failure_task = str(failure.get("task_type") or "").strip().lower()
            if failure_task != normalized_task:
                continue

            task_failures += 1
            if str(failure.get("hour_bucket") or "") == bucket:
                hour_failures += 1

            failure_destination = str(failure.get("destination") or "").strip().lower()
            if normalized_destination and failure_destination == normalized_destination:
                destination_failures += 1

            error_kind = str(failure.get("error_kind") or "unknown")
            error_kind_counts[error_kind] += 1

        high_risk = (
            hour_failures >= self.HIGH_RISK_TASK_FAILURES
            or destination_failures >= self.HIGH_RISK_DESTINATION_FAILURES
        )

        # ── Recovery effectiveness check ─────────────────────────────
        # Check if web_search fallback has worked for this task type
        recovery_successes = 0
        recovery_failures = 0
        recovery_improvements = []
        
        for record in self.recovery_records.get(normalized_task, []):
            if normalized_destination and record.get("destination") != normalized_destination:
                continue
            
            if record.get("worked"):
                recovery_successes += 1
            else:
                recovery_failures += 1
            
            if isinstance(record.get("improvement"), (int, float)):
                recovery_improvements.append(record["improvement"])
        
        avg_improvement = (
            sum(recovery_improvements) / len(recovery_improvements)
            if recovery_improvements else 0.0
        )
        
        recommended_fallback = None
        if high_risk and normalized_task != "web_search":
            # Only recommend web_search if it has worked at least 50% of the time
            total_recovery = recovery_successes + recovery_failures
            if total_recovery == 0:
                # No data yet - try web_search
                recommended_fallback = "web_search"
            elif recovery_successes / total_recovery >= 0.5:
                # Works at least half the time - recommend
                recommended_fallback = "web_search"
            # else: web_search doesn't help - skip

        return {
            "task_type": task_type,
            "destination": destination,
            "high_risk": high_risk,
            "task_failures": task_failures,
            "destination_failures": destination_failures,
            "hour_failures": hour_failures,
            "recommended_fallback": recommended_fallback,
            "recovery_success_rate": (
                round(recovery_successes / max(1, recovery_successes + recovery_failures), 2)
                if recovery_successes + recovery_failures > 0 else None
            ),
            "avg_recovery_improvement": round(avg_improvement, 3),
            "recovery_samples": len(recovery_improvements),
            "top_error_kind": max(error_kind_counts, key=error_kind_counts.get) if error_kind_counts else None,
        }

    async def get_learning_stats(self) -> Dict[str, Any]:
        """Get overall learning statistics."""
        self._ensure_loaded()
        
        total_failures = len(self.failures)
        total_recovery_records = sum(len(r) for r in self.recovery_records.values())
        
        # Calculate recovery success rate
        total_recovery_successes = 0
        total_recovery_attempts = 0
        for records in self.recovery_records.values():
            for record in records:
                if record.get("worked") is not None:
                    total_recovery_attempts += 1
                    if record.get("worked"):
                        total_recovery_successes += 1
        
        return {
            "total_failures": total_failures,
            "total_recovery_records": total_recovery_records,
            "recovery_success_rate": round(
                total_recovery_successes / max(1, total_recovery_attempts), 2
            ) if total_recovery_attempts > 0 else None,
            "tasks_with_recovery_data": len(self.recovery_records),
        }


_error_pattern_learner: Optional[ErrorPatternLearner] = None


def get_error_pattern_learner() -> ErrorPatternLearner:
    global _error_pattern_learner
    if _error_pattern_learner is None:
        _error_pattern_learner = ErrorPatternLearner()
    return _error_pattern_learner
