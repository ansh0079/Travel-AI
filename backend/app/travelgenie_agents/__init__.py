"""
TravelGenie Multi-Agent System
6 Specialized Agents for Travel Planning
"""

from .weather_agent import WeatherAgent
from .route_agent import RouteAgent
from .flight_agent import AmadeusFlightSearch
from .food_agent import FoodExplorerAgent
from .explorer_agent import ExplorerAgent
from .event_agent import EventAgent

# OpenStreetMap alternatives (FREE, no API key needed)
from .openstreetmap_agents import OSMRouteAgent, OSMFoodAgent, OSMExplorerAgent

__all__ = [
    'WeatherAgent',
    'RouteAgent', 
    'AmadeusFlightSearch',
    'FoodExplorerAgent',
    'ExplorerAgent',
    'EventAgent',
    'OSMRouteAgent',
    'OSMFoodAgent',
    'OSMExplorerAgent'
]
