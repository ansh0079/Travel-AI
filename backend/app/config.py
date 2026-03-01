from pydantic_settings import BaseSettings, Field
from functools import lru_cache
from typing import Optional
import os

class Settings(BaseSettings):
    # App
    app_name: str = "TravelAI"
    debug: bool = False

    # Security - REQUIRED, no default for production safety
    secret_key: str = Field(..., env="SECRET_KEY", min_length=32, 
                            description="Secret key for JWT signing. Must be at least 32 characters.")
    jwt_token_expire_minutes: int = 60 * 24  # 24 hours

    # Database - Default to PostgreSQL for production
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://travelai:travelai@localhost:5432/travelai"),
        description="Database connection URL. PostgreSQL recommended for production."
    )

    # CORS - comma-separated list of allowed origins
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # API Keys - External Services
    # Weather
    openweather_api_key: Optional[str] = None
    
    # Travel/Flights
    amadeus_api_key: Optional[str] = None
    amadeus_api_secret: Optional[str] = None
    
    # Hotels
    booking_api_key: Optional[str] = None
    
    # Events
    ticketmaster_api_key: Optional[str] = None
    predicthq_api_key: Optional[str] = None
    
    # AI/ML - LLM provider
    openai_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    # Set LLM_PROVIDER=deepseek and LLM_BASE_URL=https://api.deepseek.com/v1
    # to switch away from OpenAI. LLM_MODEL defaults to deepseek-chat or gpt-3.5-turbo.
    llm_provider: str = "openai"
    llm_base_url: Optional[str] = None
    llm_model: str = "gpt-3.5-turbo"

    # Web Search
    brave_search_api_key: Optional[str] = None  # https://brave.com/search/api/

    # Attractions/Places
    google_places_api_key: Optional[str] = None
    tripadvisor_api_key: Optional[str] = None

    # Exchange Rates (for affordability)
    exchangerate_api_key: Optional[str] = None

    # Visa Requirements
    visa_requirements_api_key: Optional[str] = None

    # Redis (for caching)
    redis_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Popular destinations database (simplified)
POPULAR_DESTINATIONS = [
    {"id": "paris_fr", "name": "Paris", "country": "France", "country_code": "FR", "city": "Paris", "coordinates": {"lat": 48.8566, "lng": 2.3522}, "cost_index": 75},
    {"id": "tokyo_jp", "name": "Tokyo", "country": "Japan", "country_code": "JP", "city": "Tokyo", "coordinates": {"lat": 35.6762, "lng": 139.6503}, "cost_index": 80},
    {"id": "bali_id", "name": "Bali", "country": "Indonesia", "country_code": "ID", "city": "Denpasar", "coordinates": {"lat": -8.4095, "lng": 115.1889}, "cost_index": 35},
    {"id": "nyc_us", "name": "New York City", "country": "United States", "country_code": "US", "city": "New York", "coordinates": {"lat": 40.7128, "lng": -74.0060}, "cost_index": 85},
    {"id": "london_uk", "name": "London", "country": "United Kingdom", "country_code": "GB", "city": "London", "coordinates": {"lat": 51.5074, "lng": -0.1278}, "cost_index": 80},
    {"id": "dubai_ae", "name": "Dubai", "country": "United Arab Emirates", "country_code": "AE", "city": "Dubai", "coordinates": {"lat": 25.2048, "lng": 55.2708}, "cost_index": 70},
    {"id": "singapore_sg", "name": "Singapore", "country": "Singapore", "country_code": "SG", "city": "Singapore", "coordinates": {"lat": 1.3521, "lng": 103.8198}, "cost_index": 85},
    {"id": "sydney_au", "name": "Sydney", "country": "Australia", "country_code": "AU", "city": "Sydney", "coordinates": {"lat": -33.8688, "lng": 151.2093}, "cost_index": 75},
    {"id": "rome_it", "name": "Rome", "country": "Italy", "country_code": "IT", "city": "Rome", "coordinates": {"lat": 41.9028, "lng": 12.4964}, "cost_index": 65},
    {"id": "barcelona_es", "name": "Barcelona", "country": "Spain", "country_code": "ES", "city": "Barcelona", "coordinates": {"lat": 41.3851, "lng": 2.1734}, "cost_index": 60},
    {"id": "cape_town_za", "name": "Cape Town", "country": "South Africa", "country_code": "ZA", "city": "Cape Town", "coordinates": {"lat": -33.9249, "lng": 18.4241}, "cost_index": 40},
    {"id": "marrakech_ma", "name": "Marrakech", "country": "Morocco", "country_code": "MA", "city": "Marrakech", "coordinates": {"lat": 31.6295, "lng": -7.9811}, "cost_index": 30},
    {"id": "bangkok_th", "name": "Bangkok", "country": "Thailand", "country_code": "TH", "city": "Bangkok", "coordinates": {"lat": 13.7563, "lng": 100.5018}, "cost_index": 35},
    {"id": "istanbul_tr", "name": "Istanbul", "country": "Turkey", "country_code": "TR", "city": "Istanbul", "coordinates": {"lat": 41.0082, "lng": 28.9784}, "cost_index": 40},
    {"id": "kyoto_jp", "name": "Kyoto", "country": "Japan", "country_code": "JP", "city": "Kyoto", "coordinates": {"lat": 35.0116, "lng": 135.7681}, "cost_index": 70},
    {"id": "reykjavik_is", "name": "Reykjavik", "country": "Iceland", "country_code": "IS", "city": "Reykjavik", "coordinates": {"lat": 64.1466, "lng": -21.9426}, "cost_index": 85},
    {"id": "rio_br", "name": "Rio de Janeiro", "country": "Brazil", "country_code": "BR", "city": "Rio de Janeiro", "coordinates": {"lat": -22.9068, "lng": -43.1729}, "cost_index": 45},
    {"id": "cairo_eg", "name": "Cairo", "country": "Egypt", "country_code": "EG", "city": "Cairo", "coordinates": {"lat": 30.0444, "lng": 31.2357}, "cost_index": 25},
    {"id": "prague_cz", "name": "Prague", "country": "Czech Republic", "country_code": "CZ", "city": "Prague", "coordinates": {"lat": 50.0755, "lng": 14.4378}, "cost_index": 45},
    {"id": "auckland_nz", "name": "Auckland", "country": "New Zealand", "country_code": "NZ", "city": "Auckland", "coordinates": {"lat": -36.8485, "lng": 174.7633}, "cost_index": 70},
]