"""
Auto Research API Routes
Endpoints for autonomous travel research triggered by user preferences
"""

import json
import asyncio
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from app.utils.logging_config import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = get_logger(__name__)

from app.database.connection import get_db, SessionLocal
from app.database.models import ResearchJob
from app.services.auto_research_agent import AutoResearchAgent, run_auto_research, ResearchStep
from app.utils.datetime_utils import utcnow_naive
from app.api.websocket_routes import (
    emit_research_started,
    emit_research_progress,
    emit_research_completed,
    emit_research_error,
)

router = APIRouter(prefix="/api/v1/auto-research", tags=["auto-research"])
_auto_research_limiter = Limiter(key_func=get_remote_address)


# ============ Request/Response Models ============

class TravelPreferences(BaseModel):
    """User travel preferences from questionnaire"""
    origin: str = ""
    destinations: List[str] = []
    travel_start: Optional[str] = None  # YYYY-MM-DD
    travel_end: Optional[str] = None  # YYYY-MM-DD
    budget_level: str = "moderate"  # low, moderate, high, luxury
    budget_amount: Optional[float] = None
    interests: List[str] = []
    traveling_with: str = "solo"  # solo, couple, family, group
    passport_country: str = "US"
    visa_preference: str = "visa_free"  # visa_free, visa_on_arrival, evisa_ok
    weather_preference: str = "warm"  # hot, warm, mild, cold, snow
    max_flight_duration: Optional[int] = None  # hours
    accessibility_needs: List[str] = []
    dietary_restrictions: List[str] = []
    notes: str = ""
    # New fields
    has_kids: bool = False
    kids_count: int = 0
    kids_ages: List[str] = []
    trip_type: str = "leisure"  # leisure, adventure, cultural, romantic, family, business, food, wellness
    pace_preference: str = "moderate"  # relaxed, moderate, busy
    # Research depth
    research_depth: str = "standard"  # quick, standard, deep


class ResearchJobResponse(BaseModel):
    """Research job status response"""
    job_id: str
    status: str
    progress_percentage: int
    current_step: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    destinations_count: int = 0
    results_available: bool = False


class ResearchResultsResponse(BaseModel):
    """Full research results"""
    job_id: str
    status: str
    preferences: dict
    research_timestamp: str
    destinations: List[dict]
    comparison: Optional[dict] = None
    recommendations: List[dict]


# ============ Background Task ============

async def _run_research_job(
    job_id: str,
    preferences: dict,
    depth: str = "standard"
):
    """Background task to run research, persist progress to DB, and push
    real-time updates to any connected WebSocket clients."""
    db = SessionLocal()
    
    # Map string depth to ResearchDepth enum
    from app.services.auto_research_agent import ResearchDepth
    depth_enum = ResearchDepth.STANDARD
    if depth == "quick":
        depth_enum = ResearchDepth.QUICK
    elif depth == "deep":
        depth_enum = ResearchDepth.DEEP

    async def progress_callback(progress_data):
        """Persist progress to DB and broadcast to WebSocket subscribers."""
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if job:
            job.current_step = progress_data["step"]
            job.completed_steps = progress_data["completed_steps"]
            # Update total steps based on depth
            job.total_steps = progress_data.get("total_steps", 10)
            db.commit()  # Always commit so polling clients see current state

        # Push progress to any connected WebSocket clients (fire-and-forget)
        try:
            await emit_research_progress(
                job_id=job_id,
                step=progress_data.get("step", ""),
                percentage=progress_data.get("percentage", 0),
                message=progress_data.get("message", ""),
            )
        except Exception as ws_err:
            logger.debug("WS broadcast skipped (no subscribers)", error=str(ws_err))

    try:
        # Mark job as in-progress
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if job:
            job.status = "in_progress"
            job.started_at = utcnow_naive()
            db.commit()

        # Notify connected WebSocket clients that research has started
        try:
            await emit_research_started(job_id=job_id, preferences=preferences)
        except Exception:
            pass

        # Run the research with depth parameter
        results = await run_auto_research(
            preferences=preferences,
            job_id=job_id,
            progress_callback=progress_callback,
            depth=depth_enum,
        )

        # Persist completed results
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if job:
            job.status = "completed"
            job.completed_at = utcnow_naive()
            job.results = json.dumps(results)
            # Update total steps based on depth
            if depth == "quick":
                job.total_steps = 9
            elif depth == "deep":
                job.total_steps = 18
            else:
                job.total_steps = 14
            job.completed_steps = job.total_steps
            db.commit()

        # Notify WebSocket clients that research is done
        recommendations = results.get("recommendations", [])[:3]
        try:
            await emit_research_completed(
                job_id=job_id,
                results_summary={
                    "destinations_count": len(results.get("destinations", [])),
                    "top_recommendations": [r.get("destination", "") for r in recommendations],
                },
            )
        except Exception:
            pass

    except Exception as e:
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.completed_at = utcnow_naive()
            job.errors = json.dumps({"error": str(e), "timestamp": utcnow_naive().isoformat()})
            db.commit()
        logger.error("Research job failed", job_id=job_id, error=str(e))
        try:
            await emit_research_error(job_id=job_id, error=str(e))
        except Exception:
            pass
    finally:
        db.close()


