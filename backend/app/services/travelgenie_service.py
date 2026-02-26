"""
TravelGenie Service - Integration of 6-Agent System
"""
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.travelgenie_agents import (
    WeatherAgent,
    RouteAgent,
    AmadeusFlightSearch,
    FoodExplorerAgent,
    ExplorerAgent,
    EventAgent
)


class TravelGenieService:
    """
    Service wrapper for TravelGenie's 6-Agent System:
    - Weather Agent: Forecast and climate data
    - Route Agent: Distance, duration, fuel estimates
    - Flight Agent: Amadeus flight search
    - Food Agent: Restaurant recommendations
    - Explorer Agent: Attractions and places
    - Event Agent: Ticketmaster events
    """
    
    def __init__(self):
        self.api_keys = {
            'openweather': os.getenv('OPEN_WEATHER_API_KEY'),
            'google_maps': os.getenv('GOOGLE_MAPS_API_KEY'),
            'ticketmaster': os.getenv('TICKETMASTER_API_KEY'),
            'amadeus_key': os.getenv('AMADEUS_API_KEY'),
            'amadeus_secret': os.getenv('AMADEUS_SECRET_KEY')
        }
        
        # Initialize agents with available keys
        self.agents = {}
        
        if self.api_keys['openweather']:
            self.agents['weather'] = WeatherAgent(api_key=self.api_keys['openweather'])
        
        if self.api_keys['google_maps']:
            self.agents['route'] = RouteAgent(api_key=self.api_keys['google_maps'])
            self.agents['food'] = FoodExplorerAgent(api_key=self.api_keys['google_maps'])
            self.agents['explorer'] = ExplorerAgent(api_key=self.api_keys['google_maps'])
        
        if self.api_keys['ticketmaster']:
            self.agents['events'] = EventAgent(api_key=self.api_keys['ticketmaster'])
        
        if self.api_keys['amadeus_key'] and self.api_keys['amadeus_secret']:
            self.agents['flights'] = AmadeusFlightSearch(
                api_key=self.api_keys['amadeus_key'],
                api_secret=self.api_keys['amadeus_secret']
            )
    
    def get_weather(self, location: str, travel_date: str) -> Dict[str, Any]:
        """Get weather forecast for location on specific date"""
        if 'weather' not in self.agents:
            return {"error": "Weather agent not configured. Set OPEN_WEATHER_API_KEY."}
        
        try:
            return self.agents['weather'].get_weather(location, travel_date)
        except Exception as e:
            return {"error": str(e)}
    
    def get_route(self, source: str, destination: str) -> Dict[str, Any]:
        """Get route information including distance, duration, fuel"""
        if 'route' not in self.agents:
            return {"error": "Route agent not configured. Set GOOGLE_MAPS_API_KEY."}
        
        try:
            return self.agents['route'].get_route(source, destination)
        except Exception as e:
            return {"error": str(e)}
    
    def get_flights(
        self,
        origin_city: str,
        destination_city: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_results: int = 10
    ) -> List[Dict]:
        """Search flights using Amadeus API"""
        if 'flights' not in self.agents:
            return [{"error": "Flight agent not configured. Set AMADEUS_API_KEY and AMADEUS_SECRET_KEY."}]
        
        try:
            return self.agents['flights'].search_flights(
                origin_city=origin_city,
                destination_city=destination_city,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                max_results=max_results
            )
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_restaurants(self, location: str) -> Dict[str, Any]:
        """Get top restaurants in location"""
        if 'food' not in self.agents:
            return {"error": "Food agent not configured. Set GOOGLE_MAPS_API_KEY."}
        
        try:
            return self.agents['food'].get_top_restaurants(location)
        except Exception as e:
            return {"error": str(e)}
    
    def get_attractions(self, location: str) -> Dict[str, Any]:
        """Get top attractions in location"""
        if 'explorer' not in self.agents:
            return {"error": "Explorer agent not configured. Set GOOGLE_MAPS_API_KEY."}
        
        try:
            return self.agents['explorer'].get_attractions(location)
        except Exception as e:
            return {"error": str(e)}
    
    def get_events(
        self,
        location: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get events from Ticketmaster"""
        if 'events' not in self.agents:
            return {"error": "Event agent not configured. Set TICKETMASTER_API_KEY."}
        
        try:
            return self.agents['events'].get_events(location, start_date, end_date)
        except Exception as e:
            return {"error": str(e)}
    
    def get_complete_travel_info(
        self,
        source: str,
        destination: str,
        travel_date: str,
        return_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive travel information from all agents"""
        result = {
            "source": source,
            "destination": destination,
            "travel_date": travel_date,
            "return_date": return_date,
            "agents_used": [],
            "data": {}
        }
        
        # Weather
        if 'weather' in self.agents:
            result["data"]["weather"] = self.get_weather(destination, travel_date)
            result["agents_used"].append("weather")
        
        # Route
        if 'route' in self.agents:
            result["data"]["route"] = self.get_route(source, destination)
            result["agents_used"].append("route")
        
        # Flights
        if 'flights' in self.agents and return_date:
            flights = self.get_flights(source, destination, travel_date, return_date)
            result["data"]["flights"] = flights
            result["agents_used"].append("flights")
        
        # Attractions
        if 'explorer' in self.agents:
            result["data"]["attractions"] = self.get_attractions(destination)
            result["agents_used"].append("explorer")
        
        # Restaurants
        if 'food' in self.agents:
            result["data"]["restaurants"] = self.get_restaurants(destination)
            result["agents_used"].append("food")
        
        # Events
        if 'events' in self.agents:
            result["data"]["events"] = self.get_events(destination, travel_date, return_date)
            result["agents_used"].append("events")
        
        return result


# Singleton instance
travelgenie_service = TravelGenieService()
