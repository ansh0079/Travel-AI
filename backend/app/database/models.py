from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from app.database.connection import generate_uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    passport_country = Column(String, nullable=True, default="US")
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)
    bookings = relationship("TravelBooking", back_populates="user")
    search_history = relationship("SearchHistory", back_populates="user")

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, index=True)
    budget_daily = Column(Float, default=150.0)
    budget_total = Column(Float, default=3000.0)
    travel_style = Column(String, default="moderate", index=True)
    interests = Column(Text, default="[]")  # JSON string
    preferred_weather = Column(String, nullable=True)
    avoid_weather = Column(String, nullable=True)
    passport_country = Column(String, default="US")
    visa_preference = Column(String, default="visa_free", index=True)
    max_flight_duration = Column(Integer, nullable=True)
    traveling_with = Column(String, default="solo")
    accessibility_needs = Column(Text, default="[]")  # JSON string
    dietary_restrictions = Column(Text, default="[]")  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")

class TravelBooking(Base):
    __tablename__ = "travel_bookings"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    destination_id = Column(String, nullable=False, index=True)
    destination_name = Column(String, nullable=False)
    destination_country = Column(String, nullable=False)
    travel_start = Column(DateTime, nullable=False)
    travel_end = Column(DateTime, nullable=False)
    total_cost = Column(Float, default=0.0)
    status = Column(String, default="planning", index=True)  # planning, booked, completed, cancelled
    booking_data = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="bookings")

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    origin = Column(String, nullable=False, index=True)
    destination = Column(String, nullable=True, index=True)
    travel_start = Column(DateTime, nullable=True)
    travel_end = Column(DateTime, nullable=True)
    search_query = Column(Text, nullable=False)
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="search_history")

class SavedDestination(Base):
    __tablename__ = "saved_destinations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    destination_id = Column(String, nullable=False, index=True)
    destination_name = Column(String, nullable=False)
    destination_country = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")


class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    title = Column(String, nullable=False)
    destination_id = Column(String, nullable=False)
    destination_name = Column(String, nullable=False)
    destination_country = Column(String, nullable=False)
    travel_start = Column(DateTime, nullable=False)
    travel_end = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")
    days = relationship("ItineraryDay", back_populates="itinerary", cascade="all, delete-orphan")


class ItineraryDay(Base):
    __tablename__ = "itinerary_days"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    itinerary_id = Column(String, ForeignKey("itineraries.id"), index=True)
    day_number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    
    itinerary = relationship("Itinerary", back_populates="days")
    activities = relationship("ItineraryActivity", back_populates="day", cascade="all, delete-orphan")


class ItineraryActivity(Base):
    __tablename__ = "itinerary_activities"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    day_id = Column(String, ForeignKey("itinerary_days.id"), index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    activity_type = Column(String, default="general")  # attraction, restaurant, event, transport, etc.
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    location_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    cost = Column(Float, default=0.0)
    booking_reference = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    day = relationship("ItineraryDay", back_populates="activities")


class ResearchJob(Base):
    """Tracks background research jobs for user queries"""
    __tablename__ = "research_jobs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    job_type = Column(String, nullable=False, index=True)  # 'destination_research', 'comparison', 'itinerary'
    status = Column(String, default="pending", index=True)  # pending, in_progress, completed, failed
    
    # Input parameters (stored as JSON)
    query_params = Column(Text, default="{}")  # JSON string of user preferences/answers
    
    # Progress tracking
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    
    # Results (stored as JSON)
    results = Column(Text, nullable=True)  # JSON string of research results
    errors = Column(Text, nullable=True)  # JSON string of any errors
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User")