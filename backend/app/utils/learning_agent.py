"""
Learning AI Agent for Travel Recommendations
Improves recommendations based on user interactions and feedback
"""
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from app.utils.logging_config import get_logger
from app.database.connection import SessionLocal

logger = get_logger(__name__)


class UserPreferenceLearner:
    """
    Learns user preferences from interactions and feedback.
    Updates recommendation scoring based on what users actually like.
    """
    
    def __init__(self):
        self.user_profiles: Dict[str, Dict] = {}  # In-memory user profiles
        self.global_patterns: Dict[str, Any] = {
            'destination_scores': defaultdict(lambda: {'acceptances': 0, 'rejections': 0, 'avg_score': 0}),
            'feature_importance': {
                'price': 0.3,
                'weather': 0.15,
                'attractions': 0.2,
                'visa_ease': 0.1,
                'flight_time': 0.15,
                'safety': 0.1
            },
            'seasonal_preferences': defaultdict(list),
        }
    
    async def learn_from_acceptance(
        self,
        user_id: str,
        destination: str,
        recommendations: List[Dict],
        selected_index: int
    ):
        """
        Learn from user accepting a recommendation.
        
        Args:
            user_id: User identifier
            destination: Selected destination
            recommendations: List of recommendations shown
            selected_index: Index of selected recommendation
        """
        logger.info(f"Learning from acceptance: {user_id} → {destination}")
        
        # Get selected recommendation
        if selected_index >= len(recommendations):
            return
        
        selected = recommendations[selected_index]
        
        # Update global destination score
        self.global_patterns['destination_scores'][destination]['acceptances'] += 1
        
        # Learn what features user liked
        await self._update_user_profile(user_id, {
            'preferred_destinations': destination,
            'accepted_price_range': selected.get('price_range'),
            'accepted_features': selected.get('features', []),
            'interaction_type': 'acceptance',
            'timestamp': datetime.now().isoformat()
        })
        
        # Analyze what made this recommendation successful
        await self._analyze_successful_features(destination, selected)
    
    async def learn_from_rejection(
        self,
        user_id: str,
        destination: str,
        recommendations: List[Dict],
        rejection_reason: Optional[str] = None
    ):
        """
        Learn from user rejecting recommendations.
        
        Args:
            user_id: User identifier
            destination: Destination that was rejected
            recommendations: List of recommendations shown
            rejection_reason: Optional reason for rejection
        """
        logger.info(f"Learning from rejection: {user_id} → {destination}, reason: {rejection_reason}")
        
        # Update global destination score
        self.global_patterns['destination_scores'][destination]['rejections'] += 1
        
        # Learn what user didn't like
        await self._update_user_profile(user_id, {
            'rejected_destinations': destination,
            'rejection_reason': rejection_reason,
            'interaction_type': 'rejection',
            'timestamp': datetime.now().isoformat()
        })
        
        # Analyze why recommendation failed
        await self._analyze_failed_features(destination, rejection_reason)
    
    async def learn_from_feedback(
        self,
        user_id: str,
        destination: str,
        feedback_type: str,  # 'like', 'dislike', 'saved', 'shared'
        feedback_data: Optional[Dict] = None
    ):
        """
        Learn from explicit user feedback.
        
        Args:
            user_id: User identifier
            destination: Destination being reviewed
            feedback_type: Type of feedback
            feedback_data: Additional feedback data
        """
        logger.info(f"Learning from feedback: {user_id} → {destination} ({feedback_type})")
        
        feedback_weights = {
            'like': 0.8,
            'dislike': -0.8,
            'saved': 0.6,
            'shared': 0.7,
            'bookmarked': 0.6
        }
        
        weight = feedback_weights.get(feedback_type, 0)
        
        # Update user profile
        await self._update_user_profile(user_id, {
            f'{feedback_type}_destinations': destination,
            'feedback_weight': weight,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update global patterns
        if weight > 0:
            self.global_patterns['destination_scores'][destination]['acceptances'] += 1
        else:
            self.global_patterns['destination_scores'][destination]['rejections'] += 1
    
    async def _update_user_profile(self, user_id: str, data: Dict):
        """Update or create user profile with new data."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'created_at': datetime.now().isoformat(),
                'interactions': [],
                'preferences': {},
                'destination_history': [],
            }
        
        profile = self.user_profiles[user_id]
        profile['interactions'].append(data)
        
        # Keep only last 100 interactions
        if len(profile['interactions']) > 100:
            profile['interactions'] = profile['interactions'][-100:]
        
        # Update destination history
        if 'destination' in data:
            profile['destination_history'].append({
                'destination': data['destination'],
                'type': data.get('interaction_type', 'unknown'),
                'timestamp': data.get('timestamp', datetime.now().isoformat())
            })
        
        # Extract preference patterns
        await self._extract_preference_patterns(user_id)
    
    async def _extract_preference_patterns(self, user_id: str):
        """Extract preference patterns from user history."""
        profile = self.user_profiles.get(user_id)
        if not profile:
            return
        
        # Analyze destination history
        destinations = profile.get('destination_history', [])
        if len(destinations) < 3:
            return  # Not enough data
        
        # Count destination types
        destination_types = defaultdict(int)
        price_ranges = defaultdict(int)
        seasons = defaultdict(int)
        
        for dest in destinations:
            # This would need destination metadata lookup
            # For now, just count frequencies
            destination_types[dest.get('destination', '')] += 1
        
        # Update user preferences
        profile['preferences'] = {
            'top_destination_types': dict(sorted(destination_types.items(), key=lambda x: x[1], reverse=True)[:5]),
            'learned_at': datetime.now().isoformat()
        }
    
    async def _analyze_successful_features(self, destination: str, recommendation: Dict):
        """Analyze what features made a recommendation successful."""
        # Extract features from accepted recommendation
        features = recommendation.get('features', [])
        
        for feature in features:
            # Increase importance of features that lead to acceptance
            if feature in self.global_patterns['feature_importance']:
                self.global_patterns['feature_importance'][feature] = min(
                    1.0,
                    self.global_patterns['feature_importance'][feature] * 1.05
                )
    
    async def _analyze_failed_features(self, destination: str, reason: Optional[str]):
        """Analyze why a recommendation failed."""
        if not reason:
            return
        
        # Map rejection reasons to features
        reason_to_feature = {
            'too expensive': 'price',
            'too far': 'flight_time',
            'visa issues': 'visa_ease',
            'not safe': 'safety',
            'boring': 'attractions',
            'wrong weather': 'weather'
        }
        
        for reason_key, feature in reason_to_feature.items():
            if reason_key in reason.lower():
                # Decrease importance of features that led to rejection
                if feature in self.global_patterns['feature_importance']:
                    self.global_patterns['feature_importance'][feature] = max(
                        0.05,
                        self.global_patterns['feature_importance'][feature] * 0.95
                    )
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile for personalized recommendations."""
        return self.user_profiles.get(user_id)
    
    def get_personalized_weights(self, user_id: str) -> Dict[str, float]:
        """Get personalized feature weights for a user."""
        profile = self.get_user_profile(user_id)
        
        if not profile or not profile.get('preferences'):
            return self.global_patterns['feature_importance']
        
        # Start with global weights
        weights = self.global_patterns['feature_importance'].copy()
        
        # Adjust based on user history
        # (This would be more sophisticated with more data)
        
        return weights
    
    def get_destination_success_rate(self, destination: str) -> float:
        """Get acceptance rate for a destination."""
        stats = self.global_patterns['destination_scores'].get(destination, {})
        acceptances = stats.get('acceptances', 0)
        rejections = stats.get('rejections', 0)
        
        total = acceptances + rejections
        if total == 0:
            return 0.5  # Neutral for new destinations
        
        return acceptances / total
    
    def get_learning_stats(self) -> Dict:
        """Get learning system statistics."""
        return {
            'user_profiles_count': len(self.user_profiles),
            'destinations_tracked': len(self.global_patterns['destination_scores']),
            'feature_importance': self.global_patterns['feature_importance'],
            'top_destinations': sorted(
                [
                    {
                        'destination': dest,
                        'success_rate': self.get_destination_success_rate(dest)
                    }
                    for dest in self.global_patterns['destination_scores'].keys()
                ],
                key=lambda x: x['success_rate'],
                reverse=True
            )[:10]
        }


class RecommendationImprover:
    """
    Improves recommendations based on learning data.
    Re-scores and re-ranks recommendations based on learned preferences.
    """
    
    def __init__(self, learner: UserPreferenceLearner):
        self.learner = learner
    
    def improve_recommendations(
        self,
        recommendations: List[Dict],
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Improve recommendations based on learned preferences.
        
        Args:
            recommendations: Original recommendations
            user_id: User identifier for personalization
        
        Returns:
            Improved and re-ranked recommendations
        """
        if not recommendations:
            return []
        
        # Get personalized weights
        weights = self.learner.get_personalized_weights(user_id) if user_id else self.learner.global_patterns['feature_importance']
        
        # Re-score each recommendation
        improved = []
        for rec in recommendations:
            new_score = self._calculate_improved_score(rec, weights)
            
            # Create improved recommendation
            improved_rec = rec.copy()
            improved_rec['original_score'] = rec.get('score', 0)
            improved_rec['improved_score'] = new_score
            improved_rec['score_improvement'] = new_score - rec.get('score', 0)
            improved_rec['personalized'] = user_id is not None
            improved_rec['learning_confidence'] = self._calculate_confidence(rec, user_id)
            
            improved.append(improved_rec)
        
        # Re-rank by improved score
        improved.sort(key=lambda x: x['improved_score'], reverse=True)
        
        return improved
    
    def _calculate_improved_score(self, recommendation: Dict, weights: Dict[str, float]) -> float:
        """Calculate improved score based on learned weights."""
        base_score = recommendation.get('score', 0)
        
        # Get destination success rate
        destination = recommendation.get('destination', '')
        success_rate = self.learner.get_destination_success_rate(destination)
        
        # Calculate feature match score
        features = recommendation.get('features', [])
        feature_score = sum(weights.get(f, 0.5) for f in features) / max(len(features), 1)
        
        # Combine scores
        improved_score = (
            base_score * 0.5 +  # Keep 50% of original score
            success_rate * 0.3 +  # Add 30% from destination success rate
            feature_score * 0.2  # Add 20% from feature match
        )
        
        return round(improved_score, 2)
    
    def _calculate_confidence(self, recommendation: Dict, user_id: Optional[str]) -> float:
        """Calculate confidence in the improved recommendation."""
        confidence = 0.5  # Base confidence
        
        # More data = more confidence
        if user_id:
            profile = self.learner.get_user_profile(user_id)
            if profile and len(profile.get('interactions', [])) > 10:
                confidence += 0.2
            elif profile and len(profile.get('interactions', [])) > 5:
                confidence += 0.1
        
        # Destination with history = more confidence
        destination = recommendation.get('destination', '')
        stats = self.learner.global_patterns['destination_scores'].get(destination, {})
        total_interactions = stats.get('acceptances', 0) + stats.get('rejections', 0)
        
        if total_interactions > 20:
            confidence += 0.2
        elif total_interactions > 5:
            confidence += 0.1
        
        return min(0.95, confidence)


# Global instances
_learner: Optional[UserPreferenceLearner] = None
_improver: Optional[RecommendationImprover] = None


def get_learner() -> UserPreferenceLearner:
    """Get or create learner instance."""
    global _learner
    if not _learner:
        _learner = UserPreferenceLearner()
    return _learner


def get_improver() -> RecommendationImprover:
    """Get or create improver instance."""
    global _improver
    if not _improver:
        _improver = RecommendationImprover(get_learner())
    return _improver


# Convenience functions for use in auto_research_agent

async def learn_from_interaction(
    user_id: str,
    interaction_type: str,
    destination: str,
    recommendations: Optional[List[Dict]] = None,
    **kwargs
):
    """
    Learn from user interaction.
    
    Usage:
        await learn_from_interaction(
            user_id="user123",
            interaction_type="acceptance",
            destination="Paris",
            recommendations=[...],
            selected_index=0
        )
    """
    learner = get_learner()
    
    if interaction_type == 'acceptance' and recommendations:
        await learner.learn_from_acceptance(
            user_id, destination, recommendations,
            kwargs.get('selected_index', 0)
        )
    elif interaction_type == 'rejection':
        await learner.learn_from_rejection(
            user_id, destination, recommendations or [],
            kwargs.get('rejection_reason')
        )
    elif interaction_type in ['like', 'dislike', 'saved', 'shared', 'bookmarked']:
        await learner.learn_from_feedback(
            user_id, destination, interaction_type, kwargs.get('feedback_data')
        )


def improve_recommendations(
    recommendations: List[Dict],
    user_id: Optional[str] = None
) -> List[Dict]:
    """
    Improve recommendations based on learning.
    
    Usage:
        improved = improve_recommendations(recommendations, user_id="user123")
    """
    improver = get_improver()
    return improver.improve_recommendations(recommendations, user_id)


def get_learning_stats() -> Dict:
    """Get learning system statistics."""
    return get_learner().get_learning_stats()
