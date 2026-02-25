# API routers - imported lazily to avoid circular imports

__all__ = ["main_router", "auth_router"]

# Don't import here - let main.py import directly from the modules
# to avoid circular import issues
