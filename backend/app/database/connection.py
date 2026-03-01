from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import get_settings
from app.utils.logging_config import get_logger
import uuid

logger = get_logger(__name__)
settings = get_settings()

_is_sqlite = "sqlite" in settings.database_url

# Log database configuration
if _is_sqlite:
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