"""
Feedback API Routes
Collect user feedback to improve recommendations
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.api.auth_routes import get_current_user
from app.utils.learning_agent import learn_from_interaction, get_learning_stats
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """User feedback on a recommendation"""
    job_id: str
    destination: str
    feedback_type: str  # 'like', 'dislike', 'saved', 'shared', 'bookmarked'
    feedback_data: Optional[Dict[str, Any]] = None


class RecommendationInteractionRequest(BaseModel):
    """User interaction with recommendations"""
    job_id: str
    interaction_type: str  # 'acceptance', 'rejection'
    destination: str
    recommendations: List[Dict[str, Any]]
    selected_index: Optional[int] = None  # For acceptance
    rejection_reason: Optional[str] = None  # For rejection


@router.post("/recommendation")
async def submit_recommendation_feedback(
    request: FeedbackRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback on a destination recommendation.
    
    Examples:
    - User clicks "like" on a destination
    - User saves a destination to favorites
    - User shares a destination
    """
    user_id = str(current_user.id) if current_user else f"anonymous_{request.job_id}"
    
    try:
        await learn_from_interaction(
            user_id=user_id,
            interaction_type=request.feedback_type,
            destination=request.destination,
            feedback_data=request.feedback_data
        )
        
        return {
            "status": "success",
            "message": f"Thank you for your {request.feedback_type} feedback!",
            "learning_impact": "Your feedback will improve future recommendations"
        }
    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process feedback")


@router.post("/interaction")
async def submit_recommendation_interaction(
    request: RecommendationInteractionRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit interaction with recommendations.
    
    Examples:
    - User selects a destination from recommendations (acceptance)
    - User rejects all recommendations and searches again (rejection)
    """
    user_id = str(current_user.id) if current_user else f"anonymous_{request.job_id}"
    
    try:
        await learn_from_interaction(
            user_id=user_id,
            interaction_type=request.interaction_type,
            destination=request.destination,
            recommendations=request.recommendations,
            selected_index=request.selected_index,
            rejection_reason=request.rejection_reason
        )
        
        return {
            "status": "success",
            "message": "Interaction recorded",
            "learning_impact": "This will help us personalize your future recommendations"
        }
    except Exception as e:
        logger.error(f"Error processing interaction: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process interaction")


@router.get("/stats")
async def get_feedback_stats(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get learning system statistics.
    Shows how the AI is improving based on user feedback.
    """
    try:
        stats = get_learning_stats()
        
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/user/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get user's learned preference profile.
    Shows what the AI has learned about this user's preferences.
    """
    from app.utils.learning_agent import get_learner
    
    try:
        learner = get_learner()
        profile = learner.get_user_profile(user_id)
        
        if not profile:
            return {
                "status": "success",
                "profile": None,
                "message": "Not enough interactions yet to build a profile"
            }
        
        return {
            "status": "success",
            "profile": {
                "interactions_count": len(profile.get('interactions', [])),
                "destination_history_count": len(profile.get('destination_history', [])),
                "preferences": profile.get('preferences', {}),
                "learned_at": profile.get('preferences', {}).get('learned_at'),
                "created_at": profile.get('created_at')
            }
        }
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")


@router.post("/cache/clear")
async def clear_cache(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Clear cache (admin only).
    Useful for testing or when data needs to be refreshed.
    """
    # In production, add admin check here
    try:
        from app.utils.cache import get_cache
        
        cache = get_cache()
        stats_before = await cache.get_stats()
        
        # Clear all cache (implementation depends on backend)
        if hasattr(cache.backend, '_cache'):
            cache.backend._cache.clear()
            cache.backend._expiry.clear()
        
        return {
            "status": "success",
            "message": "Cache cleared",
            "stats_before": stats_before
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.get("/cache/stats")
async def get_cache_stats(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get cache statistics.
    Shows cache performance and hit rates.
    """
    try:
        from app.utils.cache import get_cache
        
        cache = get_cache()
        stats = await cache.get_stats()
        
        return {
            "status": "success",
            "cache_stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats")
