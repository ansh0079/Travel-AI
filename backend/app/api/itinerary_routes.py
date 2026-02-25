from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database.connection import get_db
from app.database.models import Itinerary, ItineraryDay, ItineraryActivity, User
from app.models.itinerary import (
    ItineraryCreate, ItineraryUpdate, ItineraryResponse, ItinerarySummary,
    ItineraryDayCreate, ItineraryDayUpdate,
    ItineraryActivityCreate, ItineraryActivityUpdate, ItineraryActivityResponse
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/api/v1/itineraries", tags=["itineraries"])


def _activity_to_response(activity: ItineraryActivity) -> dict:
    """Convert activity DB model to response dict"""
    return {
        "id": activity.id,
        "day_id": activity.day_id,
        "title": activity.title,
        "description": activity.description,
        "activity_type": activity.activity_type,
        "start_time": activity.start_time,
        "end_time": activity.end_time,
        "location_name": activity.location_name,
        "latitude": activity.latitude,
        "longitude": activity.longitude,
        "cost": activity.cost,
        "booking_reference": activity.booking_reference,
        "notes": activity.notes,
        "created_at": activity.created_at
    }


def _day_to_response(day: ItineraryDay) -> dict:
    """Convert day DB model to response dict"""
    return {
        "id": day.id,
        "itinerary_id": day.itinerary_id,
        "day_number": day.day_number,
        "date": day.date,
        "notes": day.notes,
        "activities": [_activity_to_response(a) for a in day.activities]
    }


def _itinerary_to_response(itinerary: Itinerary) -> dict:
    """Convert itinerary DB model to response dict"""
    return {
        "id": itinerary.id,
        "user_id": itinerary.user_id,
        "title": itinerary.title,
        "destination_id": itinerary.destination_id,
        "destination_name": itinerary.destination_name,
        "destination_country": itinerary.destination_country,
        "travel_start": itinerary.travel_start.date(),
        "travel_end": itinerary.travel_end.date(),
        "notes": itinerary.notes,
        "is_public": itinerary.is_public,
        "created_at": itinerary.created_at,
        "updated_at": itinerary.updated_at,
        "days": [_day_to_response(d) for d in sorted(itinerary.days, key=lambda x: x.day_number)]
    }


def _itinerary_to_summary(itinerary: Itinerary) -> dict:
    """Convert itinerary to summary response"""
    total_activities = sum(len(day.activities) for day in itinerary.days)
    return {
        "id": itinerary.id,
        "title": itinerary.title,
        "destination_name": itinerary.destination_name,
        "destination_country": itinerary.destination_country,
        "travel_start": itinerary.travel_start.date(),
        "travel_end": itinerary.travel_end.date(),
        "is_public": itinerary.is_public,
        "created_at": itinerary.created_at,
        "total_days": len(itinerary.days),
        "total_activities": total_activities
    }


@router.post("", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED)
async def create_itinerary(
    itinerary_data: ItineraryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new itinerary"""
    # Calculate number of days
    num_days = (itinerary_data.travel_end - itinerary_data.travel_start).days + 1
    
    # Create itinerary
    db_itinerary = Itinerary(
        user_id=current_user.id,
        title=itinerary_data.title,
        destination_id=itinerary_data.destination_id,
        destination_name=itinerary_data.destination_name,
        destination_country=itinerary_data.destination_country,
        travel_start=datetime.combine(itinerary_data.travel_start, datetime.min.time()),
        travel_end=datetime.combine(itinerary_data.travel_end, datetime.min.time()),
        notes=itinerary_data.notes,
        is_public=itinerary_data.is_public
    )
    db.add(db_itinerary)
    db.flush()  # Get the itinerary ID
    
    # Create days if provided, otherwise auto-generate empty days
    if itinerary_data.days:
        for day_data in itinerary_data.days:
            db_day = ItineraryDay(
                itinerary_id=db_itinerary.id,
                day_number=day_data.day_number,
                date=day_data.date,
                notes=day_data.notes
            )
            db.add(db_day)
            db.flush()
            
            # Add activities for this day
            for activity_data in day_data.activities:
                db_activity = ItineraryActivity(
                    day_id=db_day.id,
                    title=activity_data.title,
                    description=activity_data.description,
                    activity_type=activity_data.activity_type,
                    start_time=activity_data.start_time,
                    end_time=activity_data.end_time,
                    location_name=activity_data.location_name,
                    latitude=activity_data.latitude,
                    longitude=activity_data.longitude,
                    cost=activity_data.cost,
                    booking_reference=activity_data.booking_reference,
                    notes=activity_data.notes
                )
                db.add(db_activity)
    else:
        # Auto-generate empty days
        for i in range(num_days):
            day_date = datetime.combine(
                itinerary_data.travel_start + timedelta(days=i),
                datetime.min.time()
            )
            db_day = ItineraryDay(
                itinerary_id=db_itinerary.id,
                day_number=i + 1,
                date=day_date,
                notes=None
            )
            db.add(db_day)
    
    db.commit()
    db.refresh(db_itinerary)
    
    return _itinerary_to_response(db_itinerary)


@router.get("", response_model=List[ItinerarySummary])
async def list_itineraries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all itineraries for the current user"""
    itineraries = db.query(Itinerary).filter(
        Itinerary.user_id == current_user.id
    ).order_by(Itinerary.created_at.desc()).all()
    
    return [_itinerary_to_summary(i) for i in itineraries]


@router.get("/public", response_model=List[ItinerarySummary])
async def list_public_itineraries(
    db: Session = Depends(get_db)
):
    """List all public itineraries"""
    itineraries = db.query(Itinerary).filter(
        Itinerary.is_public == True
    ).order_by(Itinerary.created_at.desc()).all()
    
    return [_itinerary_to_summary(i) for i in itineraries]


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(
    itinerary_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific itinerary"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    # Check if user owns the itinerary or if it's public
    if itinerary.user_id != current_user.id and not itinerary.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to view this itinerary")
    
    return _itinerary_to_response(itinerary)


@router.put("/{itinerary_id}", response_model=ItineraryResponse)
async def update_itinerary(
    itinerary_id: str,
    update_data: ItineraryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an itinerary"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this itinerary")
    
    # Update fields
    if update_data.title is not None:
        itinerary.title = update_data.title
    if update_data.notes is not None:
        itinerary.notes = update_data.notes
    if update_data.is_public is not None:
        itinerary.is_public = update_data.is_public
    if update_data.travel_start is not None:
        itinerary.travel_start = datetime.combine(update_data.travel_start, datetime.min.time())
    if update_data.travel_end is not None:
        itinerary.travel_end = datetime.combine(update_data.travel_end, datetime.min.time())
    
    db.commit()
    db.refresh(itinerary)
    
    return _itinerary_to_response(itinerary)


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_itinerary(
    itinerary_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an itinerary"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this itinerary")
    
    db.delete(itinerary)
    db.commit()
    
    return None


# Day management endpoints

@router.post("/{itinerary_id}/days", response_model=ItineraryResponse)
async def add_day(
    itinerary_id: str,
    day_data: ItineraryDayCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a day to an itinerary"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this itinerary")
    
    db_day = ItineraryDay(
        itinerary_id=itinerary_id,
        day_number=day_data.day_number,
        date=day_data.date,
        notes=day_data.notes
    )
    db.add(db_day)
    db.flush()
    
    # Add activities
    for activity_data in day_data.activities:
        db_activity = ItineraryActivity(
            day_id=db_day.id,
            **activity_data.dict()
        )
        db.add(db_activity)
    
    db.commit()
    db.refresh(itinerary)
    
    return _itinerary_to_response(itinerary)


@router.put("/{itinerary_id}/days/{day_id}", response_model=ItineraryResponse)
async def update_day(
    itinerary_id: str,
    day_id: str,
    day_data: ItineraryDayUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a day in an itinerary"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this itinerary")
    
    day = db.query(ItineraryDay).filter(
        ItineraryDay.id == day_id,
        ItineraryDay.itinerary_id == itinerary_id
    ).first()
    
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    
    if day_data.day_number is not None:
        day.day_number = day_data.day_number
    if day_data.date is not None:
        day.date = day_data.date
    if day_data.notes is not None:
        day.notes = day_data.notes
    
    db.commit()
    db.refresh(itinerary)
    
    return _itinerary_to_response(itinerary)


@router.delete("/{itinerary_id}/days/{day_id}", response_model=ItineraryResponse)
async def delete_day(
    itinerary_id: str,
    day_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a day from an itinerary"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this itinerary")
    
    day = db.query(ItineraryDay).filter(
        ItineraryDay.id == day_id,
        ItineraryDay.itinerary_id == itinerary_id
    ).first()
    
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    
    db.delete(day)
    db.commit()
    db.refresh(itinerary)
    
    return _itinerary_to_response(itinerary)


# Activity management endpoints

@router.post("/{itinerary_id}/days/{day_id}/activities", response_model=ItineraryResponse)
async def add_activity(
    itinerary_id: str,
    day_id: str,
    activity_data: ItineraryActivityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an activity to a day"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this itinerary")
    
    day = db.query(ItineraryDay).filter(
        ItineraryDay.id == day_id,
        ItineraryDay.itinerary_id == itinerary_id
    ).first()
    
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    
    db_activity = ItineraryActivity(
        day_id=day_id,
        **activity_data.dict()
    )
    db.add(db_activity)
    db.commit()
    db.refresh(itinerary)
    
    return _itinerary_to_response(itinerary)


@router.put("/{itinerary_id}/days/{day_id}/activities/{activity_id}", response_model=ItineraryResponse)
async def update_activity(
    itinerary_id: str,
    day_id: str,
    activity_id: str,
    activity_data: ItineraryActivityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an activity"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this itinerary")
    
    activity = db.query(ItineraryActivity).join(ItineraryDay).filter(
        ItineraryActivity.id == activity_id,
        ItineraryActivity.day_id == day_id,
        ItineraryDay.itinerary_id == itinerary_id
    ).first()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Update fields
    update_dict = activity_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(activity, field, value)
    
    db.commit()
    db.refresh(itinerary)
    
    return _itinerary_to_response(itinerary)


@router.delete("/{itinerary_id}/days/{day_id}/activities/{activity_id}", response_model=ItineraryResponse)
async def delete_activity(
    itinerary_id: str,
    day_id: str,
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an activity"""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this itinerary")
    
    activity = db.query(ItineraryActivity).join(ItineraryDay).filter(
        ItineraryActivity.id == activity_id,
        ItineraryActivity.day_id == day_id,
        ItineraryDay.itinerary_id == itinerary_id
    ).first()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    db.delete(activity)
    db.commit()
    db.refresh(itinerary)
    
    return _itinerary_to_response(itinerary)
