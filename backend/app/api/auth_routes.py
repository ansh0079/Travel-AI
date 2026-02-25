from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional
import json

from app.database.connection import get_db
from app.database.models import User, UserPreferences
from app.utils.security import (
    verify_password, get_password_hash, create_access_token, get_current_user
)
from app.config import get_settings
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
settings = get_settings()

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    passport_country: Optional[str] = "US"

class UserPreferencesInput(BaseModel):
    budget_daily: float = Field(default=150.0, gt=0)
    budget_total: float = Field(default=3000.0, gt=0)
    travel_style: str = "moderate"
    interests: list = []
    preferred_weather: Optional[str] = None
    avoid_weather: Optional[str] = None
    passport_country: str = "US"
    visa_preference: str = "visa_free"
    max_flight_duration: Optional[int] = None
    traveling_with: str = "solo"
    accessibility_needs: list = []
    dietary_restrictions: list = []

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

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        passport_country=user_data.passport_country or "US"
    )
    db.add(user)
    db.flush()  # Get user ID
    
    # Create default preferences
    preferences = UserPreferences(
        user_id=user.id,
        passport_country=user_data.passport_country or "US"
    )
    db.add(preferences)
    
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        passport_country=user.passport_country,
        is_active=user.is_active
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login user and return JWT token"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.jwt_token_expire_minutes)
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            passport_country=user.passport_country,
            is_active=user.is_active
        )
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        passport_country=current_user.passport_country,
        is_active=current_user.is_active
    )

@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    
    return {
        "budget_daily": prefs.budget_daily,
        "budget_total": prefs.budget_total,
        "travel_style": prefs.travel_style,
        "interests": json.loads(prefs.interests) if prefs.interests else [],
        "preferred_weather": prefs.preferred_weather,
        "avoid_weather": prefs.avoid_weather,
        "passport_country": prefs.passport_country,
        "visa_preference": prefs.visa_preference,
        "max_flight_duration": prefs.max_flight_duration,
        "traveling_with": prefs.traveling_with,
        "accessibility_needs": json.loads(prefs.accessibility_needs) if prefs.accessibility_needs else [],
        "dietary_restrictions": json.loads(prefs.dietary_restrictions) if prefs.dietary_restrictions else []
    }

@router.put("/preferences")
async def update_preferences(
    preferences_data: UserPreferencesInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    user_prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not user_prefs:
        user_prefs = UserPreferences(user_id=current_user.id)
        db.add(user_prefs)
    
    # Update fields
    user_prefs.budget_daily = preferences_data.budget_daily
    user_prefs.budget_total = preferences_data.budget_total
    user_prefs.travel_style = preferences_data.travel_style
    user_prefs.interests = json.dumps(preferences_data.interests)
    user_prefs.preferred_weather = preferences_data.preferred_weather
    user_prefs.avoid_weather = preferences_data.avoid_weather
    user_prefs.passport_country = preferences_data.passport_country
    user_prefs.visa_preference = preferences_data.visa_preference
    user_prefs.max_flight_duration = preferences_data.max_flight_duration
    user_prefs.traveling_with = preferences_data.traveling_with
    user_prefs.accessibility_needs = json.dumps(preferences_data.accessibility_needs)
    user_prefs.dietary_restrictions = json.dumps(preferences_data.dietary_restrictions)
    
    # Update user passport country if changed
    if preferences_data.passport_country != current_user.passport_country:
        current_user.passport_country = preferences_data.passport_country
    
    db.commit()
    db.refresh(user_prefs)
    
    return {
        "message": "Preferences updated successfully",
        "preferences": {
            "budget_daily": user_prefs.budget_daily,
            "budget_total": user_prefs.budget_total,
            "travel_style": user_prefs.travel_style,
            "interests": json.loads(user_prefs.interests) if user_prefs.interests else [],
            "passport_country": user_prefs.passport_country
        }
    }

@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}