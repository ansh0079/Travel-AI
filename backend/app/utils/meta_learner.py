"""
Meta-Learning System - Learns how to improve recommendation strategies.

Persists data in the database so learning survives server restarts and deploys.
"""

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


def _serialize(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


class MetaLearner:
    PROFILE_ID = "__meta_learner__"
    MIN_SESSIONS_FOR_ADAPTATION = 5
    _ADAPT_EVERY = 10  # run analyze_and_adapt() every N new sessions
    DEFAULT_DECISION_WEIGHTS: Dict[str, float] = {
        "cost": 0.30,
        "weather": 0.25,
        "attractions": 0.20,
        "safety": 0.15,
        "visa_ease": 0.10,
    }

    def __init__(self):
        self.performance_history: List[Dict[str, Any]] = []
        self.strategy_effectiveness: Dict[str, List[bool]] = defaultdict(list)
        self.user_engagement_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.per_user_outcomes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.destination_acceptance_rates: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"accepted": 0, "rejected": 0}
        )
        self._last_analysis: Optional[Dict[str, Any]] = None
        self._per_user_analysis: Dict[str, Dict[str, Any]] = {}
        self._analysis_timestamp: Optional[datetime] = None
        self._sessions_since_last_adapt: int = 0
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
            logger.warning("MetaLearner: could not load persisted data", error=str(exc))
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
            logger.warning("MetaLearner: save failed", error=str(exc))
            return False
        finally:
            db.close()

    def _ensure_loaded(self) -> None:
        """Lazy-load persisted data on first use."""
        if self._loaded:
            return
        self._loaded = True
        data = self._sync_load_state()
        if not data:
            return

        self.performance_history = data.get("performance_history", [])[-1000:]
        self._last_analysis = data.get("last_analysis")
        per_user_analysis = data.get("per_user_analysis")
        self._per_user_analysis = per_user_analysis if isinstance(per_user_analysis, dict) else {}
        ts = data.get("analysis_timestamp")
        self._analysis_timestamp = datetime.fromisoformat(ts) if ts else None
        self._sessions_since_last_adapt = data.get("sessions_since_last_adapt", 0)
        self._rebuild_indexes()

        logger.info("MetaLearner: loaded persisted state", session_count=len(self.performance_history))

    def _rebuild_indexes(self) -> None:
        self.strategy_effectiveness = defaultdict(list)
        self.user_engagement_patterns = defaultdict(list)
        self.per_user_outcomes = defaultdict(list)
        self.destination_acceptance_rates = defaultdict(
            lambda: {"accepted": 0, "rejected": 0}
        )

        for record in self.performance_history:
            accepted = record.get("user_accepted")
            strategy = record.get("strategy", "default")
            if isinstance(accepted, bool):
                self.strategy_effectiveness[strategy].append(accepted)

            user_id = record.get("user_id")
            if user_id:
                self.user_engagement_patterns[user_id].append({
                    "engagement_seconds": record.get("engagement_seconds", 0),
                    "user_accepted": accepted,
                    "research_depth": record.get("research_depth", "standard"),
                    "timestamp": record.get("timestamp"),
                })
                if isinstance(accepted, bool):
                    self.per_user_outcomes[user_id].append(record)

            dest_chosen = record.get("destination_chosen")
            if not isinstance(accepted, bool):
                continue
            if dest_chosen:
                if accepted:
                    self.destination_acceptance_rates[dest_chosen]["accepted"] += 1
                else:
                    self.destination_acceptance_rates[dest_chosen]["rejected"] += 1
            if accepted and dest_chosen:
                for dest in record.get("destinations_shown", []):
                    if dest != dest_chosen:
                        self.destination_acceptance_rates[dest]["rejected"] += 1

    def _normalize_decision_context(self, raw_context: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(raw_context, dict):
            return None

        evaluations: List[Dict[str, Any]] = []
        for raw_evaluation in raw_context.get("evaluations") or []:
            if not isinstance(raw_evaluation, dict):
                continue

            destination = str(raw_evaluation.get("destination") or "").strip()
            if not destination:
                continue

            evaluation: Dict[str, Any] = {"destination": destination}
            for key in (
                "total_score",
                "personalized_total_score",
                "final_total_score",
                "confidence",
                "personalization_bonus",
                "engagement_boost",
            ):
                value = raw_evaluation.get(key)
                if isinstance(value, (int, float)):
                    evaluation[key] = round(float(value), 3)

            criteria_scores = {}
            for criterion, score in (raw_evaluation.get("criteria_scores") or {}).items():
                if isinstance(score, (int, float)):
                    criteria_scores[str(criterion)] = round(float(score), 3)
            if criteria_scores:
                evaluation["criteria_scores"] = criteria_scores

            criteria_weights = {}
            for criterion, weight in (raw_evaluation.get("criteria_weights") or {}).items():
                if isinstance(weight, (int, float)):
                    criteria_weights[str(criterion)] = round(float(weight), 3)
            if criteria_weights:
                evaluation["criteria_weights"] = criteria_weights

            evaluations.append(evaluation)

        if not evaluations:
            return None

        context: Dict[str, Any] = {
            "ranking_basis": str(raw_context.get("ranking_basis") or "default"),
            "best_destination": str(
                raw_context.get("best_destination") or evaluations[0]["destination"]
            ).strip(),
            "evaluations": evaluations,
        }

        best_score = raw_context.get("best_score")
        if isinstance(best_score, (int, float)):
            context["best_score"] = round(float(best_score), 3)

        selected_destination = str(raw_context.get("selected_destination") or "").strip()
        if selected_destination:
            context["selected_destination"] = selected_destination

        selected_evaluation = raw_context.get("selected_evaluation")
        if isinstance(selected_evaluation, dict):
            normalized_selected = self._normalize_decision_context(
                {"evaluations": [selected_evaluation]}
            )
            if normalized_selected:
                context["selected_evaluation"] = normalized_selected["evaluations"][0]

        return context

    def _resolve_decision_evaluation(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        context = self._normalize_decision_context(record.get("decision_context"))
        if not context:
            return None

        evaluations = context.get("evaluations") or []
        if not evaluations:
            return None

        chosen_destination = str(
            record.get("destination_chosen") or context.get("selected_destination") or ""
        ).strip()
        if chosen_destination:
            for evaluation in evaluations:
                if str(evaluation.get("destination") or "").strip().lower() == chosen_destination.lower():
                    return evaluation

        selected_evaluation = context.get("selected_evaluation")
        if isinstance(selected_evaluation, dict):
            return selected_evaluation

        return evaluations[0]

    async def _save_state(self) -> None:
        """Persist current state to the database (non-blocking via executor)."""
        async with _SAVE_LOCK:
            payload = {
                "performance_history": _serialize(self.performance_history[-1000:]),
                "last_analysis": _serialize(self._last_analysis),
                "per_user_analysis": _serialize(self._per_user_analysis),
                "analysis_timestamp": self._analysis_timestamp.isoformat() if self._analysis_timestamp else None,
                "sessions_since_last_adapt": self._sessions_since_last_adapt,
            }
            try:
                await asyncio.to_thread(self._sync_save_state, payload)
            except Exception as exc:
                logger.warning("MetaLearner: save failed", error=str(exc))

    async def record_session_outcome(self, session_data: Dict[str, Any]) -> None:
        """Record a session outcome for later analysis."""
        self._ensure_loaded()

        record = {
            "session_id": session_data.get("session_id"),
            "user_id": session_data.get("user_id"),
            "research_depth": session_data.get("research_depth", "standard"),
            "strategy": session_data.get("strategy", "default"),
            "task_count": session_data.get("task_count", 0),
            "user_accepted": (
                session_data.get("user_accepted")
                if isinstance(session_data.get("user_accepted"), bool)
                else None
            ),
            "user_rating": session_data.get("user_rating", 3),
            "engagement_seconds": session_data.get("engagement_seconds", 0),
            "destinations_shown": session_data.get("destinations_shown", []),
            "destination_chosen": session_data.get("destination_chosen"),
            "decision_context": self._normalize_decision_context(session_data.get("decision_context")),
            "timestamp": session_data.get("timestamp", datetime.now().isoformat()),
        }

        self.performance_history.append(record)

        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]

        self._rebuild_indexes()
        self._per_user_analysis = {}
        self._sessions_since_last_adapt += 1

        # Auto-adapt every N sessions
        if self._sessions_since_last_adapt >= self._ADAPT_EVERY:
            try:
                await self.analyze_and_adapt()
                self._sessions_since_last_adapt = 0
            except Exception as exc:
                logger.warning(f"MetaLearner: auto-adapt failed: {exc}")

        await self._save_state()
        logger.info("MetaLearner: recorded session outcome", session_id=record["session_id"])

    async def update_session_feedback(
        self,
        session_id: str,
        user_accepted: bool,
        destination_chosen: Optional[str] = None,
        rating: int = 3,
    ) -> None:
        """Update a previously recorded session with real feedback from the user.

        Called from the feedback endpoint so we get actual accept/reject signals
        rather than the hardcoded True we used to emit at research-complete time.
        """
        self._ensure_loaded()
        for record in reversed(self.performance_history):
            if record.get("session_id") == session_id:
                record["user_accepted"] = user_accepted
                record["user_rating"] = rating
                if destination_chosen:
                    record["destination_chosen"] = destination_chosen
                context = self._normalize_decision_context(record.get("decision_context"))
                if context:
                    if destination_chosen:
                        context["selected_destination"] = destination_chosen
                    selected_evaluation = self._resolve_decision_evaluation(
                        {
                            **record,
                            "destination_chosen": destination_chosen or record.get("destination_chosen"),
                            "decision_context": context,
                        }
                    )
                    if selected_evaluation:
                        context["selected_evaluation"] = selected_evaluation
                    record["decision_context"] = context
                break

        self._rebuild_indexes()
        self._per_user_analysis = {}

        await self._save_state()

    def _compute_strategy_scores(
        self,
        records: List[Dict[str, Any]],
        min_samples: int = 3,
    ) -> Dict[str, float]:
        strategy_stats: Dict[str, List[bool]] = defaultdict(list)
        for record in records:
            accepted = record.get("user_accepted")
            if not isinstance(accepted, bool):
                continue
            strategy = record.get("strategy", "default")
            strategy_stats[strategy].append(accepted)

        strategy_scores = {}
        for strategy, outcomes in strategy_stats.items():
            if len(outcomes) >= min_samples:
                strategy_scores[strategy] = round(sum(outcomes) / len(outcomes), 2)
        return strategy_scores

    def _build_analysis(
        self,
        records: List[Dict[str, Any]],
        *,
        strategy_min_samples: int,
        depth_min_samples: int,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        strategy_scores = self._compute_strategy_scores(records, min_samples=strategy_min_samples)
        best_strategy = max(strategy_scores, key=strategy_scores.get) if strategy_scores else "default"
        depth_performance = self._analyze_depth_performance(
            records=records,
            min_samples=depth_min_samples,
        )
        optimal_depth = depth_performance.get("best_depth", "standard")
        decision_weight_profile = self._build_decision_weight_profile(
            records,
            min_samples=depth_min_samples,
            source="per_user" if user_id else "global",
        )

        adaptations = []
        if best_strategy != "default":
            adaptations.append({
                "type": "strategy_change",
                "priority": "high",
                "recommendation": f"Use '{best_strategy}' strategy more often",
                "confidence": strategy_scores.get(best_strategy, 0),
            })

        if optimal_depth != "standard":
            adaptations.append({
                "type": "depth_adjustment",
                "priority": "medium",
                "recommendation": f"Default to '{optimal_depth}' research depth",
                "confidence": depth_performance.get("confidence", 0),
            })

        decision_confidence = float(decision_weight_profile.get("confidence", 0.0) or 0.0)
        decision_source = str(decision_weight_profile.get("source") or "")
        if decision_confidence >= 0.08 and decision_source not in {"default", "per_user_fallback"}:
            top_criterion = next(
                iter(
                    sorted(
                        (decision_weight_profile.get("criterion_signals") or {}).items(),
                        key=lambda item: abs(float(item[1])),
                        reverse=True,
                    )
                ),
                None,
            )
            if top_criterion:
                adaptations.append({
                    "type": "decision_weighting",
                    "priority": "medium",
                    "recommendation": f"Bias decision scoring toward '{top_criterion[0]}' based on feedback loop",
                    "confidence": round(decision_confidence, 2),
                })

        # ── A/B experiment analysis ──────────────────────────────────
        # Compare exploration sessions (random depth) vs exploitation
        # sessions (optimal depth) to validate or update strategy.
        exploration_records = [r for r in records if r.get("is_exploration")]
        exploitation_records = [r for r in records if not r.get("is_exploration")]
        experiment_analysis: Optional[Dict[str, Any]] = None
        if len(exploration_records) >= 3 and len(exploitation_records) >= 3:
            def _acceptance_rate(recs: list) -> float:
                labeled = [r for r in recs if isinstance(r.get("user_accepted"), bool)]
                if not labeled:
                    return 0.0
                return sum(1 for r in labeled if r["user_accepted"]) / len(labeled)

            explore_rate = _acceptance_rate(exploration_records)
            exploit_rate = _acceptance_rate(exploitation_records)
            experiment_analysis = {
                "exploration_sessions": len(exploration_records),
                "exploitation_sessions": len(exploitation_records),
                "exploration_acceptance_rate": round(explore_rate, 3),
                "exploitation_acceptance_rate": round(exploit_rate, 3),
                "exploration_outperforms": explore_rate > exploit_rate,
            }
            # If exploration consistently outperforms, promote it
            if explore_rate > exploit_rate + 0.10 and len(exploration_records) >= 5:
                # Find which depth the exploration sessions used most
                explore_depths = [r.get("exploration_depth") or r.get("research_depth") for r in exploration_records]
                from collections import Counter
                depth_counts = Counter(explore_depths)
                winning_depth = depth_counts.most_common(1)[0][0] if depth_counts else None
                if winning_depth and winning_depth != optimal_depth:
                    optimal_depth = winning_depth
                    adaptations.append({
                        "type": "ab_experiment_promotion",
                        "priority": "high",
                        "recommendation": (
                            f"A/B experiment: '{winning_depth}' depth outperforms "
                            f"'{depth_performance.get('best_depth', 'standard')}' "
                            f"({explore_rate:.0%} vs {exploit_rate:.0%}). Promoting."
                        ),
                        "confidence": round(explore_rate - exploit_rate, 2),
                    })
                    logger.info(
                        f"MetaLearner A/B: promoting {winning_depth} "
                        f"(explore {explore_rate:.0%} > exploit {exploit_rate:.0%})"
                    )

        analysis = {
            "best_strategy": best_strategy,
            "strategy_scores": strategy_scores,
            "optimal_research_depth": optimal_depth,
            "decision_weight_profile": decision_weight_profile,
            "adaptations": adaptations,
            "experiment_analysis": experiment_analysis,
            "sessions_analyzed": len(records),
            "analyzed_at": datetime.now().isoformat(),
        }
        if user_id:
            analysis.update({
                "user_id": user_id,
                "user_sessions_analyzed": len(records),
                "user_depth_confidence": round(depth_performance.get("confidence", 0), 2),
                "user_strategy_confidence": round(strategy_scores.get(best_strategy, 0), 2),
            })
        return analysis

    def _build_per_user_analysis(self, user_id: str) -> Optional[Dict[str, Any]]:
        user_sessions = list(self.per_user_outcomes.get(user_id) or [])
        if len(user_sessions) < 3:
            return None

        return self._build_analysis(
            user_sessions,
            strategy_min_samples=2,
            depth_min_samples=2,
            user_id=user_id,
        )

    def _build_decision_weight_profile(
        self,
        records: List[Dict[str, Any]],
        *,
        min_samples: int,
        source: str,
    ) -> Dict[str, Any]:
        base_weights = dict(self.DEFAULT_DECISION_WEIGHTS)
        criterion_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {
                "accepted_total": 0.0,
                "rejected_total": 0.0,
                "accepted_count": 0,
                "rejected_count": 0,
                "weight_total": 0.0,
                "weight_count": 0,
            }
        )
        sessions_with_context = 0

        for record in records:
            if not isinstance(record.get("user_accepted"), bool):
                continue

            evaluation = self._resolve_decision_evaluation(record)
            if not evaluation:
                continue

            sessions_with_context += 1
            accepted = bool(record.get("user_accepted"))
            criteria_scores = evaluation.get("criteria_scores") or {}
            criteria_weights = evaluation.get("criteria_weights") or {}

            for criterion, raw_score in criteria_scores.items():
                if not isinstance(raw_score, (int, float)):
                    continue

                criterion_name = str(criterion)
                bucket = criterion_stats[criterion_name]
                score = float(raw_score)
                if accepted:
                    bucket["accepted_total"] += score
                    bucket["accepted_count"] += 1
                else:
                    bucket["rejected_total"] += score
                    bucket["rejected_count"] += 1

                try:
                    weight = float(criteria_weights.get(criterion_name, base_weights.get(criterion_name, 0.0)) or 0.0)
                except (TypeError, ValueError):
                    weight = 0.0
                if weight > 0:
                    bucket["weight_total"] += weight
                    bucket["weight_count"] += 1

        if sessions_with_context == 0:
            return {
                "source": "default",
                "weights": base_weights,
                "confidence": 0.0,
                "sessions_with_decision_context": 0,
                "criterion_signals": {},
                "sample_counts": {},
            }

        raw_weights: Dict[str, float] = {}
        criterion_signals: Dict[str, float] = {}
        sample_counts: Dict[str, int] = {}
        confidence_total = 0.0
        confidence_terms = 0

        for criterion_name, base_weight in base_weights.items():
            bucket = criterion_stats.get(criterion_name) or {}
            accepted_count = int(bucket.get("accepted_count", 0))
            rejected_count = int(bucket.get("rejected_count", 0))
            sample_count = accepted_count + rejected_count
            sample_counts[criterion_name] = sample_count

            raw_weight = base_weight
            if (
                sample_count >= min_samples
                and accepted_count > 0
                and rejected_count > 0
            ):
                accepted_avg = float(bucket.get("accepted_total", 0.0)) / accepted_count
                rejected_avg = float(bucket.get("rejected_total", 0.0)) / rejected_count
                avg_weight = (
                    float(bucket.get("weight_total", 0.0)) / int(bucket.get("weight_count", 0))
                    if int(bucket.get("weight_count", 0)) > 0
                    else base_weight
                )
                score_lift = accepted_avg - rejected_avg
                weighted_signal = score_lift * max(avg_weight, base_weight)
                criterion_signals[criterion_name] = round(weighted_signal, 3)

                confidence = min(1.0, sample_count / max(float(min_samples * 3), 6.0))
                evidence_strength = 0.15 + (0.45 * confidence)
                multiplier = 1.0 + max(-0.35, min(0.35, weighted_signal * 3.0))
                proposed_weight = base_weight * multiplier
                raw_weight = (
                    (base_weight * (1.0 - evidence_strength))
                    + (proposed_weight * evidence_strength)
                )
                confidence_total += confidence
                confidence_terms += 1

            raw_weights[criterion_name] = max(0.02, raw_weight)

        total_weight = sum(raw_weights.values()) or 1.0
        normalized_weights = {
            criterion_name: round(weight / total_weight, 3)
            for criterion_name, weight in raw_weights.items()
        }

        profile_source = source
        if confidence_terms == 0:
            profile_source = "default" if source == "global" else f"{source}_fallback"

        coverage = sessions_with_context / max(
            1,
            len([record for record in records if isinstance(record.get("user_accepted"), bool)]),
        )
        confidence = (
            (confidence_total / confidence_terms) * coverage
            if confidence_terms > 0
            else 0.0
        )

        return {
            "source": profile_source,
            "weights": normalized_weights,
            "confidence": round(confidence, 3),
            "sessions_with_decision_context": sessions_with_context,
            "criterion_signals": criterion_signals,
            "sample_counts": sample_counts,
        }

    def get_decision_weight_profile(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        self._ensure_loaded()

        if user_id:
            user_records = list(self.per_user_outcomes.get(user_id) or [])
            if len(user_records) >= 3:
                return self._build_decision_weight_profile(
                    user_records,
                    min_samples=2,
                    source="per_user",
                )

        labeled_records = [
            record for record in self.performance_history
            if isinstance(record.get("user_accepted"), bool)
        ]
        return self._build_decision_weight_profile(
            labeled_records,
            min_samples=3,
            source="global",
        )

    def get_decision_feedback_insights(self) -> Dict[str, Any]:
        self._ensure_loaded()
        labeled_records = [
            record for record in self.performance_history
            if isinstance(record.get("user_accepted"), bool)
        ]

        if not labeled_records:
            return {
                "labeled_sessions": 0,
                "sessions_with_decision_context": 0,
                "coverage": 0.0,
                "criteria_effectiveness": [],
                "ranking_basis_performance": {},
                "learned_weights": dict(self.DEFAULT_DECISION_WEIGHTS),
            }

        criteria_rollup: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {
                "samples": 0,
                "accepted_count": 0,
                "rejected_count": 0,
                "accepted_score_total": 0.0,
                "rejected_score_total": 0.0,
                "accepted_weight_total": 0.0,
                "rejected_weight_total": 0.0,
                "accepted_contribution_total": 0.0,
                "rejected_contribution_total": 0.0,
                "high_score_total": 0,
                "high_score_accepted": 0,
                "low_score_total": 0,
                "low_score_accepted": 0,
            }
        )
        ranking_rollup: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"accepted": 0, "total": 0}
        )
        sessions_with_context = 0

        for record in labeled_records:
            context = self._normalize_decision_context(record.get("decision_context"))
            evaluation = self._resolve_decision_evaluation(record)
            if not context or not evaluation:
                continue

            sessions_with_context += 1
            accepted = bool(record.get("user_accepted"))
            ranking_basis = str(context.get("ranking_basis") or "default")
            ranking_rollup[ranking_basis]["total"] += 1
            if accepted:
                ranking_rollup[ranking_basis]["accepted"] += 1

            criteria_scores = evaluation.get("criteria_scores") or {}
            criteria_weights = evaluation.get("criteria_weights") or {}
            for criterion, raw_score in criteria_scores.items():
                if not isinstance(raw_score, (int, float)):
                    continue

                score = float(raw_score)
                try:
                    weight = float(criteria_weights.get(criterion, 0.0) or 0.0)
                except (TypeError, ValueError):
                    weight = 0.0
                contribution = score * weight if weight > 0 else score

                bucket = criteria_rollup[str(criterion)]
                bucket["samples"] += 1
                if accepted:
                    bucket["accepted_count"] += 1
                    bucket["accepted_score_total"] += score
                    bucket["accepted_weight_total"] += weight
                    bucket["accepted_contribution_total"] += contribution
                else:
                    bucket["rejected_count"] += 1
                    bucket["rejected_score_total"] += score
                    bucket["rejected_weight_total"] += weight
                    bucket["rejected_contribution_total"] += contribution

                if score >= 0.65:
                    bucket["high_score_total"] += 1
                    if accepted:
                        bucket["high_score_accepted"] += 1
                else:
                    bucket["low_score_total"] += 1
                    if accepted:
                        bucket["low_score_accepted"] += 1

        criteria_effectiveness = []
        for criterion, bucket in criteria_rollup.items():
            accepted_count = int(bucket["accepted_count"])
            rejected_count = int(bucket["rejected_count"])
            accepted_avg_score = (
                bucket["accepted_score_total"] / accepted_count
                if accepted_count else None
            )
            rejected_avg_score = (
                bucket["rejected_score_total"] / rejected_count
                if rejected_count else None
            )
            accepted_avg_weight = (
                bucket["accepted_weight_total"] / accepted_count
                if accepted_count else None
            )
            rejected_avg_weight = (
                bucket["rejected_weight_total"] / rejected_count
                if rejected_count else None
            )
            accepted_avg_contribution = (
                bucket["accepted_contribution_total"] / accepted_count
                if accepted_count else None
            )
            rejected_avg_contribution = (
                bucket["rejected_contribution_total"] / rejected_count
                if rejected_count else None
            )
            score_lift = None
            weighted_lift = None
            if accepted_avg_score is not None and rejected_avg_score is not None:
                score_lift = accepted_avg_score - rejected_avg_score
            if (
                accepted_avg_contribution is not None
                and rejected_avg_contribution is not None
            ):
                weighted_lift = accepted_avg_contribution - rejected_avg_contribution

            if weighted_lift is None and score_lift is None:
                signal = "insufficient"
            elif (weighted_lift if weighted_lift is not None else score_lift) > 0.05:
                signal = "positive"
            elif (weighted_lift if weighted_lift is not None else score_lift) < -0.05:
                signal = "negative"
            else:
                signal = "mixed"

            high_score_acceptance_rate = (
                bucket["high_score_accepted"] / bucket["high_score_total"]
                if bucket["high_score_total"] else None
            )
            low_score_acceptance_rate = (
                bucket["low_score_accepted"] / bucket["low_score_total"]
                if bucket["low_score_total"] else None
            )

            criteria_effectiveness.append(
                {
                    "criterion": criterion,
                    "samples": int(bucket["samples"]),
                    "accepted_avg_score": round(accepted_avg_score, 3) if accepted_avg_score is not None else None,
                    "rejected_avg_score": round(rejected_avg_score, 3) if rejected_avg_score is not None else None,
                    "accepted_avg_weight": round(accepted_avg_weight, 3) if accepted_avg_weight is not None else None,
                    "rejected_avg_weight": round(rejected_avg_weight, 3) if rejected_avg_weight is not None else None,
                    "score_lift": round(score_lift, 3) if score_lift is not None else None,
                    "weighted_contribution_lift": round(weighted_lift, 3) if weighted_lift is not None else None,
                    "high_score_acceptance_rate": round(high_score_acceptance_rate, 3) if high_score_acceptance_rate is not None else None,
                    "low_score_acceptance_rate": round(low_score_acceptance_rate, 3) if low_score_acceptance_rate is not None else None,
                    "signal": signal,
                }
            )

        criteria_effectiveness.sort(
            key=lambda item: abs(
                item.get("weighted_contribution_lift")
                if item.get("weighted_contribution_lift") is not None
                else (item.get("score_lift") or 0.0)
            ),
            reverse=True,
        )

        ranking_basis_performance = {
            ranking_basis: {
                "sessions": stats["total"],
                "acceptance_rate": round(stats["accepted"] / stats["total"], 3),
            }
            for ranking_basis, stats in ranking_rollup.items()
            if stats["total"] > 0
        }

        return {
            "labeled_sessions": len(labeled_records),
            "sessions_with_decision_context": sessions_with_context,
            "coverage": round(sessions_with_context / max(1, len(labeled_records)), 3),
            "criteria_effectiveness": criteria_effectiveness,
            "ranking_basis_performance": ranking_basis_performance,
            "learned_weights": self.get_decision_weight_profile().get("weights", dict(self.DEFAULT_DECISION_WEIGHTS)),
        }

    async def analyze_and_adapt(self) -> Dict[str, Any]:
        """Analyze performance history and generate adaptation recommendations."""
        self._ensure_loaded()

        labeled_sessions = [
            record for record in self.performance_history
            if isinstance(record.get("user_accepted"), bool)
        ]
        if len(labeled_sessions) < self.MIN_SESSIONS_FOR_ADAPTATION:
            return {
                "status": "insufficient_data",
                "sessions_recorded": len(labeled_sessions),
            }

        self._last_analysis = self._build_analysis(
            labeled_sessions,
            strategy_min_samples=3,
            depth_min_samples=3,
        )
        self._per_user_analysis = {}
        for user_id in self.per_user_outcomes:
            user_analysis = self._build_per_user_analysis(user_id)
            if user_analysis:
                self._per_user_analysis[user_id] = user_analysis
        self._analysis_timestamp = datetime.now()

        logger.info(
            f"MetaLearner: adapt complete - best_strategy={self._last_analysis['best_strategy']}, "
            f"optimal_depth={self._last_analysis['optimal_research_depth']}, "
            f"adaptations={len(self._last_analysis['adaptations'])}, "
            f"per_user_profiles={len(self._per_user_analysis)}"
        )
        await self._save_state()
        return self._last_analysis

    def get_recommendations(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Return the latest analysis/recommendations.

        If *user_id* is supplied and we have >=3 labeled sessions for that user,
        return a per-user recommendation that overrides the global default.
        Otherwise fall back to the global analysis.
        """
        self._ensure_loaded()
        global_recs = dict(self._last_analysis or {})

        if not user_id:
            return global_recs

        user_recs = self._per_user_analysis.get(user_id) or self._build_per_user_analysis(user_id)
        if not user_recs:
            global_recs["per_user"] = False
            return global_recs

        logger.info(
            f"MetaLearner: per-user recs for {user_id} - "
            f"depth={user_recs['optimal_research_depth']} ({user_recs.get('user_depth_confidence', 0):.0%}), "
            f"strategy={user_recs['best_strategy']} ({user_recs.get('user_strategy_confidence', 0):.0%}), "
            f"sessions={user_recs.get('user_sessions_analyzed', 0)}"
        )
        return {**global_recs, **user_recs, "per_user": True}

    def _analyze_depth_performance(
        self,
        records: Optional[List[Dict[str, Any]]] = None,
        min_samples: int = 3,
    ) -> Dict[str, Any]:
        depth_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"accepted": 0, "total": 0})

        for record in records or self.performance_history:
            accepted = record.get("user_accepted")
            if not isinstance(accepted, bool):
                continue
            depth = record["research_depth"]
            depth_stats[depth]["total"] += 1
            if accepted:
                depth_stats[depth]["accepted"] += 1

        best_depth = "standard"
        best_rate = 0.0

        for depth, stats in depth_stats.items():
            if stats["total"] >= min_samples:
                rate = stats["accepted"] / stats["total"]
                if rate > best_rate:
                    best_rate = rate
                    best_depth = depth

        return {
            "best_depth": best_depth,
            "confidence": best_rate,
            "depth_stats": dict(depth_stats),
        }

    async def get_learning_stats(self) -> Dict[str, Any]:
        self._ensure_loaded()
        labeled_sessions = [
            record for record in self.performance_history
            if isinstance(record.get("user_accepted"), bool)
        ]
        total_sessions = len(labeled_sessions)
        total_acceptances = sum(1 for record in labeled_sessions if record["user_accepted"])
        overall_acceptance_rate = total_acceptances / total_sessions if total_sessions > 0 else 0

        return {
            "total_sessions": len(self.performance_history),
            "labeled_sessions": total_sessions,
            "total_acceptances": total_acceptances,
            "overall_acceptance_rate": round(overall_acceptance_rate, 2),
            "strategies_tracked": len(self.strategy_effectiveness),
            "users_tracked": len(self.user_engagement_patterns),
            "users_with_personalized_analysis": len(self._per_user_analysis),
            "destinations_tracked": len(self.destination_acceptance_rates),
            "last_analysis": self._analysis_timestamp.isoformat() if self._analysis_timestamp else None,
        }

    def get_destination_insights(self, destination: str) -> Dict[str, Any]:
        self._ensure_loaded()
        stats = self.destination_acceptance_rates.get(destination, {"accepted": 0, "rejected": 0})
        total = stats["accepted"] + stats["rejected"]

        if total == 0:
            return {"destination": destination, "acceptance_rate": None, "message": "No data"}

        acceptance_rate = stats["accepted"] / total
        return {
            "destination": destination,
            "acceptance_rate": round(acceptance_rate, 2),
            "times_accepted": stats["accepted"],
            "times_rejected": stats["rejected"],
        }

    def predict_acceptance(
        self,
        destination: str,
        prefs: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> float:
        """Predict the probability (0.0–1.0) that a user will accept *destination*.

        Uses a Beta-distribution mode from ``destination_acceptance_rates`` as
        the base rate, then applies lightweight adjustments for budget match,
        interest overlap, and strategy signals from performance history.
        """
        self._ensure_loaded()
        prefs = prefs or {}

        # ── Base rate from observed accept/reject counts (Beta mode) ─────────
        stats = self.destination_acceptance_rates.get(destination, {"accepted": 0, "rejected": 0})
        alpha = stats["accepted"] + 1   # Beta(α, β) with Laplace smoothing
        beta = stats["rejected"] + 1
        # Mode of Beta(α,β) = (α-1)/(α+β-2) for α,β>1, else 0.5
        total = alpha + beta - 2
        base_rate: float = (alpha - 1) / total if total > 0 else 0.5

        score = base_rate

        # ── Interest overlap adjustment ────────────────────────────────────
        from app.config import POPULAR_DESTINATIONS
        dest_tags: set = set()
        for entry in POPULAR_DESTINATIONS:
            if str(entry.get("name") or "").strip().lower() == destination.strip().lower():
                dest_tags = {str(t).strip().lower() for t in (entry.get("focus_tags") or []) if t}
                break

        user_interests = {str(i).strip().lower() for i in (prefs.get("interests") or []) if i}
        if dest_tags and user_interests:
            overlap = len(dest_tags & user_interests)
            score += 0.05 * min(overlap, 3)   # up to +0.15

        # ── Budget match adjustment ────────────────────────────────────────
        user_budget = str(prefs.get("budget_level") or "").strip().lower()
        if user_budget:
            for entry in POPULAR_DESTINATIONS:
                if str(entry.get("name") or "").strip().lower() == destination.strip().lower():
                    dest_budget = str(entry.get("budget_band") or "").strip().lower()
                    if dest_budget and dest_budget == user_budget:
                        score += 0.08
                    elif dest_budget and {dest_budget, user_budget} <= {"budget", "moderate"}:
                        score += 0.03
                    break

        # ── Strategy bonus for repeat users ───────────────────────────────
        if user_id and self.per_user_outcomes.get(user_id):
            score += 0.10  # personalized_priority gets a boost

        return round(min(max(score, 0.0), 1.0), 3)

    def rank_candidates(
        self,
        candidates: List[str],
        prefs: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> List[str]:
        """Return *candidates* sorted by predicted acceptance score (descending)."""
        scored = [
            (self.predict_acceptance(dest, prefs=prefs, user_id=user_id), dest)
            for dest in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [dest for _, dest in scored]

_meta_learner_instance: Optional[MetaLearner] = None


def get_meta_learner() -> MetaLearner:
    """Get or create the meta-learner singleton."""
    global _meta_learner_instance
    if _meta_learner_instance is None:
        _meta_learner_instance = MetaLearner()
    return _meta_learner_instance
