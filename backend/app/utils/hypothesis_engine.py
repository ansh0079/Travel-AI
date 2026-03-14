"""
Hypothesis Generation Engine
============================

Causal reasoning for travel recommendations.
Moves from pattern recognition to causal understanding.

Examples:
- "Rejected 3 cities for weather → suggest warm destinations"
- "User always accepts beach destinations → prioritize coastal options"
- "Budget rejections cluster in Europe → suggest Southeast Asia"

Features:
- Detects patterns in rejections and acceptances
- Generates hypotheses about user preferences
- Tests hypotheses against historical data
- Provides actionable recommendations to downstream systems
"""

import asyncio
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from app.database.connection import SessionLocal, engine
from app.database.models import LearnedUserProfile
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_SAVE_LOCK = asyncio.Lock()

# Hypothesis templates with pattern detection rules
HYPOTHESIS_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "weather_preference": {
        "pattern": "Multiple rejections mentioning weather",
        "trigger": {"rejection_reasons": ["weather", "too cold", "too hot", "rainy", "monsoon"]},
        "hypothesis": "User has strong weather preferences",
        "action": "Filter destinations by climate matching",
        "confidence_threshold": 0.7,
    },
    "budget_constraint": {
        "pattern": "Consistent price-based rejections",
        "trigger": {"rejection_reasons": ["expensive", "too expensive", "over budget", "price"]},
        "hypothesis": "User is budget-constrained",
        "action": "Prioritize affordable destinations, show value options",
        "confidence_threshold": 0.6,
    },
    "interest_focus": {
        "pattern": "Strong engagement with specific interest category",
        "trigger": {"acceptance_features": ["culture", "adventure", "beach", "nightlife", "food"]},
        "hypothesis": "User has focused interest in {interest}",
        "action": "Boost destinations strong in {interest}",
        "confidence_threshold": 0.5,
    },
    "destination_type_preference": {
        "pattern": "Consistent acceptance of destination type",
        "trigger": {"destination_traits": ["city", "beach", "mountain", "rural", "tropical"]},
        "hypothesis": "User prefers {type} destinations",
        "action": "Prioritize {type} destinations",
        "confidence_threshold": 0.6,
    },
    "travel_style_match": {
        "pattern": "Pattern in activity level / comfort preferences",
        "trigger": {"behavioral_signals": ["high_activity", "luxury", "backpacking", "family_friendly"]},
        "hypothesis": "User travels in {style} style",
        "action": "Match destination offerings to travel style",
        "confidence_threshold": 0.5,
    },
    "regional_bias": {
        "pattern": "Acceptance/rejection clustering by region",
        "trigger": {"regions": ["Europe", "Asia", "Americas", "Africa", "Oceania"]},
        "hypothesis": "User prefers/avoids {region}",
        "action": "Adjust regional diversity in recommendations",
        "confidence_threshold": 0.6,
    },
    "seasonal_preference": {
        "pattern": "Different choices based on travel season",
        "trigger": {"seasonal_patterns": True},
        "hypothesis": "User preferences vary by season",
        "action": "Apply season-aware recommendation strategy",
        "confidence_threshold": 0.7,
    },
    "duration_constraint": {
        "pattern": "Rejections related to trip length",
        "trigger": {"rejection_reasons": ["too long", "too short", "not enough time"]},
        "hypothesis": "User has specific duration preferences",
        "action": "Filter by optimal trip duration",
        "confidence_threshold": 0.5,
    },
    "visa_sensitivity": {
        "pattern": "Rejections mentioning visa requirements",
        "trigger": {"rejection_reasons": ["visa", "visa required", "visa hassle"]},
        "hypothesis": "User prefers visa-free/easy visa destinations",
        "action": "Prioritize visa-friendly destinations",
        "confidence_threshold": 0.6,
    },
    "flight_time_sensitivity": {
        "pattern": "Concerns about travel duration",
        "trigger": {"rejection_reasons": ["too far", "long flight", "travel time"]},
        "hypothesis": "User is sensitive to flight duration",
        "action": "Filter by maximum flight time",
        "confidence_threshold": 0.5,
    },
    # ── Criteria-score-based hypotheses (causal, not text-based) ──
    "low_safety_rejection": {
        "pattern": "Rejections where safety criterion scored low",
        "trigger": {"rejection_reasons": ["low_safety"], "acceptance_features": []},
        "hypothesis": "User prioritises destination safety",
        "action": "Filter out destinations with safety score < 0.5",
        "confidence_threshold": 0.5,
    },
    "low_cost_rejection": {
        "pattern": "Rejections where cost criterion scored low (expensive)",
        "trigger": {"rejection_reasons": ["low_cost", "low_price"], "acceptance_features": []},
        "hypothesis": "User is cost-sensitive based on objective pricing data",
        "action": "Prioritise affordable destinations by cost criterion",
        "confidence_threshold": 0.5,
    },
    "low_attractions_rejection": {
        "pattern": "Rejections where attractions criterion scored low",
        "trigger": {"rejection_reasons": ["low_attractions"], "acceptance_features": []},
        "hypothesis": "User requires strong attraction offerings",
        "action": "Only recommend destinations with attractions score >= 0.6",
        "confidence_threshold": 0.5,
    },
    "low_weather_rejection": {
        "pattern": "Rejections where weather criterion scored poorly",
        "trigger": {"rejection_reasons": ["low_weather"], "acceptance_features": []},
        "hypothesis": "User needs favourable weather conditions",
        "action": "Filter by weather comfort score >= 0.6",
        "confidence_threshold": 0.5,
    },
    "low_visa_ease_rejection": {
        "pattern": "Rejections where visa criterion scored poorly",
        "trigger": {"rejection_reasons": ["low_visa_ease"], "acceptance_features": []},
        "hypothesis": "User avoids destinations with complex visa requirements",
        "action": "Prioritise visa-free or visa-on-arrival destinations",
        "confidence_threshold": 0.5,
    },
}


