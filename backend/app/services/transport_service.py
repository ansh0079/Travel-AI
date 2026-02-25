"""
Local Transport Service
Provides information about getting around destinations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class TransportService:
    """Service for local transportation information"""
    
    def get_transport_options(self, destination: str) -> Dict[str, Any]:
        """
        Get all transport options for a destination
        
        Returns:
            Dict with public transport, taxis, rideshare, walking, etc.
        """
        transport_db = self._get_transport_database()
        
        dest_key = None
        dest_lower = destination.lower()
        
        # Try to match destination
        for key in transport_db.keys():
            if key in dest_lower:
                dest_key = key
                break
        
        if dest_key:
            return {
                "destination": destination,
                "transport_data": transport_db[dest_key],
                "source": "local_knowledge"
            }
        
        # Return general advice
        return {
            "destination": destination,
            "transport_data": self._get_general_transport_advice(),
            "source": "general"
        }
    
    def get_public_transport_info(self, destination: str) -> Dict[str, Any]:
        """Get detailed public transport information"""
        options = self.get_transport_options(destination)
        return {
            "destination": destination,
            "public_transport": options["transport_data"].get("public_transport", {})
        }
    
    def estimate_transport_costs(
        self,
        destination: str,
        duration_days: int,
        transport_mix: str = "balanced"  # public, taxi, balanced
    ) -> Dict[str, Any]:
        """Estimate daily transport costs"""
        
        # Base costs per day in USD
        cost_estimates = {
            "tokyo": {"public": 8, "taxi": 50, "balanced": 20},
            "london": {"public": 12, "taxi": 60, "balanced": 25},
            "new york": {"public": 10, "taxi": 55, "balanced": 22},
            "bangkok": {"public": 3, "taxi": 15, "balanced": 8},
            "paris": {"public": 8, "taxi": 45, "balanced": 18},
            "rome": {"public": 6, "taxi": 40, "balanced": 15},
            "default": {"public": 5, "taxi": 30, "balanced": 12}
        }
        
        dest_lower = destination.lower()
        base_costs = cost_estimates.get("default")
        
        for key, costs in cost_estimates.items():
            if key in dest_lower:
                base_costs = costs
                break
        
        daily_cost = base_costs.get(transport_mix, base_costs["balanced"])
        total_cost = daily_cost * duration_days
        
        return {
            "destination": destination,
            "duration_days": duration_days,
            "transport_mix": transport_mix,
            "daily_cost_usd": daily_cost,
            "total_cost_usd": total_cost,
            "breakdown": {
                "public_transport_per_day": base_costs["public"],
                "taxi_per_day": base_costs["taxi"]
            },
            "recommendations": self._get_cost_recommendations(destination, transport_mix)
        }
    
    def get_airport_transfers(self, destination: str, airport_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get airport to city transfer options"""
        
        transfers_db = {
            "tokyo": [
                {"type": "train", "name": "Narita Express", "duration": "60 min", "cost": "$30", "comfort": "high"},
                {"type": "bus", "name": "Airport Limousine Bus", "duration": "90 min", "cost": "$28", "comfort": "medium"},
                {"type": "taxi", "name": "Fixed Fare Taxi", "duration": "60 min", "cost": "$200", "comfort": "high"},
            ],
            "london": [
                {"type": "train", "name": "Heathrow Express", "duration": "15 min", "cost": "$32", "comfort": "high"},
                {"type": "train", "name": "Elizabeth Line", "duration": "45 min", "cost": "$15", "comfort": "medium"},
                {"type": "tube", "name": "Piccadilly Line", "duration": "50 min", "cost": "$7", "comfort": "medium"},
            ],
            "paris": [
                {"type": "train", "name": "RER B", "duration": "35 min", "cost": "$12", "comfort": "medium"},
                {"type": "bus", "name": "RoissyBus", "duration": "60 min", "cost": "$15", "comfort": "medium"},
                {"type": "taxi", "name": "Fixed Fare", "duration": "45 min", "cost": "$60", "comfort": "high"},
            ],
            "bangkok": [
                {"type": "train", "name": "Airport Rail Link", "duration": "30 min", "cost": "$1.50", "comfort": "medium"},
                {"type": "bus", "name": "Airport Bus", "duration": "60 min", "cost": "$3", "comfort": "low"},
                {"type": "taxi", "name": "Meter Taxi", "duration": "45 min", "cost": "$15-25", "comfort": "medium"},
            ],
        }
        
        dest_lower = destination.lower()
        for key, transfers in transfers_db.items():
            if key in dest_lower:
                return transfers
        
        # Default options
        return [
            {"type": "taxi", "name": "Airport Taxi", "duration": "30-60 min", "cost": "$30-50", "comfort": "medium"},
            {"type": "rideshare", "name": "Uber/Lyft", "duration": "30-60 min", "cost": "$25-40", "comfort": "medium"},
            {"type": "shuttle", "name": "Airport Shuttle", "duration": "45-90 min", "cost": "$15-25", "comfort": "low"},
        ]
    
    def get_driving_info(self, destination: str) -> Dict[str, Any]:
        """Get information about driving in a destination"""
        
        driving_db = {
            "japan": {
                "side": "left",
                "license_requirements": "International Driving Permit required",
                "difficulty": "medium",
                "notes": "Excellent public transport makes driving unnecessary in cities",
                "parking": "Expensive and scarce in city centers",
                "tolls": "Highway tolls are expensive"
            },
            "uk": {
                "side": "left",
                "license_requirements": "Foreign license valid for 12 months",
                "difficulty": "medium",
                "notes": "Congestion charge in central London",
                "parking": "Very expensive in London",
                "tolls": "Few toll roads"
            },
            "usa": {
                "side": "right",
                "license_requirements": "Foreign license generally accepted",
                "difficulty": "easy",
                "notes": "Car often necessary outside major cities",
                "parking": "Varies by city - expensive in NYC, SF",
                "tolls": "Common on highways in Northeast"
            },
            "italy": {
                "side": "right",
                "license_requirements": "International Driving Permit recommended",
                "difficulty": "hard",
                "notes": "ZTL zones in city centers - heavy fines for violations",
                "parking": "Challenging in historic centers",
                "tolls": "Extensive autostrada toll system"
            },
            "thailand": {
                "side": "left",
                "license_requirements": "International Driving Permit required",
                "difficulty": "hard",
                "notes": "Chaotic traffic, motorbikes everywhere",
                "parking": "Can be challenging",
                "tolls": "Some expressway tolls"
            }
        }
        
        dest_lower = destination.lower()
        for key, info in driving_db.items():
            if key in dest_lower:
                return {
                    "destination": destination,
                    "driving_info": info,
                    "recommendation": self._get_driving_recommendation(key)
                }
        
        return {
            "destination": destination,
            "driving_info": {
                "side": "right",
                "license_requirements": "Check local requirements",
                "difficulty": "unknown",
                "notes": "Research local driving conditions",
                "parking": "Unknown",
                "tolls": "Unknown"
            },
            "recommendation": "Research driving requirements before renting a car"
        }
    
    def get_best_transport_apps(self, destination: str) -> List[Dict[str, Any]]:
        """Get recommended transport apps for a destination"""
        
        apps_db = {
            "tokyo": [
                {"name": "Hyperdia", "type": "train", "description": "Train schedules and routes"},
                {"name": "Google Maps", "type": "all", "description": "Works well for Tokyo transit"},
                {"name": "JapanTaxi", "type": "taxi", "description": "Taxi hailing app"},
            ],
            "london": [
                {"name": "Citymapper", "type": "all", "description": "Best for London transport"},
                {"name": "TfL Oyster", "type": "transit_card", "description": "Official transport app"},
                {"name": "Uber", "type": "rideshare", "description": "Ride hailing"},
            ],
            "paris": [
                {"name": "Citymapper", "type": "all", "description": "Great for Paris navigation"},
                {"name": "Bonjour RATP", "type": "public", "description": "Official Paris transport"},
                {"name": "Uber", "type": "rideshare", "description": "Available in Paris"},
            ],
            "bangkok": [
                {"name": "Grab", "type": "rideshare", "description": "Essential for Bangkok"},
                {"name": "ViaBus", "type": "bus", "description": "Bus tracking"},
                {"name": "BTS SkyTrain", "type": "train", "description": "Official SkyTrain app"},
            ],
            "default": [
                {"name": "Google Maps", "type": "all", "description": "Works worldwide"},
                {"name": "Uber", "type": "rideshare", "description": "Available in many cities"},
                {"name": "Rome2Rio", "type": "planning", "description": "Multi-modal trip planning"},
            ]
        }
        
        dest_lower = destination.lower()
        for key, apps in apps_db.items():
            if key in dest_lower:
                return apps
        
        return apps_db["default"]
    
    def _get_transport_database(self) -> Dict[str, Any]:
        """Get detailed transport database"""
        return {
            "tokyo": {
                "overview": "World's most efficient public transport system",
                "public_transport": {
                    "available": True,
                    "quality": "excellent",
                    "options": ["JR Lines", "Tokyo Metro", "Toei Subway", "Private Railways"],
                    "recommended_pass": "JR Pass for tourists, Suica/Pasmo card for local travel",
                    "coverage": "Comprehensive - covers entire metropolitan area",
                    "frequency": "Trains every 2-5 minutes during peak",
                    "cost": "¥200-¥500 per journey",
                    "notes": "Rush hour extremely crowded (7-9 AM, 5-7 PM)"
                },
                "taxi": {
                    "available": True,
                    "quality": "excellent",
                    "cost": "Expensive - starts at ¥500, ¥400 per km",
                    "notes": "Very clean, automatic doors, can be hailed or at taxi stands"
                },
                "rideshare": {
                    "available": True,
                    "options": ["Uber (limited)", "Go Taxi"],
                    "notes": "Not as common as taxis, Go Taxi app recommended"
                },
                "walking": {
                    "viability": "excellent",
                    "notes": "Very walkable city, stations close together"
                },
                "cycling": {
                    "viability": "good",
                    "notes": "Bike rentals available, flat terrain in many areas"
                }
            },
            "london": {
                "overview": "Extensive but expensive public transport",
                "public_transport": {
                    "available": True,
                    "quality": "very_good",
                    "options": ["Tube", "Bus", "Overground", "DLR", "Elizabeth Line"],
                    "recommended_pass": "Oyster card or contactless payment",
                    "coverage": "Excellent within zones 1-6",
                    "frequency": "Tube every 2-10 minutes",
                    "cost": "£2.50-£6 per journey",
                    "notes": "Very expensive without Oyster/contactless"
                },
                "taxi": {
                    "available": True,
                    "quality": "very_good",
                    "cost": "Expensive - £10-£30 for central journeys",
                    "notes": "Black cabs are iconic but pricey"
                },
                "rideshare": {
                    "available": True,
                    "options": ["Uber", "Bolt", "Free Now"],
                    "notes": "Widely used, often cheaper than black cabs"
                },
                "walking": {
                    "viability": "very_good",
                    "notes": "Central London very walkable"
                }
            },
            "paris": {
                "overview": "Metro-centric transport, very walkable center",
                "public_transport": {
                    "available": True,
                    "quality": "very_good",
                    "options": ["Metro", "RER", "Bus", "Tram"],
                    "recommended_pass": "Navigo Easy card or weekly pass",
                    "coverage": "Excellent within city center",
                    "frequency": "Metro every 2-8 minutes",
                    "cost": "€1.90-€7.50 per journey",
                    "notes": "Metro closes around 2 AM (5 AM on weekends)"
                },
                "taxi": {
                    "available": True,
                    "quality": "good",
                    "cost": "Moderate - €10-€20 for central journeys",
                    "notes": "Can be hailed or at stands"
                },
                "rideshare": {
                    "available": True,
                    "options": ["Uber", "Bolt", "Free Now"],
                    "notes": "Widely available"
                },
                "walking": {
                    "viability": "excellent",
                    "notes": "Paris is very walkable, beautiful strolls"
                }
            },
            "bangkok": {
                "overview": "Mix of modern transit and chaotic traffic",
                "public_transport": {
                    "available": True,
                    "quality": "mixed",
                    "options": ["BTS SkyTrain", "MRT Subway", "Airport Link", "Bus", "Boat"],
                    "recommended_pass": "Rabbit card for BTS",
                    "coverage": "Limited - doesn't cover all areas",
                    "frequency": "Trains every 3-7 minutes",
                    "cost": "15-65 THB per journey",
                    "notes": "BTS/MRT don't connect well, traffic terrible 7-10 AM, 4-8 PM"
                },
                "taxi": {
                    "available": True,
                    "quality": "mixed",
                    "cost": "Cheap - 35 THB base, 5-10 THB per km",
                    "notes": "Insist on meter, some refuse tourists"
                },
                "rideshare": {
                    "available": True,
                    "options": ["Grab"],
                    "notes": "Grab dominates, often better than taxis"
                },
                "walking": {
                    "viability": "poor",
                    "notes": "Sidewalks often blocked, hot and humid"
                },
                "motorcycle_taxi": {
                    "available": True,
                    "quality": "good",
                    "cost": "Very cheap",
                    "notes": "Fast through traffic, negotiate price first"
                }
            }
        }
    
    def _get_general_transport_advice(self) -> Dict[str, Any]:
        """Get general transport advice for unknown destinations"""
        return {
            "overview": "Research local transport options before arrival",
            "public_transport": {
                "available": True,
                "quality": "varies",
                "options": ["Research local options"],
                "recommended_pass": "Check for tourist passes",
                "notes": "Often the cheapest way to get around"
            },
            "taxi": {
                "available": True,
                "quality": "varies",
                "notes": "Use official taxis, insist on meter or agree price"
            },
            "rideshare": {
                "available": True,
                "options": ["Uber"],
                "notes": "Check availability in your destination"
            },
            "walking": {
                "viability": "varies",
                "notes": "Often the best way to explore city centers"
            }
        }
    
    def _get_cost_recommendations(self, destination: str, transport_mix: str) -> List[str]:
        """Get recommendations based on cost preferences"""
        recommendations = []
        
        if transport_mix == "public":
            recommendations.append("Use day passes for unlimited travel")
            recommendations.append("Walk when possible - free and healthy!")
        elif transport_mix == "taxi":
            recommendations.append("Use rideshare apps - often cheaper than taxis")
            recommendations.append("Share rides with other travelers when possible")
        else:  # balanced
            recommendations.append("Use public transport for long distances")
            recommendations.append("Use taxis/rideshare for short trips or late nights")
        
        return recommendations
    
    def _get_driving_recommendation(self, country: str) -> str:
        """Get driving recommendation for a country"""
        recommendations = {
            "japan": "Not recommended for tourists - public transport is excellent",
            "uk": "Avoid in London - congestion charge + expensive parking",
            "usa": "Often necessary - rent a car for road trips",
            "italy": "Avoid in cities - ZTL zones, use for countryside only",
            "thailand": "Not recommended - chaotic traffic, cheap alternatives available"
        }
        return recommendations.get(country, "Research local conditions before deciding")


# Convenience function
def get_transport_guide(destination: str, duration_days: int = 7) -> Dict[str, Any]:
    """Get comprehensive transport guide"""
    service = TransportService()
    
    return {
        "destination": destination,
        "transport_options": service.get_transport_options(destination),
        "cost_estimate": service.estimate_transport_costs(destination, duration_days),
        "airport_transfers": service.get_airport_transfers(destination),
        "driving_info": service.get_driving_info(destination),
        "recommended_apps": service.get_best_transport_apps(destination)
    }