# ============ API Endpoints ============

@router.post("/start", response_model=ResearchJobResponse)
@_auto_research_limiter.limit("60/minute")
async def start_auto_research(
    request: Request,
    preferences: TravelPreferences,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Start automatic research based on user preferences.
    
    This endpoint immediately returns a job ID and starts the research
    in the background. Use the /status/{job_id} endpoint to check progress.
    
    Example preferences:
    {
        "origin": "New York",
        "destinations": [],  # Empty to get suggestions
        "travel_start": "2024-06-15",
        "travel_end": "2024-06-22",
        "budget_level": "moderate",
        "interests": ["beach", "food", "culture"],
        "traveling_with": "couple",
        "passport_country": "US"
    }
    """
    try:
        preferences_payload = preferences.model_dump()
        
        # Determine total steps based on depth
        depth = preferences.research_depth or "standard"
        if depth == "quick":
            total_steps = 9
        elif depth == "deep":
            total_steps = 18
        else:
            total_steps = 14
        
        # Create research job record
        job = ResearchJob(
            user_id=user_id,
            job_type="destination_research",
            status="pending",
            query_params=json.dumps(preferences_payload),
            total_steps=total_steps,
            completed_steps=0
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Start background research with depth parameter
        background_tasks.add_task(
            _run_research_job,
            job.id,
            preferences_payload,
            depth
        )

        return ResearchJobResponse(
            job_id=job.id,
            status="pending",
            progress_percentage=0,
            current_step="initializing",
            created_at=job.created_at.isoformat(),
            destinations_count=len(preferences.destinations) if preferences.destinations else 0,
            results_available=False
        )
        
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to start research")


@router.get("/status/{job_id}", response_model=ResearchJobResponse)
async def get_research_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the current status of a research job.
    
    Poll this endpoint to track progress. When status is "completed",
    use /results/{job_id} to get the full results.
    """
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    progress_percentage = 0
    if job.total_steps > 0:
        progress_percentage = min(100, int((job.completed_steps / job.total_steps) * 100))
    
    return ResearchJobResponse(
        job_id=job.id,
        status=job.status,
        progress_percentage=progress_percentage,
        current_step=job.current_step or "pending",
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        destinations_count=0,  # Could parse from query_params if needed
        results_available=job.status == "completed" and job.results is not None
    )


@router.get("/results/{job_id}", response_model=ResearchResultsResponse)
async def get_research_results(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the full results of a completed research job.
    
    This returns all the gathered information including:
    - Destination details with weather, visa, attractions, events
    - Comparison table between destinations
    - Personalized recommendations with rankings
    """
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    if job.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Research not completed yet. Current status: {job.status}"
        )
    
    if not job.results:
        raise HTTPException(status_code=500, detail="Research completed but results not available")
    
    try:
        results = json.loads(job.results)
        return ResearchResultsResponse(
            job_id=job.id,
            status=job.status,
            preferences=json.loads(job.query_params),
            research_timestamp=results.get("research_timestamp", ""),
            destinations=results.get("destinations", []),
            comparison=results.get("comparison"),
            recommendations=results.get("recommendations", [])
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse research results")


@router.get("/jobs", response_model=List[ResearchJobResponse])
async def list_research_jobs(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    List research jobs for a user.
    
    Query parameters:
    - user_id: Filter by user (optional)
    - status: Filter by status - pending, in_progress, completed, failed (optional)
    - limit: Maximum number of results (default 10)
    """
    query = db.query(ResearchJob)
    
    if user_id:
        query = query.filter(ResearchJob.user_id == user_id)
    if status:
        query = query.filter(ResearchJob.status == status)
    
    jobs = query.order_by(ResearchJob.created_at.desc()).limit(limit).all()
    
    results = []
    for job in jobs:
        progress_percentage = 0
        if job.total_steps > 0:
            progress_percentage = min(100, int((job.completed_steps / job.total_steps) * 100))
        
        results.append(ResearchJobResponse(
            job_id=job.id,
            status=job.status,
            progress_percentage=progress_percentage,
            current_step=job.current_step or "pending",
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            results_available=job.status == "completed" and job.results is not None
        ))
    
    return results


@router.delete("/jobs/{job_id}")
async def delete_research_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Delete a research job and its results"""
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    
    db.delete(job)
    db.commit()
    
    return {"status": "success", "message": "Research job deleted"}


@router.post("/quick-research")
async def quick_research(
    destination: str,
    interests: List[str] = [],
    db: Session = Depends(get_db)
):
    """
    Quick research endpoint for a single destination.
    
    This runs synchronously and returns results immediately.
    Use this for simple, fast lookups.
    """
    try:
        agent = AutoResearchAgent()
        
        preferences = {
            "destinations": [destination],
            "interests": interests,
            "budget_level": "moderate"
        }
        
        # Run with shorter timeout
        results = await asyncio.wait_for(
            agent.research_from_preferences(preferences),
            timeout=30.0
        )
        
        return {
            "status": "success",
            "destination": destination,
            "results": results["destinations"][0] if results["destinations"] else None
        }
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Research timed out. Try the async endpoint instead.")
    except Exception:
        raise HTTPException(status_code=500, detail="Research failed")


@router.get("/stream/{job_id}")
async def stream_research_progress(job_id: str):
    """
    Server-sent events endpoint for real-time progress updates.
    
    Connect to this endpoint to receive real-time updates on research progress.
    Note: This requires SSE support on the client side.
    """
    # This is a placeholder for SSE implementation
    # In production, you'd use FastAPI's StreamingResponse with SSE format
    raise HTTPException(status_code=501, detail="SSE streaming not yet implemented. Use polling on /status/{job_id}")


@router.get("/config")
async def get_research_config():
    """Get available options for research preferences"""
    return {
        "budget_levels": ["low", "moderate", "high", "luxury"],
        "travel_styles": ["solo", "couple", "family", "group"],
        "visa_preferences": ["visa_free", "visa_on_arrival", "evisa_ok"],
        "weather_preferences": ["hot", "warm", "mild", "cold", "snow"],
        "interests": [
            "beach", "mountain", "city", "history", "nature",
            "adventure", "food", "culture", "relaxation", "nightlife",
            "shopping", "art", "music", "sports", "photography",
            "wildlife", "architecture", "wine", "spa", "hiking"
        ],
        "max_flight_duration_options": [3, 5, 8, 12, 16, 24]
    }
