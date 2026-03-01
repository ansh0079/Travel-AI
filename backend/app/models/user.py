from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import date, datetime
from enum import Enum

class TravelStyle(str, Enum):
    BUDGET = "budget"
    MODERATE = "moderate"
    COMFORT = "comfort"
    LUXURY = "luxury"

class Interest(str, Enum):
    NATURE = "nature"
    CULTURE = "culture"
    ADVENTURE = "adventure"
    RELAXATION = "relaxation"
    FOOD = "food"
    NIGHTLIFE = "nightlife"
    SHOPPING = "shopping"
    HISTORY = "history"
    ART = "art"
    BEACHES = "beaches"
    MOUNTAINS = "mountains"
    WILDLIFE = "wildlife"

class UserPreferences(BaseModel):
    budget_daily: float = Field(default=150.0, gt=0)
    budget_total: float = Field(default=3000.0, gt=0)
    travel_style: TravelStyle = TravelStyle.MODERATE
    interests: List[Interest] = []
    preferred_weather: Optional[str] = None  # hot, warm, mild, cold, snowy
    avoid_weather: Optional[str] = None  # rain, snow, extreme_heat, extreme_cold
    passport_country: str = "US"
    visa_preference: str = "visa_free"  # visa_free, evisa_ok, visa_ok
    max_flight_duration: Optional[int] = None  # hours
    traveling_with: str = "solo"  # solo, couple, family, friends
    accessibility_needs: List[str] = []
    dietary_restrictions: List[str] = []
    # Location preferences
    preferred_continent: Optional[str] = None  # europe, asia, north_america, south_america, africa, oceania, antarctica
    preferred_countries: List[str] = []  # List of country names or codes to filter by

class TravelRequest(BaseModel):
    origin: str
    travel_start: date
    travel_end: date
    num_travelers: int = Field(default=1, ge=1)
    num_recommendations: int = Field(default=5, ge=1, le=10)
    user_preferences: UserPreferences
    
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    passport_country: Optional[str] = "US"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    passport_country: Optional[str]
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    
class SearchHistoryItem(BaseModel):
    id: str
    search_query: str
    results_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True