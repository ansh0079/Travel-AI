"""
Logging configuration for the application
Provides structured logging with JSON output for production
"""
import logging
import sys
from typing import Optional
import structlog


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' for production, 'console' for development)
    """
    
    # Shared processors for all loggers
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if log_format == "json":
        # Production JSON formatting
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Development console formatting
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            if log_format == "console"
            else "%(message)s"
        )
    )
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
