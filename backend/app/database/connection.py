from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings
import logging
import uuid
import os

logger = logging.getLogger(__name__)
settings = get_settings()

_is_sqlite = "sqlite" in settings.database_url

# Ensure directory exists for SQLite database
if _is_sqlite:
    # Extract path from SQLite URL (e.g., "sqlite:///./data/travel_ai.db" -> "./data")
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")
    logger.warning("Using SQLite database - not recommended for production")
else:
    logger.info("Using PostgreSQL database with connection pooling")

# Create engine with appropriate settings
if _is_sqlite:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    # PostgreSQL with connection pooling
    engine = create_engine(
        settings.database_url,
        pool_size=20,
        max_overflow=40,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=settings.debug
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())