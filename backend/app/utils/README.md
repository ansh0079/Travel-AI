# Utils Module

## Circular Import Handling

This module uses lazy imports (imports inside functions) to avoid circular dependencies with the `app.services` module.

### Pattern Used

```python
def some_function():
    from app.services.some_service import SomeService  # Lazy import
    service = SomeService()
    return service.do_something()
```

### Why This Pattern?

The services import from utils (for caching, scoring, etc.), and utils may need services for calculations. Lazy imports break the circular dependency by only importing when the function is actually called at runtime.

### Affected Files

- `scoring.py` - Imports WeatherService, AffordabilityService, VisaService, AttractionsService

### Future Refactoring

Consider using dependency injection or passing services as parameters to eliminate lazy imports:

```python
# Better pattern
def calculate_score(destination, preferences, weather_service, visa_service):
    # Services injected as parameters
    pass
```