class Hypothesis:
    """Represents a generated hypothesis about user preferences."""

    def __init__(
        self,
        hypothesis_id: str,
        template_name: str,
        hypothesis_text: str,
        confidence: float,
        evidence: List[Dict[str, Any]],
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.id = hypothesis_id
        self.template_name = template_name
        self.text = hypothesis_text
        self.confidence = confidence
        self.evidence = evidence
        self.action = action
        self.parameters = parameters or {}
        self.created_at = datetime.now()
        self.last_validated = None
        self.validation_status = "pending"  # pending, validated, refuted

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_name": self.template_name,
            "hypothesis": self.text,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "action": self.action,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "validation_status": self.validation_status,
        }


class HypothesisGenerationEngine:
    """
    Generates and validates hypotheses about user preferences.
    
    Process:
    1. Observe user interactions (acceptances, rejections, feedback)
    2. Detect patterns that match hypothesis templates
    3. Generate hypotheses with confidence scores
    4. Test hypotheses against historical data
    5. Promote validated hypotheses to active preferences
    """

    GLOBAL_PROFILE_ID = "__hypothesis_engine__"
    MIN_EVIDENCE_FOR_HYPOTHESIS = 3
    _VALIDATE_EVERY = 25  # validate hypotheses every N interactions

    def __init__(self):
        # Active hypotheses per user
        # {user_id: [Hypothesis]}
        self.user_hypotheses: Dict[str, List[Hypothesis]] = defaultdict(list)
        
        # Global hypotheses (apply to all users)
        self.global_hypotheses: List[Hypothesis] = []
        
        # Evidence store for hypothesis generation
        # {user_id: [interaction_data]}
        self.user_evidence: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Hypothesis validation history
        self.validation_history: List[Dict[str, Any]] = []
        
        # Pattern detection cache
        self.detected_patterns: Dict[str, Dict[str, Any]] = {}
        
        # State management
        self._loaded = False
        self._table_ready = False
        self._interactions_since_validate = 0

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
                .filter(LearnedUserProfile.user_id == self.GLOBAL_PROFILE_ID)
                .first()
            )
            if not record or not record.profile_json:
                return {}
            payload = json.loads(record.profile_json)
            return payload if isinstance(payload, dict) else {}
        except Exception as exc:
            logger.warning("HypothesisGenerationEngine: could not load persisted data", error=str(exc))
            return {}
        finally:
            db.close()

    def _sync_save_state(self, payload: Dict[str, Any]) -> bool:
        self._ensure_table()
        db = SessionLocal()
        try:
            record = (
                db.query(LearnedUserProfile)
                .filter(LearnedUserProfile.user_id == self.GLOBAL_PROFILE_ID)
                .first()
            )
            if record is None:
                record = LearnedUserProfile(user_id=self.GLOBAL_PROFILE_ID)
                db.add(record)
            record.profile_json = json.dumps(payload)
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            logger.warning("HypothesisGenerationEngine: save failed", error=str(exc))
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

        # Restore user hypotheses
        user_hyp_data = data.get("user_hypotheses", {})
        for user_id, hyp_list in user_hyp_data.items():
            if isinstance(hyp_list, list):
                self.user_hypotheses[user_id] = [
                    Hypothesis(
                        hypothesis_id=h.get("id", ""),
                        template_name=h.get("template_name", ""),
                        hypothesis_text=h.get("hypothesis", ""),
                        confidence=float(h.get("confidence", 0)),
                        evidence=h.get("evidence", []),
                        action=h.get("action", ""),
                        parameters=h.get("parameters", {}),
                    )
                    for h in hyp_list
                    if isinstance(h, dict)
                ]

        # Restore global hypotheses
        global_hyp_data = data.get("global_hypotheses", [])
        self.global_hypotheses = [
            Hypothesis(
                hypothesis_id=h.get("id", ""),
                template_name=h.get("template_name", ""),
                hypothesis_text=h.get("hypothesis", ""),
                confidence=float(h.get("confidence", 0)),
                evidence=h.get("evidence", []),
                action=h.get("action", ""),
                parameters=h.get("parameters", {}),
            )
            for h in global_hyp_data
            if isinstance(h, dict)
        ]

        # Restore user evidence (last 200 per user)
        evidence_data = data.get("user_evidence", {})
        for user_id, ev_list in evidence_data.items():
            if isinstance(ev_list, list):
                self.user_evidence[user_id] = [e for e in ev_list[-200:] if isinstance(e, dict)]

        # Restore validation history
        self.validation_history = [
            h for h in data.get("validation_history", [])[-500:] if isinstance(h, dict)
        ]

        # Restore pattern cache
        self.detected_patterns = data.get("detected_patterns", {})

        self._interactions_since_validate = data.get("interactions_since_validate", 0)
        logger.info(
            "HypothesisGenerationEngine: loaded persisted state",
            users_with_hypotheses=len(self.user_hypotheses),
            global_hypotheses=len(self.global_hypotheses),
        )

    async def _save_state(self) -> None:
        """Persist current state to the database."""
        async with _SAVE_LOCK:
            payload = {
                "user_hypotheses": {
                    uid: [h.to_dict() for h in hyps]
                    for uid, hyps in self.user_hypotheses.items()
                },
                "global_hypotheses": [h.to_dict() for h in self.global_hypotheses],
                "user_evidence": {uid: ev[-200:] for uid, ev in self.user_evidence.items()},
                "validation_history": self.validation_history[-500:],
                "detected_patterns": self.detected_patterns,
                "interactions_since_validate": self._interactions_since_validate,
            }
            try:
                await asyncio.to_thread(self._sync_save_state, payload)
            except Exception as exc:
                logger.warning("HypothesisGenerationEngine: save failed", error=str(exc))

    async def record_interaction(
        self,
        user_id: str,
        interaction_type: str,
        destination: str,
        preferences: Dict[str, Any],
        rejection_reason: Optional[str] = None,
        accepted_features: Optional[List[str]] = None,
        research_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Record an interaction for hypothesis generation.
        
        Returns:
            List of new or updated hypotheses generated from this interaction
        """
        self._ensure_loaded()

        # Extract evidence from interaction
        evidence = {
            "user_id": user_id,
            "interaction_type": interaction_type,
            "destination": destination,
            "preferences": {
                "budget_level": preferences.get("budget_level"),
                "interests": preferences.get("interests", []),
                "traveling_with": preferences.get("traveling_with"),
            },
            "rejection_reason": rejection_reason,
            "accepted_features": accepted_features or [],
            "research_data": research_data or {},
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Store evidence
        self.user_evidence[user_id].append(evidence)
        
        # Keep only last 200 interactions per user
        if len(self.user_evidence[user_id]) > 200:
            self.user_evidence[user_id] = self.user_evidence[user_id][-200:]

        # Detect patterns and generate hypotheses
        new_hypotheses = await self._generate_hypotheses_for_interaction(user_id, evidence)

        # Auto-validate periodically
        self._interactions_since_validate += 1
        if self._interactions_since_validate >= self._VALIDATE_EVERY:
            try:
                await self._validate_all_hypotheses()
                self._interactions_since_validate = 0
            except Exception as exc:
                logger.warning(f"HypothesisGenerationEngine: validation failed: {exc}")

        await self._save_state()

        return [h.to_dict() for h in new_hypotheses]

    async def _generate_hypotheses_for_interaction(
        self,
        user_id: str,
        evidence: Dict[str, Any],
    ) -> List[Hypothesis]:
        """Generate hypotheses based on new evidence."""
        new_hypotheses = []

        # Get user's evidence history
        user_evidence = self.user_evidence.get(user_id, [])
        
        if len(user_evidence) < self.MIN_EVIDENCE_FOR_HYPOTHESIS:
            return new_hypotheses

        # Check each hypothesis template
        for template_name, template in HYPOTHESIS_TEMPLATES.items():
            # Check if pattern is triggered
            trigger_match = self._check_trigger(template["trigger"], user_evidence, evidence)
            
            if not trigger_match:
                continue

            # Calculate confidence based on evidence strength
            confidence = self._calculate_confidence(template_name, user_evidence, trigger_match)

            if confidence < template["confidence_threshold"]:
                continue

            # Generate hypothesis text with parameters
            hypothesis_text = template["hypothesis"]
            parameters = trigger_match.get("parameters", {})
            
            # Fill in template parameters
            for key, value in parameters.items():
                hypothesis_text = hypothesis_text.replace(f"{{{key}}}", str(value))

            # Check if we already have this hypothesis
            existing = self._find_existing_hypothesis(user_id, template_name, parameters)
            
            if existing:
                # Update existing hypothesis
                existing.confidence = min(1.0, existing.confidence + 0.1)
                existing.evidence.append(evidence)
                existing.evidence = existing.evidence[-10:]  # Keep last 10 pieces of evidence
            else:
                # Create new hypothesis
                hypothesis = Hypothesis(
                    hypothesis_id=f"{user_id}_{template_name}_{len(new_hypotheses)}",
                    template_name=template_name,
                    hypothesis_text=hypothesis_text,
                    confidence=confidence,
                    evidence=[evidence],
                    action=template["action"],
                    parameters=parameters,
                )
                self.user_hypotheses[user_id].append(hypothesis)
                new_hypotheses.append(hypothesis)

        return new_hypotheses

    def _check_trigger(
        self,
        trigger: Dict[str, Any],
        evidence_history: List[Dict[str, Any]],
        new_evidence: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Check if a trigger pattern is matched in the evidence."""
        parameters: Dict[str, Any] = {}

        # Check rejection reasons
        if "rejection_reasons" in trigger:
            trigger_reasons = trigger["rejection_reasons"]
            matching_reasons = [
                e for e in evidence_history + [new_evidence]
                if e.get("rejection_reason") and any(
                    kw in e["rejection_reason"].lower() for kw in trigger_reasons
                )
            ]
            if len(matching_reasons) >= self.MIN_EVIDENCE_FOR_HYPOTHESIS:
                # Find most common reason category
                reason_counts: Dict[str, int] = defaultdict(int)
                for e in matching_reasons:
                    reason = e.get("rejection_reason", "").lower()
                    for kw in trigger_reasons:
                        if kw in reason:
                            reason_counts[kw] += 1
                            break
                
                if reason_counts:
                    parameters["primary_reason"] = max(reason_counts, key=reason_counts.get)
                    return {"parameters": parameters}

        # Check acceptance features
        if "acceptance_features" in trigger:
            trigger_features = trigger["acceptance_features"]
            feature_counts: Dict[str, int] = defaultdict(int)
            
            for e in evidence_history + [new_evidence]:
                if e.get("interaction_type") == "acceptance":
                    for feature in e.get("accepted_features", []):
                        if feature.lower() in trigger_features:
                            feature_counts[feature.lower()] += 1
            
            # Find dominant feature
            if feature_counts:
                dominant_feature = max(feature_counts, key=feature_counts.get)
                count = feature_counts[dominant_feature]
                
                if count >= self.MIN_EVIDENCE_FOR_HYPOTHESIS:
                    parameters["interest"] = dominant_feature
                    return {"parameters": parameters}

        # Check destination traits
        if "destination_traits" in trigger:
            trigger_traits = trigger["destination_traits"]
            trait_counts: Dict[str, int] = defaultdict(int)
            
            for e in evidence_history + [new_evidence]:
                if e.get("interaction_type") == "acceptance":
                    research_data = e.get("research_data", {})
                    for trait in trigger_traits:
                        # Check if trait appears in destination features
                        dest_features = research_data.get("features", [])
                        if trait in dest_features:
                            trait_counts[trait] += 1
            
            if trait_counts:
                dominant_trait = max(trait_counts, key=trait_counts.get)
                if trait_counts[dominant_trait] >= self.MIN_EVIDENCE_FOR_HYPOTHESIS:
                    parameters["type"] = dominant_trait
                    return {"parameters": parameters}

        # Check regional patterns
        if "regions" in trigger:
            trigger_regions = trigger["regions"]
            region_accepts: Dict[str, int] = defaultdict(int)
            region_rejects: Dict[str, int] = defaultdict(int)
            
            for e in evidence_history + [new_evidence]:
                research_data = e.get("research_data", {})
                destination = e.get("destination", "")
                region = research_data.get("region", "")
                
                if not region:
                    # Infer region from destination (simplified)
                    region = self._infer_region(destination)
                
                if e.get("interaction_type") == "acceptance":
                    region_accepts[region] += 1
                else:
                    region_rejects[region] += 1
            
            # Find regions with strong bias
            for region in trigger_regions:
                accepts = region_accepts.get(region, 0)
                rejects = region_rejects.get(region, 0)
                
                if accepts >= 3 and rejects == 0:
                    parameters["region"] = region
                    parameters["bias"] = "prefers"
                    return {"parameters": parameters}
                elif rejects >= 3 and accepts == 0:
                    parameters["region"] = region
                    parameters["bias"] = "avoids"
                    return {"parameters": parameters}

        return None

    def _infer_region(self, destination: str) -> str:
        """Infer geographic region from destination name."""
        # Simplified region mapping
        europe = ["paris", "london", "rome", "barcelona", "amsterdam", "berlin", "vienna", "prague"]
        asia = ["tokyo", "bangkok", "singapore", "bali", "kyoto", "seoul", "hong kong"]
        americas = ["new york", "miami", "cancun", "rio", "buenos aires", "toronto"]
        oceania = ["sydney", "melbourne", "queenstown", "bali"]
        africa = ["cairo", "cape town", "nairobi", "marrakech"]
        
        dest_lower = destination.lower()
        
        for eur_dest in europe:
            if eur_dest in dest_lower:
                return "Europe"
        for asia_dest in asia:
            if asia_dest in dest_lower:
                return "Asia"
        for amer_dest in americas:
            if amer_dest in dest_lower:
                return "Americas"
        for ocean_dest in oceania:
            if ocean_dest in dest_lower:
                return "Oceania"
        for africa_dest in africa:
            if africa_dest in dest_lower:
                return "Africa"
        
        return "Unknown"

    def _calculate_confidence(
        self,
        template_name: str,
        evidence_history: List[Dict[str, Any]],
        trigger_match: Dict[str, Any],
    ) -> float:
        """Calculate confidence score for a hypothesis."""
        # Base confidence from evidence count
        relevant_evidence = [
            e for e in evidence_history
            if self._is_evidence_relevant(template_name, e)
        ]
        
        evidence_count = len(relevant_evidence)
        base_confidence = min(0.5, evidence_count * 0.1)  # 0.1 per piece, max 0.5

        # Boost for consistency (all evidence points same direction)
        if evidence_count >= 3:
            consistency = self._calculate_evidence_consistency(template_name, relevant_evidence)
            base_confidence += consistency * 0.3

        # Boost for recency (recent evidence weighted higher)
        recency_boost = self._calculate_recency_boost(relevant_evidence)
        base_confidence += recency_boost * 0.2

        return min(1.0, base_confidence)

    def _is_evidence_relevant(
        self,
        template_name: str,
        evidence: Dict[str, Any],
    ) -> bool:
        """Check if evidence is relevant to a hypothesis template."""
        template = HYPOTHESIS_TEMPLATES.get(template_name, {})
        trigger = template.get("trigger", {})

        if "rejection_reasons" in trigger and evidence.get("rejection_reason"):
            return True
        if "acceptance_features" in trigger and evidence.get("interaction_type") == "acceptance":
            return True
        if "destination_traits" in trigger and evidence.get("research_data"):
            return True
        
        return False

    def _calculate_evidence_consistency(
        self,
        template_name: str,
        evidence_list: List[Dict[str, Any]],
    ) -> float:
        """Calculate how consistent the evidence is (0-1)."""
        if len(evidence_list) < 2:
            return 0.0

        # For rejection-based hypotheses, check if reasons are similar
        if template_name in ["weather_preference", "budget_constraint", "visa_sensitivity"]:
            reasons = [e.get("rejection_reason", "").lower() for e in evidence_list]
            if not reasons:
                return 0.0
            
            # Check if reasons share common keywords
            template = HYPOTHESIS_TEMPLATES.get(template_name, {})
            trigger_reasons = template.get("trigger", {}).get("rejection_reasons", [])
            
            matching = sum(
                1 for r in reasons
                if any(kw in r for kw in trigger_reasons)
            )
            return matching / len(reasons)

        # For acceptance-based hypotheses, check feature consistency
        if template_name == "interest_focus":
            all_features = []
            for e in evidence_list:
                all_features.extend(e.get("accepted_features", []))
            
            if not all_features:
                return 0.0
            
            # Find most common feature
            feature_counts: Dict[str, int] = defaultdict(int)
            for f in all_features:
                feature_counts[f] += 1
            
            top_feature, top_count = max(feature_counts.items(), key=lambda x: x[1])
            return top_count / len(evidence_list)

        return 0.5  # Default moderate consistency

    def _calculate_recency_boost(self, evidence_list: List[Dict[str, Any]]) -> float:
        """Calculate boost for recent evidence."""
        if not evidence_list:
            return 0.0

        now = datetime.now()
        recent_count = 0
        
        for e in evidence_list:
            timestamp_str = e.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if now - timestamp < timedelta(days=7):
                        recent_count += 1
                except ValueError:
                    pass

        return recent_count / len(evidence_list)

    def _find_existing_hypothesis(
        self,
        user_id: str,
        template_name: str,
        parameters: Dict[str, Any],
    ) -> Optional[Hypothesis]:
        """Find an existing hypothesis matching template and parameters."""
        for hyp in self.user_hypotheses.get(user_id, []):
            if hyp.template_name != template_name:
                continue
            
            # Check if parameters match
            match = True
            for key, value in parameters.items():
                if hyp.parameters.get(key) != value:
                    match = False
                    break
            
            if match:
                return hyp
        
        return None

    async def _validate_all_hypotheses(self) -> Dict[str, Any]:
        """Validate all active hypotheses against historical data."""
        validation_results = {
            "validated": 0,
            "refuted": 0,
            "inconclusive": 0,
        }

        for user_id, hypotheses in list(self.user_hypotheses.items()):
            for hyp in hypotheses:
                result = await self._validate_hypothesis(user_id, hyp)
                hyp.validation_status = result["status"]
                hyp.last_validated = datetime.now()
                
                validation_results[result["status"].replace("validated", "validated").replace("refuted", "refuted")] += 1

        self.validation_history.append({
            "timestamp": datetime.now().isoformat(),
            "results": validation_results,
        })

        logger.info(
            "HypothesisGenerationEngine: validation complete",
            **validation_results,
        )

        return validation_results

    async def _validate_hypothesis(
        self,
        user_id: str,
        hypothesis: Hypothesis,
    ) -> Dict[str, Any]:
        """Validate a single hypothesis against user's evidence."""
        user_evidence = self.user_evidence.get(user_id, [])
        
        if len(user_evidence) < self.MIN_EVIDENCE_FOR_HYPOTHESIS * 2:
            return {"status": "inconclusive", "reason": "insufficient_evidence"}

        # Test hypothesis against evidence
        template = HYPOTHESIS_TEMPLATES.get(hypothesis.template_name, {})
        trigger = template.get("trigger", {})

        # Count supporting vs contradicting evidence
        supporting = 0
        contradicting = 0

        for e in user_evidence:
            if self._evidence_supports_hypothesis(e, hypothesis, trigger):
                supporting += 1
            elif self._evidence_contradicts_hypothesis(e, hypothesis, trigger):
                contradicting += 1

        total = supporting + contradicting
        if total < self.MIN_EVIDENCE_FOR_HYPOTHESIS:
            return {"status": "inconclusive", "reason": "insufficient_test_data"}

        support_ratio = supporting / total

        if support_ratio >= 0.7:
            return {"status": "validated", "support_ratio": support_ratio}
        elif support_ratio <= 0.3:
            return {"status": "refuted", "support_ratio": support_ratio}
        else:
            return {"status": "inconclusive", "support_ratio": support_ratio}

    def _evidence_supports_hypothesis(
        self,
        evidence: Dict[str, Any],
        hypothesis: Hypothesis,
        trigger: Dict[str, Any],
    ) -> bool:
        """Check if evidence supports a hypothesis."""
        # Rejection-based hypotheses
        if "rejection_reasons" in trigger:
            if evidence.get("interaction_type") == "rejection":
                reason = evidence.get("rejection_reason", "").lower()
                return any(kw in reason for kw in trigger["rejection_reasons"])

        # Acceptance-based hypotheses
        if "acceptance_features" in trigger:
            if evidence.get("interaction_type") == "acceptance":
                features = evidence.get("accepted_features", [])
                return any(f.lower() in trigger["acceptance_features"] for f in features)

        return False

    def _evidence_contradicts_hypothesis(
        self,
        evidence: Dict[str, Any],
        hypothesis: Hypothesis,
        trigger: Dict[str, Any],
    ) -> bool:
        """Check if evidence contradicts a hypothesis."""
        # For rejection-based: acceptance of thing user supposedly dislikes
        if "rejection_reasons" in trigger:
            if evidence.get("interaction_type") == "acceptance":
                # User accepted something they should reject based on hypothesis
                return True

        # For acceptance-based: rejection of thing user supposedly likes
        if "acceptance_features" in trigger:
            if evidence.get("interaction_type") == "rejection":
                return True

        return False

    def get_active_hypotheses(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active hypotheses for a user."""
        self._ensure_loaded()

        hypotheses = self.user_hypotheses.get(user_id, [])
        
        # Filter to validated or high-confidence pending
        active = [
            h for h in hypotheses
            if h.validation_status == "validated" or (
                h.validation_status == "pending" and h.confidence >= 0.7
            )
        ]

        # Sort by confidence
        active.sort(key=lambda h: h.confidence, reverse=True)

        return [h.to_dict() for h in active]

    def get_recommendations_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get actionable recommendations based on hypotheses.
        
        Returns a dict of recommendation strategies to apply.
        """
        self._ensure_loaded()

        hypotheses = self.get_active_hypotheses(user_id)
        
        if not hypotheses:
            return {
                "strategies": [],
                "filters": {},
                "boosts": {},
            }

        strategies = []
        filters = {}
        boosts = {}

        for hyp in hypotheses:
            action = hyp.get("action", "")
            parameters = hyp.get("parameters", {})

            # Parse action into strategy/filter/boost
            if "filter" in action.lower():
                # Extract filter criteria from action text
                if "weather" in hyp.get("template_name", ""):
                    filters["climate_match"] = True
                elif "budget" in hyp.get("template_name", ""):
                    filters["max_price"] = "strict"
                elif "visa" in hyp.get("template_name", ""):
                    filters["visa_free_only"] = True
                elif "flight" in hyp.get("template_name", ""):
                    filters["max_flight_hours"] = 10

            elif "prioritize" in action.lower() or "boost" in action.lower():
                # Extract boost criteria
                if "culture" in hyp.get("template_name", "").lower() or parameters.get("interest") == "culture":
                    boosts["culture_score"] = 1.3
                elif "adventure" in hyp.get("template_name", "").lower() or parameters.get("interest") == "adventure":
                    boosts["adventure_score"] = 1.3
                elif "beach" in hyp.get("template_name", "").lower() or parameters.get("interest") == "beach":
                    boosts["beach_score"] = 1.3

            strategies.append({
                "hypothesis_id": hyp["id"],
                "hypothesis": hyp["hypothesis"],
                "confidence": hyp["confidence"],
                "action": action,
            })

        return {
            "user_id": user_id,
            "strategies": strategies,
            "filters": filters,
            "boosts": boosts,
            "hypothesis_count": len(hypotheses),
        }

    async def get_learning_stats(self) -> Dict[str, Any]:
        """Get overall learning statistics."""
        self._ensure_loaded()

        total_hypotheses = sum(len(hyps) for hyps in self.user_hypotheses.values())
        validated = sum(
            1 for hyps in self.user_hypotheses.values()
            for h in hyps if h.validation_status == "validated"
        )

        return {
            "users_with_hypotheses": len(self.user_hypotheses),
            "total_hypotheses": total_hypotheses,
            "validated_hypotheses": validated,
            "global_hypotheses": len(self.global_hypotheses),
            "total_evidence_stored": sum(len(ev) for ev in self.user_evidence.values()),
            "validation_history_entries": len(self.validation_history),
            "interactions_since_last_validate": self._interactions_since_validate,
        }


_hypothesis_engine_instance: Optional[HypothesisGenerationEngine] = None


def get_hypothesis_engine() -> HypothesisGenerationEngine:
    """Get or create the hypothesis generation engine singleton."""
    global _hypothesis_engine_instance
    if _hypothesis_engine_instance is None:
        _hypothesis_engine_instance = HypothesisGenerationEngine()
    return _hypothesis_engine_instance
