"""
OpenStreetMap-based Agents (FREE - No API key required)
Replaces Google Maps agents with open-source alternatives
"""
import requests
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import math


class OSMRouteAgent:
    """Route agent using OpenStreetMap (OSRM) - FREE"""
    
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        self.osrm_url = "http://router.project-osrm.org"
    
    def geocode_location(self, place_name: str) -> tuple:
        """Convert location name to lat/lon using Nominatim"""
        try:
            params = {
                "q": place_name,
                "format": "json",
                "limit": 1
            }
            headers = {"User-Agent": "TravelAI/1.0"}
            response = requests.get(f"{self.nominatim_url}/search", params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
            else:
                raise Exception(f"Location not found: {place_name}")
        except Exception as e:
            raise Exception(f"Geocoding error: {str(e)}")
    
    def get_route(self, source: str, destination: str) -> Dict[str, Any]:
        """Get route using OSRM (Open Source Routing Machine)"""
        try:
            # Geocode source and destination
            source_lat, source_lon = self.geocode_location(source)
            dest_lat, dest_lon = self.geocode_location(destination)
            
            # Get route from OSRM
            coords = f"{source_lon},{source_lat};{dest_lon},{dest_lat}"
            url = f"{self.osrm_url}/route/v1/driving/{coords}"
            params = {
                "overview": "false",
                "steps": "false"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                distance_meters = route["distance"]
                duration_seconds = route["duration"]
                
                # Convert to readable formats
                distance_km = round(distance_meters / 1000, 2)
                distance_miles = round(distance_meters * 0.000621371, 2)
                duration_minutes = round(duration_seconds / 60, 1)
                duration_hours = round(duration_seconds / 3600, 2)
                
                # Estimate fuel (approx 8L per 100km for average car)
                fuel_liters = round((distance_km / 100) * 8, 2)
                
                summary = f"Route from {source} to {destination} is {distance_miles} miles ({distance_km} km) and takes approx {duration_hours} hours."
                
                return {
                    "source": source,
                    "destination": destination,
                    "distance_meters": int(distance_meters),
                    "distance_km": distance_km,
                    "distance_miles": distance_miles,
                    "duration_seconds": int(duration_seconds),
                    "duration_minutes": duration_minutes,
                    "duration_hours": duration_hours,
                    "fuel_estimate_liters": fuel_liters,
                    "route_labels": ["driving"],
                    "warnings": [],
                    "summary": summary,
                    "provider": "OpenStreetMap (OSRM)",
                    "coordinates": {
                        "source": {"lat": source_lat, "lon": source_lon},
                        "destination": {"lat": dest_lat, "lon": dest_lon}
                    }
                }
            else:
                return {
                    "source": source,
                    "destination": destination,
                    "distance_meters": 0,
                    "duration": "",
                    "fuel_estimate_liters": None,
                    "warnings": ["Unable to fetch route from OSRM"],
                    "summary": "",
                    "provider": "OpenStreetMap"
                }
                
        except Exception as e:
            return {
                "source": source,
                "destination": destination,
                "distance_meters": 0,
                "duration": "",
                "fuel_estimate_liters": None,
                "warnings": [f"Error: {str(e)}"],
                "summary": "",
                "provider": "OpenStreetMap"
            }


class OSMRestaurant:
    def __init__(self, data: dict):
        self.name = data.get("tags", {}).get("name", "Unknown Restaurant")
        self.address = self._build_address(data.get("tags", {}))
        self.rating = float(data.get("tags", {}).get("rating", 0) or 0)
        self.total_ratings = 0  # OSM doesn't have review counts
        self.types = [data.get("tags", {}).get("cuisine", "restaurant")]
        self.photo_url = None
        self.lat = data.get("lat")
        self.lon = data.get("lon")
    
    def _build_address(self, tags: dict) -> str:
        parts = []
        for key in ["addr:street", "addr:housenumber", "addr:city", "addr:country"]:
            if tags.get(key):
                parts.append(tags[key])
        return ", ".join(parts) if parts else "Address not available"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address": self.address,
            "rating": self.rating,
            "total_ratings": self.total_ratings,
            "types": self.types,
            "photo_url": self.photo_url,
            "location": {"lat": self.lat, "lon": self.lon}
        }


class OSMFoodAgent:
    """Food/Restaurant agent using OpenStreetMap - FREE"""
    
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org"
    
    def get_top_restaurants(self, location: str) -> Dict[str, Any]:
        """Find restaurants using Overpass API"""
        try:
            # First geocode the location to get bounding box
            lat, lon = self._geocode(location)
            
            # Query Overpass for restaurants near that location
            query = f"""
            [out:json][timeout:25];
            (
              node["amenity"="restaurant"](around:5000,{lat},{lon});
              way["amenity"="restaurant"](around:5000,{lat},{lon});
              node["amenity"="cafe"](around:5000,{lat},{lon});
              way["amenity"="cafe"](around:5000,{lat},{lon});
            );
            out body 10;
            >;
            out skel qt;
            """
            
            response = requests.post(self.overpass_url, data={"data": query}, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            restaurants = []
            for element in data.get("elements", []):
                if element.get("tags") and "name" in element["tags"]:
                    restaurant = OSMRestaurant(element)
                    restaurants.append(restaurant.to_dict())
            
            # If no results, return fallback with location info
            if not restaurants:
                restaurants = self._get_fallback_restaurants(location)
            
            return {
                "location": location,
                "top_restaurants": restaurants[:10],
                "total_found": len(restaurants),
                "provider": "OpenStreetMap"
            }
            
        except Exception as e:
            return {
                "location": location,
                "top_restaurants": self._get_fallback_restaurants(location),
                "total_found": 0,
                "provider": "OpenStreetMap (Fallback)",
                "error": str(e)
            }
    
    def _geocode(self, location: str) -> tuple:
        """Simple geocoding using Nominatim"""
        params = {"q": location, "format": "json", "limit": 1}
        headers = {"User-Agent": "TravelAI/1.0"}
        response = requests.get(f"{self.nominatim_url}/search", params=params, headers=headers, timeout=10)
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        raise Exception(f"Could not geocode: {location}")
    
    def _get_fallback_restaurants(self, location: str) -> List[dict]:
        """Return sample restaurants when API fails"""
        return [
            {"name": f"Local Bistro - {location}", "address": f"Downtown {location}", "rating": 4.5, "types": ["local", "bistro"]},
            {"name": f"Cafe Central - {location}", "address": f"City Center, {location}", "rating": 4.3, "types": ["cafe", "breakfast"]},
            {"name": f"The Gourmet Spot", "address": f"Main Street, {location}", "rating": 4.7, "types": ["fine dining"]},
            {"name": f"Street Food Market", "address": f"Market Square, {location}", "rating": 4.2, "types": ["street food", "local"]},
            {"name": f"Rooftop Restaurant", "address": f"High Street, {location}", "rating": 4.4, "types": ["view", "dinner"]}
        ]


class OSMAttraction:
    def __init__(self, data: dict):
        tags = data.get("tags", {})
        self.name = tags.get("name", "Unknown Attraction")
        self.address = self._build_address(tags)
        self.rating = 0.0  # OSM doesn't have ratings
        self.total_ratings = 0
        self.photo_url = None
        self.location = {
            "lat": data.get("lat"),
            "lon": data.get("lon")
        }
        self.types = self._get_types(tags)
    
    def _build_address(self, tags: dict) -> str:
        parts = []
        for key in ["addr:street", "addr:housenumber", "addr:city"]:
            if tags.get(key):
                parts.append(tags[key])
        return ", ".join(parts) if parts else "Historic Center"
    
    def _get_types(self, tags: dict) -> List[str]:
        types = []
        if tags.get("tourism") == "museum":
            types.append("museum")
        if tags.get("historic"):
            types.append("historic")
        if tags.get("tourism") == "attraction":
            types.append("attraction")
        if tags.get("amenity") == "place_of_worship":
            types.append("religious site")
        if tags.get("natural"):
            types.append("natural")
        return types if types else ["attraction"]
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address": self.address,
            "rating": self.rating,
            "total_ratings": self.total_ratings,
            "photo_url": self.photo_url,
            "location": self.location,
            "types": self.types
        }


class OSMExplorerAgent:
    """Attractions/Explorer agent using OpenStreetMap - FREE"""
    
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org"
    
    def get_attractions(self, location: str) -> Dict[str, Any]:
        """Find attractions using Overpass API"""
        try:
            # Geocode location
            lat, lon = self._geocode(location)
            
            # Query for tourist attractions
            query = f"""
            [out:json][timeout:25];
            (
              node["tourism"="attraction"](around:10000,{lat},{lon});
              way["tourism"="attraction"](around:10000,{lat},{lon});
              node["tourism"="museum"](around:10000,{lat},{lon});
              way["tourism"="museum"](around:10000,{lat},{lon});
              node["historic"](around:10000,{lat},{lon});
              way["historic"](around:10000,{lat},{lon});
              node["amenity"="place_of_worship"](around:10000,{lat},{lon});
              way["amenity"="place_of_worship"](around:10000,{lat},{lon});
            );
            out body 15;
            >;
            out skel qt;
            """
            
            response = requests.post(self.overpass_url, data={"data": query}, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            attractions = []
            for element in data.get("elements", []):
                if element.get("tags") and "name" in element["tags"]:
                    attraction = OSMAttraction(element)
                    attractions.append(attraction.to_dict())
            
            # If no results, return fallback
            if not attractions:
                attractions = self._get_fallback_attractions(location)
            
            return {
                "location": location,
                "attractions": attractions[:15],
                "total_found": len(attractions),
                "provider": "OpenStreetMap"
            }
            
        except Exception as e:
            return {
                "location": location,
                "attractions": self._get_fallback_attractions(location),
                "total_found": 0,
                "provider": "OpenStreetMap (Fallback)",
                "error": str(e)
            }
    
    def _geocode(self, location: str) -> tuple:
        params = {"q": location, "format": "json", "limit": 1}
        headers = {"User-Agent": "TravelAI/1.0"}
        response = requests.get(f"{self.nominatim_url}/search", params=params, headers=headers, timeout=10)
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        raise Exception(f"Could not geocode: {location}")
    
    def _get_fallback_attractions(self, location: str) -> List[dict]:
        return [
            {"name": f"Historic City Center - {location}", "address": f"Old Town, {location}", "types": ["historic", "sightseeing"]},
            {"name": f"Central Museum", "address": f"Museum District, {location}", "types": ["museum", "culture"]},
            {"name": f"Famous Cathedral", "address": f"Cathedral Square, {location}", "types": ["religious", "architecture"]},
            {"name": f"City Park", "address": f"Green Avenue, {location}", "types": ["park", "nature"]},
            {"name": f"National Gallery", "address": f"Art District, {location}", "types": ["museum", "art"]}
        ]
