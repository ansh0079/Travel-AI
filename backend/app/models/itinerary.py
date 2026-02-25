from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from enum import Enum


class ActivityType(str, Enum):
    ATTRACTION = "attraction"
    RESTAURANT = "restaurant"
    EVENT = "event"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    SHOPPING = "shopping"
    RELAXATION = "relaxation"
    GENERAL = "general"


class ItineraryActivityBase(BaseModel):
    title: str
    description: Optional[str] = None
    activity_type: ActivityType = ActivityType.GENERAL
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cost: float = 0.0
    booking_reference: Optional[str] = None
    notes: Optional[str] = None


class ItineraryActivityCreate(ItineraryActivityBase):
    pass


class ItineraryActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    activity_type: Optional[ActivityType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cost: Optional[float] = None
    booking_reference: Optional[str] = None
    notes: Optional[str] = None


class ItineraryActivityResponse(ItineraryActivityBase):
    id: str
    day_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class ItineraryDayBase(BaseModel):
    day_number: int = Field(..., ge=1)
    date: datetime
    notes: Optional[str] = None


class ItineraryDayCreate(ItineraryDayBase):
    activities: List[ItineraryActivityCreate] = []


class ItineraryDayUpdate(BaseModel):
    day_number: Optional[int] = None
    date: Optional[datetime] = None
    notes: Optional[str] = None


class ItineraryDayResponse(ItineraryDayBase):
    id: str
    itinerary_id: str
    activities: List[ItineraryActivityResponse] = []

    class Config:
        from_attributes = True


class ItineraryBase(BaseModel):
    title: str
    destination_id: str
    destination_name: str
    destination_country: str
    travel_start: date
    travel_end: date
    notes: Optional[str] = None
    is_public: bool = False


class ItineraryCreate(ItineraryBase):
    days: List[ItineraryDayCreate] = []


class ItineraryUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    is_public: Optional[bool] = None
    travel_start: Optional[date] = None
    travel_end: Optional[date] = None


class ItineraryResponse(ItineraryBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    days: List[ItineraryDayResponse] = []

    class Config:
        from_attributes = True


class ItinerarySummary(BaseModel):
    id: str
    title: str
    destination_name: str
    destination_country: str
    travel_start: date
    travel_end: date
    is_public: bool
    created_at: datetime
    total_days: int
    total_activities: int

    class Config:
        from_attributes = True
