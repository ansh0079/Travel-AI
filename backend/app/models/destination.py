from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    MUSIC = "music"
    THEATRE = "theatre"
    FILM = "film"
    SPORTS = "sports"
    FESTIVAL = "festival"
    CULTURAL = "cultural"
    FOOD = "food"
    ART = "art"

class Weather(BaseModel):
    condition: str
    temperature: float
    humidity: int
    wind_speed: float
    forecast_days: List[dict] = []
    recommendation: str = ""

class Affordability(BaseModel):
    cost_level: str  # budget, moderate, expensive, luxury
    daily_cost_estimate: float
    currency: str = "USD"
    accommodation_avg: float
    food_avg: float
    transport_avg: float
    activities_avg: float
    cost_index: float = Field(..., ge=0, le=200)  # 0=cheapest, 200=most expensive (NYC=100 baseline)

class Visa(BaseModel):
    required: bool
    type: Optional[str] = None
    duration_days: Optional[int] = None
    processing_days: Optional[int] = None
    cost_usd: Optional[float] = None
    evisa_available: bool = False
    visa_free_days: Optional[int] = None
    notes: str = ""

class Attraction(BaseModel):
    id: str
    name: str
    type: str
    rating: float = Field(..., ge=0, le=5)
    description: str
    image_url: Optional[str] = None
    location: Dict[str, float]  # lat, lng
    entry_fee: Optional[float] = None
    currency: str = "USD"
    opening_hours: Optional[str] = None
    duration_hours: Optional[float] = None
    best_time_to_visit: Optional[str] = None
    natural_feature: bool = False  # True for natural attractions

class Event(BaseModel):
    id: str
    name: str
    type: EventType
    date: datetime
    venue: str
    description: Optional[str] = None
    price_range: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None

class Destination(BaseModel):
    id: str
    name: str
    country: str
    city: str
    country_code: str
    coordinates: Dict[str, float]  # lat, lng
    description: Optional[str] = None
    image_url: Optional[str] = None
    
    # Enriched data from APIs
    weather: Optional[Weather] = None
    affordability: Optional[Affordability] = None
    visa: Optional[Visa] = None
    attractions: List[Attraction] = []
    events: List[Event] = []
    
    # AI scoring
    overall_score: float = Field(default=0.0, ge=0, le=100)
    recommendation_reason: str = ""
    
    # Category scores
    weather_score: float = Field(default=0.0, ge=0, le=100)
    affordability_score: float = Field(default=0.0, ge=0, le=100)
    visa_score: float = Field(default=0.0, ge=0, le=100)
    attractions_score: float = Field(default=0.0, ge=0, le=100)
    events_score: float = Field(default=0.0, ge=0, le=100)
    
    class Config:
        from_attributes = True