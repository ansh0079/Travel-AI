"""
City Details API Routes
Provides comprehensive information about individual cities/destinations
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

from app.services.weather_service import WeatherService
from app.services.visa_service import VisaService
from app.services.attractions_service import AttractionsService
from app.services.events_service import EventsService
from app.services.affordability_service import AffordabilityService
from app.services.flight_service import FlightService
from app.services.hotel_service import HotelService
from app.services.restaurants_service import RestaurantsService
from app.services.transport_service import TransportService, get_transport_guide
from app.services.nightlife_service import NightlifeService
from app.services.agent_service import TravelResearchAgent

router = APIRouter(prefix="/api/v1/cities", tags=["cities"])

# Initialize services
weather_service = WeatherService()
visa_service = VisaService()
attractions_service = AttractionsService()
events_service = EventsService()
affordability_service = AffordabilityService()
flight_service = FlightService()
hotel_service = HotelService()
restaurants_service = RestaurantsService()
transport_service = TransportService()
nightlife_service = NightlifeService()
web_agent = TravelResearchAgent()


# ============ Response Models ============

class CityOverview(BaseModel):
    name: str
    country: str
    description: str
    best_time_to_visit: str
    language: str
    currency: str
    time_zone: str
    emergency_number: str


class CityWeather(BaseModel):
    current_temp: Optional[float]
    condition: str
    humidity: Optional[int]
    forecast: List[dict]
    best_time_to_visit: str
    climate_overview: str


class CityFlights(BaseModel):
    from_origin: Optional[str]
    cheapest_price: Optional[float]
    duration_hours: Optional[float]
    airlines: List[str]
    flight_options: List[dict]


class CityAttractions(BaseModel):
    top_attractions: List[dict]
    categories: List[str]
    total_count: int


class CityEvents(BaseModel):
    upcoming_events: List[dict]
    festivals: List[dict]
    total_count: int


class CityHotels(BaseModel):
    price_range: dict
    top_rated: List[dict]
    budget_options: List[dict]
    luxury_options: List[dict]


class CityRestaurants(BaseModel):
    must_try_dishes: List[str]
    top_restaurants: List[dict]
    food_scene: str
    price_range: str


class CityTransport(BaseModel):
    from_airport: dict
    public_transport: dict
    taxi_rideshare: dict
    recommended_pass: str
    metro_lines: Optional[List[dict]]
    bus_network: Optional[dict]
    cab_companies: Optional[List[dict]]
    bike_scooter: Optional[dict]
    walking_info: Optional[dict]
    transport_apps: Optional[List[str]]
    payment_methods: Optional[List[str]]


class CityCosts(BaseModel):
    budget_daily: float
    moderate_daily: float
    luxury_daily: float
    meal_average: float
    transport_average: float


class CityVisa(BaseModel):
    visa_required: bool
    visa_type: Optional[str]
    duration: Optional[str]
    cost: Optional[str]
    processing_time: Optional[str]


class CityDetailsResponse(BaseModel):
    overview: CityOverview
    weather: CityWeather
    flights: CityFlights
    attractions: CityAttractions
    events: CityEvents
    hotels: CityHotels
    restaurants: CityRestaurants
    transport: CityTransport
    costs: CityCosts
    visa: CityVisa
    tips: List[str]
    weather_alerts: List[str]
    images: dict  # City images (hero, gallery, etc.)


# ============ Mock Data for Cities ============

CITY_DATABASE = {
    "paris": {
        "name": "Paris",
        "country": "France",
        "description": "The City of Light, famous for its art, fashion, gastronomy, and culture.",
        "best_time_to_visit": "April to June, September to November",
        "language": "French",
        "currency": "Euro (€)",
        "time_zone": "CET (UTC+1)",
        "emergency_number": "112",
        "lat": 48.8566,
        "lon": 2.3522,
        "images": {
            "hero": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1200",
            "gallery": [
                "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=600",
                "https://images.unsplash.com/photo-1511739001486-6bfe10ce7859?w=600",
                "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=600",
                "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=600",
            ],
            "attractions": {
                "Eiffel Tower": "https://images.unsplash.com/photo-1511739001486-6bfe10ce7859?w=400",
                "Louvre Museum": "https://images.unsplash.com/photo-1566139884357-1f7c5b4845ba?w=400",
                "Notre-Dame": "https://images.unsplash.com/photo-1478391679764-b2d8b3cd7e33?w=400",
                "Arc de Triomphe": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400",
                "Sacré-Cœur": "https://images.unsplash.com/photo-1599707367072-cd6c6c272376?w=400",
                "Musée d'Orsay": "https://images.unsplash.com/photo-1563789031959-4c02bcb40319?w=400",
            }
        },
        "tips": [
            "Get a Paris Museum Pass for skip-the-line access",
            "Learn basic French phrases - locals appreciate the effort",
            "Many museums are free on first Sundays of the month",
            "Metro runs until 2:15 AM (3:15 AM on weekends)",
            "Book Eiffel Tower tickets well in advance"
        ],
        "transport": {
            "metro_lines": [
                {"line": "M1", "color": "yellow", "route": "La Défense ↔ Château de Vincennes", "key_stops": ["Arc de Triomphe", "Louvre", "Châtelet"]},
                {"line": "M2", "color": "blue", "route": "Porte Dauphine ↔ Nation", "key_stops": ["Sacré-Cœur", "Pigalle"]},
                {"line": "M4", "color": "purple", "route": "Porte de Clignancourt ↔ Bagneux", "key_stops": ["Gare du Nord", "Châtelet", "Montparnasse"]},
                {"line": "M6", "color": "green", "route": "Charles de Gaulle-Étoile ↔ Nation", "key_stops": ["Eiffel Tower", "Montparnasse"]},
                {"line": "M9", "color": "green_light", "route": "Pont de Sèvres ↔ Mairie de Montreuil", "key_stops": ["Trocadéro", "Grands Boulevards"]}
            ],
            "bus_network": {
                "coverage": "Extensive day and night bus network (Noctilien)",
                "day_hours": "5:30 AM - 12:30 AM",
                "night_hours": "12:30 AM - 5:30 AM (reduced frequency)",
                "key_routes": ["38 (Gare du Nord-Luxembourg)", "63 (Gare Lyon-Trocadéro)", "87 (Champ de Mars-Louvre)"],
                "cost": "€2.10 single ticket, €17.80 (Navigo Weekly)"
            },
            "cab_companies": [
                {"name": "Taxi G7", "phone": "+33 1 47 39 47 39", "app": "G7 Taxi", "features": "Largest fleet, wheelchair accessible"},
                {"name": "Taxi Bleu", "phone": "+33 1 49 36 10 10", "app": "Taxi Bleu", "features": "Premium service, airport specialists"},
                {"name": "Uber", "app": "Uber", "features": "Cashless, track your ride"},
                {"name": "Bolt", "app": "Bolt", "features": "Often cheaper than Uber"},
                {"name": "Free Now", "app": "Free Now", "features": "Licensed taxis + rideshare"}
            ],
            "transport_apps": ["Citymapper", "Bonjour RATP", "Google Maps", "Uber", "Bolt"],
            "payment_methods": ["Contactless card", "Navigo card", "Metro tickets (t+)", "Cash (taxis only)"],
            "bike_scooter": {
                "vlib": "City bike rental (€5/day)",
                "lime_tier": "E-scooters available via apps",
                "cycling": "750km of bike lanes, Véligo long-term rental"
            },
            "walking_info": {
                "walkability": "Excellent",
                "pedestrian_zones": "Les Halles, Montmartre, Marais",
                "walking_tours": "Free walking tours available"
            }
        }
    },
    "tokyo": {
        "name": "Tokyo",
        "country": "Japan",
        "description": "A dazzling mix of traditional culture and futuristic technology.",
        "best_time_to_visit": "March to May, October to November",
        "language": "Japanese",
        "currency": "Japanese Yen (¥)",
        "time_zone": "JST (UTC+9)",
        "emergency_number": "110 (Police), 119 (Fire/Ambulance)",
        "lat": 35.6762,
        "lon": 139.6503,
        "images": {
            "hero": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1200",
            "gallery": [
                "https://images.unsplash.com/photo-1536098561742-ca998e48cbcc?w=600",
                "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=600",
                "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=600",
                "https://images.unsplash.com/photo-1542051841857-5f90071e7989?w=600",
            ],
            "attractions": {
                "Senso-ji Temple": "https://images.unsplash.com/photo-1536098561742-ca998e48cbcc?w=400",
                "Tokyo Tower": "https://images.unsplash.com/photo-1532236204323-e1d854524256?w=400",
                "Shibuya Crossing": "https://images.unsplash.com/photo-1542051841857-5f90071e7989?w=400",
                "Meiji Shrine": "https://images.unsplash.com/photo-1528360983277-13d401cdc186?w=400",
                "TeamLab Planets": "https://images.unsplash.com/photo-1570459027562-4a916cc6113f?w=400",
                "Tsukiji Outer Market": "https://images.unsplash.com/photo-1554797589-7241bb691973?w=400",
            }
        },
        "tips": [
            "Get a Suica or Pasmo card for easy transport",
            "Many restaurants have plastic food displays outside",
            "Convenience stores (konbini) have excellent food",
            "Don't tip - it's not customary in Japan",
            "Bow when greeting or thanking people"
        ],
        "transport": {
            "metro_lines": [
                {"line": "JR Yamanote", "color": "green", "route": "Circular loop", "key_stops": ["Shibuya", "Shinjuku", "Tokyo Station", "Ueno", "Harajuku"]},
                {"line": "Metro Ginza", "color": "orange", "route": "Asakusa ↔ Shibuya", "key_stops": ["Ginza", "Shimbashi", "Asakusa"]},
                {"line": "Metro Marunouchi", "color": "red", "route": "Ogikubo ↔ Ikebukuro", "key_stops": ["Tokyo Station", "Ginza", "Shinjuku"]},
                {"line": "Metro Hibiya", "color": "silver", "route": "Naka-Meguro ↔ Kita-Senju", "key_stops": ["Roppongi", "Ginza", "Akihabara"]},
                {"line": "Metro Oedo", "color": "purple", "route": "Tocho-mae ↔ Hikarigaoka", "key_stops": ["Shinjuku", "Roppongi", "Tsukiji"]}
            ],
            "bus_network": {
                "coverage": "Extensive Toei Bus network",
                "day_hours": "5:00 AM - 12:00 AM",
                "night_hours": "Limited night buses",
                "key_routes": ["Hato Bus (sightseeing)", "Airport Limousine", "Tokyo Bus"],
                "cost": "¥210 flat fare, ¥500 day pass"
            },
            "cab_companies": [
                {"name": "Nihon Kotsu", "phone": "+81 3-5755-2336", "app": "Go Taxi", "features": "Largest fleet, English available"},
                {"name": "Tokyo Musen", "phone": "+81 3-3498-1111", "app": "Go Taxi", "features": "Wheelchair accessible"},
                {"name": "Uber", "app": "Uber", "features": "Premium black cars only"},
                {"name": "Go Taxi", "app": "Go Taxi", "features": "Most popular, includes taxis"},
                {"name": "S.Ride", "app": "S.Ride", "features": "Quick pickup, English UI"}
            ],
            "transport_apps": ["Google Maps", "Hyperdia", "Japan Transit Planner", "Suica/Pasmo app", "Go Taxi"],
            "payment_methods": ["Suica/Pasmo IC card", "Contactless card", "Cash", "Apple Pay/Google Pay"],
            "bike_scooter": {
                "docomo": "Docomo Bike Share (¥165/30min)",
                "luup": "E-scooters and bikes",
                "notes": "Cycling on sidewalks allowed, helmets recommended"
            },
            "walking_info": {
                "walkability": "Excellent",
                "pedestrian_zones": "Ginza (weekends), Shibuya Crossing area",
                "walking_tours": "Free walking tours in Asakusa, Harajuku"
            }
        }
    },
    "bali": {
        "name": "Bali",
        "country": "Indonesia",
        "description": "Tropical paradise with stunning beaches, temples, and vibrant culture.",
        "best_time_to_visit": "April to October (dry season)",
        "language": "Indonesian, Balinese",
        "currency": "Indonesian Rupiah (IDR)",
        "time_zone": "WITA (UTC+8)",
        "emergency_number": "112",
        "lat": -8.4095,
        "lon": 115.1889,
        "images": {
            "hero": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=1200",
            "gallery": [
                "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=600",
                "https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=600",
                "https://images.unsplash.com/photo-1573790387438-4da905039392?w=600",
                "https://images.unsplash.com/photo-1539367628448-4bc5c9d171c8?w=600",
            ],
            "attractions": {
                "Tanah Lot Temple": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=400",
                "Uluwatu Temple": "https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=400",
                "Sacred Monkey Forest": "https://images.unsplash.com/photo-1573790387438-4da905039392?w=400",
                "Tegallalang Rice Terraces": "https://images.unsplash.com/photo-1539367628448-4bc5c9d171c8?w=400",
                "Nusa Penida": "https://images.unsplash.com/photo-1598324789736-4861f89564a0?w=400",
                "Seminyak Beach": "https://images.unsplash.com/photo-1559628233-100c798642d4?w=400",
            }
        },
        "tips": [
            "Rent a scooter for easiest transportation",
            "Respect local customs at temples (cover shoulders and knees)",
            "Bargain at markets - start at 50% of asking price",
            "Drink only bottled or filtered water",
            "Sunset at Tanah Lot is a must-see"
        ],
        "transport": {
            "metro_lines": [],
            "bus_network": {
                "coverage": "Limited public bus network",
                "day_hours": "6:00 AM - 9:00 PM",
                "night_hours": "Limited night service",
                "key_routes": ["Kura-Kura Bus (tourist areas)", "Trans Sarbagita (Denpasar area)", "Shuttle buses between towns"],
                "cost": "Rp 5,000 - 20,000 per trip"
            },
            "cab_companies": [
                {"name": "Blue Bird Taxi", "phone": "+62 361 701111", "app": "My Blue Bird", "features": "Metered, reliable, largest fleet"},
                {"name": "Grab", "app": "Grab", "features": "Fixed prices, cash/card, widely available"},
                {"name": "Gojek", "app": "Gojek", "features": "Most popular, bikes and cars"},
                {"name": "Uber", "app": "Uber", "features": "Limited availability"},
                {"name": "Private Drivers", "app": "WhatsApp", "features": "Day hire ~Rp 500,000-700,000"}
            ],
            "transport_apps": ["Gojek", "Grab", "Google Maps", "My Blue Bird"],
            "payment_methods": ["Cash (IDR)", "Gojek/Grab credit", "Credit card (limited)"],
            "bike_scooter": {
                "rental": "Scooter rental ~Rp 60,000-80,000/day",
                "gojek_bike": "Bike taxi (ojek) via app",
                "notes": "International driving permit required for scooters"
            },
            "walking_info": {
                "walkability": "Limited - not pedestrian friendly",
                "pedestrian_zones": "Ubud town center, Seminyak beach walk",
                "notes": "Walk on sidewalks where available, watch for scooters"
            }
        }
    },
    "london": {
        "name": "London",
        "country": "United Kingdom",
        "description": "Historic city blending royal tradition with modern multicultural vibrancy.",
        "best_time_to_visit": "May to September",
        "language": "English",
        "currency": "British Pound (£)",
        "time_zone": "GMT (UTC+0)",
        "emergency_number": "999",
        "lat": 51.5074,
        "lon": -0.1278,
        "images": {
            "hero": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=1200",
            "gallery": [
                "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=600",
                "https://images.unsplash.com/photo-1505761671935-60b3a7427bad?w=600",
                "https://images.unsplash.com/photo-1529655683826-aba9b3e77383?w=600",
                "https://images.unsplash.com/photo-1533929736562-6a4c4f30e49c?w=600",
            ],
            "attractions": {
                "Big Ben": "https://images.unsplash.com/photo-1529655683826-aba9b3e77383?w=400",
                "Tower Bridge": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=400",
                "Buckingham Palace": "https://images.unsplash.com/photo-1549488497-0b45630b94b3?w=400",
                "London Eye": "https://images.unsplash.com/photo-1533929736562-6a4c4f30e49c?w=400",
                "British Museum": "https://images.unsplash.com/photo-1565060169194-1d6d84435e8b?w=400",
                "Tower of London": "https://images.unsplash.com/photo-1533856493584-0cdef1e8e2f0?w=400",
            }
        },
        "tips": [
            "Get an Oyster card or use contactless payment",
            "Many museums are free including British Museum",
            "Stand on the right side of escalators",
            "Pubs stop serving food at 9 PM in many places",
            "Book Westminster Abbey tickets in advance"
        ],
        "transport": {
            "metro_lines": [
                {"line": "Central", "color": "red", "route": "Ealing Broadway ↔ Epping", "key_stops": ["Notting Hill", "Oxford Circus", "Bank", "Liverpool Street"]},
                {"line": "Piccadilly", "color": "dark_blue", "route": "Uxbridge ↔ Cockfosters", "key_stops": ["Heathrow", "South Kensington", "Piccadilly Circus", "King's Cross"]},
                {"line": "Northern", "color": "black", "route": "High Barnet/Edgware ↔ Morden", "key_stops": ["Camden Town", "Leicester Square", "London Bridge", "Battersea"]},
                {"line": "Jubilee", "color": "silver", "route": "Stanmore ↔ Stratford", "key_stops": ["Bond Street", "Westminster", "London Bridge", "Canary Wharf"]},
                {"line": "Circle/District", "color": "yellow/green", "route": "Circular routes", "key_stops": ["Victoria", "Tower Hill", "South Kensington"]}
            ],
            "bus_network": {
                "coverage": "Extensive 24-hour bus network",
                "day_hours": "24 hours",
                "night_hours": "Night buses (N-prefixed routes)",
                "key_routes": ["RV1 (South Bank)", "11 (Chelsea-Liverpool St)", "15 (Tower Hill-Westminster)"],
                "cost": "£1.75 single, £5.25 daily cap, Hopper fare (2nd ride free within 1hr)"
            },
            "cab_companies": [
                {"name": "Black Cabs (Hackney Carriage)", "phone": "None - hail on street", "app": "Gett", "features": "Licensed, can use bus lanes, metered"},
                {"name": "Addison Lee", "phone": "+44 20 7387 8888", "app": "Addison Lee", "features": "Premium minicabs, pre-booked"},
                {"name": "Uber", "app": "Uber", "features": "Widely available, cashless"},
                {"name": "Bolt", "app": "Bolt", "features": "Often cheaper alternatives"},
                {"name": "Free Now", "app": "Free Now", "features": "Black cabs + private hire"}
            ],
            "transport_apps": ["Citymapper", "TfL Oyster", "Uber", "Gett (Black cabs)", "Google Maps"],
            "payment_methods": ["Contactless card", "Oyster card", "Apple/Google Pay", "Cash (buses only, no change)"],
            "bike_scooter": {
                "santander": "Santander Cycles (Boris Bikes) £1.65/30min",
                "lime": "E-scooters in trial areas",
                "notes": "Extensive cycling lanes, cycle superhighways"
            },
            "walking_info": {
                "walkability": "Excellent",
                "pedestrian_zones": "Oxford Street, Covent Garden, South Bank",
                "walking_tours": "Free walking tours daily"
            }
        }
    },
    "new york": {
        "name": "New York City",
        "country": "USA",
        "description": "The city that never sleeps, famous for skyline, culture, and diversity.",
        "best_time_to_visit": "April to June, September to November",
        "language": "English",
        "currency": "US Dollar ($)",
        "time_zone": "EST (UTC-5)",
        "emergency_number": "911",
        "lat": 40.7128,
        "lon": -74.0060,
        "images": {
            "hero": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=1200",
            "gallery": [
                "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=600",
                "https://images.unsplash.com/photo-1522083165195-3424ed129620?w=600",
                "https://images.unsplash.com/photo-1499092346589-b9b6be3e94b2?w=600",
                "https://images.unsplash.com/photo-1534270804882-6b5048b1c1fc?w=600",
            ],
            "attractions": {
                "Statue of Liberty": "https://images.unsplash.com/photo-1605130284535-11dd9eedc58a?w=400",
                "Times Square": "https://images.unsplash.com/photo-1534270804882-6b5048b1c1fc?w=400",
                "Central Park": "https://images.unsplash.com/photo-1534430480872-3498386e7856?w=400",
                "Empire State Building": "https://images.unsplash.com/photo-1550664776-3a802f6e6e7d?w=400",
                "Brooklyn Bridge": "https://images.unsplash.com/photo-1522083165195-3424ed129620?w=400",
                "One World Trade Center": "https://images.unsplash.com/photo-1485871981535-5be48f351dfc?w=400",
            }
        },
        "tips": [
            "Get a MetroCard for subway and buses",
            "Walk or bike in Central Park on weekends (closed to cars)",
            "Many Broadway shows have discount TKTS booths",
            "Tipping 15-20% is expected at restaurants",
            "Walk the High Line for unique city views"
        ],
        "transport": {
            "metro_lines": [
                {"line": "1/2/3 (Red)", "color": "red", "route": "North-South Manhattan/Bronx", "key_stops": ["Times Square", "Columbus Circle", "Wall Street"]},
                {"line": "4/5/6 (Green)", "color": "green", "route": "East Side Manhattan/Bronx", "key_stops": ["Grand Central", "Union Square", "Brooklyn Bridge"]},
                {"line": "N/Q/R/W (Yellow)", "color": "yellow", "route": "Broadway Line", "key_stops": ["Times Square", "Herald Square", "Canal Street"]},
                {"line": "A/C/E (Blue)", "color": "blue", "route": "8th Avenue Line", "key_stops": ["Penn Station", "Port Authority", "World Trade Center"]},
                {"line": "L (Grey)", "color": "grey", "route": "14th Street-Canarsie", "key_stops": ["Union Square", "Bedford Avenue (Williamsburg)"]}
            ],
            "bus_network": {
                "coverage": "Extensive MTA bus network",
                "day_hours": "24 hours",
                "night_hours": "Overnight buses",
                "key_routes": ["M5 (Staten Island ferry)", "M20 (Central Park)", "Select Bus Service (SBS)"],
                "cost": "$2.90 (MetroCard/OMNY), free transfer within 2hrs"
            },
            "cab_companies": [
                {"name": "Yellow Cab", "phone": "311 or hail", "app": "NYC Taxi & Limousine", "features": "Street hail, metered, iconic"},
                {"name": "Green Cab", "phone": "311 or hail", "features": "Outer boroughs, metered"},
                {"name": "Uber", "app": "Uber", "features": "Widely available"},
                {"name": "Lyft", "app": "Lyft", "features": "Competitive pricing"},
                {"name": "Via", "app": "Via", "features": "Shared rides, cheaper"}
            ],
            "transport_apps": ["Citymapper", "MTA", "Google Maps", "Uber", "Lyft", "Citi Bike"],
            "payment_methods": ["MetroCard", "OMNY (contactless)", "Apple/Google Pay", "Cash", "Credit card"],
            "bike_scooter": {
                "citi_bike": "Citi Bike (bike share) $4.49/30min",
                "revel": "Revel mopeds (license required)",
                "notes": "Protected bike lanes, Central Park loop"
            },
            "walking_info": {
                "walkability": "Excellent - grid system",
                "pedestrian_zones": "Times Square, Herald Square, Meatpacking District",
                "walking_tours": "Free walking tours in all boroughs"
            }
        }
    }
}


# ============ API Endpoints ============

@router.get("/{city_name}/details", response_model=CityDetailsResponse)
async def get_city_details(
    city_name: str,
    origin: Optional[str] = Query(None, description="Origin city for flight prices"),
    travel_start: Optional[str] = Query(None, description="Travel start date (YYYY-MM-DD)"),
    travel_end: Optional[str] = Query(None, description="Travel end date (YYYY-MM-DD)"),
    passport_country: str = Query("US", description="Passport country for visa info"),
    budget_level: str = Query("moderate", description="Budget level: low, moderate, high, luxury")
):
    """
    Get comprehensive details for a specific city.
    
    Includes: overview, weather, flights, attractions, events, hotels, 
    restaurants, transport, costs, and visa information.
    """
    # Normalize city name
    city_key = city_name.lower().replace(" ", "").replace(",", "").split("and")[0].strip()
    
    # Get base city data or use defaults
    city_data = CITY_DATABASE.get(city_key, {
        "name": city_name.title(),
        "country": "Unknown",
        "description": f"Beautiful destination with rich culture and attractions.",
        "best_time_to_visit": "Spring and Fall",
        "language": "Local",
        "currency": "Local Currency",
        "time_zone": "Local Time",
        "emergency_number": "112",
        "lat": 48.8566,
        "lon": 2.3522,
        "tips": [
            "Research local customs before visiting",
            "Learn a few basic phrases in the local language",
            "Keep copies of important documents",
            "Respect local dress codes at religious sites"
        ],
        "transport": {
            "metro_lines": [
                {"line": "Line 1", "color": "blue", "route": "City Center ↔ Suburbs", "key_stops": ["Central Station", "City Hall", "Museum District"]}
            ],
            "bus_network": {
                "coverage": "City-wide bus network",
                "day_hours": "6:00 AM - 11:00 PM",
                "night_hours": "Limited night service",
                "key_routes": ["Route 1 (City Center)", "Route 2 (Airport)"],
                "cost": "Local currency - check locally"
            },
            "cab_companies": [
                {"name": "Local Taxi", "phone": "Check locally", "features": "Metered taxis available"},
                {"name": "Uber", "app": "Uber", "features": "Available in most cities"},
                {"name": "Bolt", "app": "Bolt", "features": "Alternative rideshare option"}
            ],
            "transport_apps": ["Google Maps", "Citymapper", "Uber", "Local transport app"],
            "payment_methods": ["Cash", "Credit card", "Contactless payment"],
            "bike_scooter": {
                "rental": "Bike rentals available near tourist areas",
                "notes": "Ask at your hotel for recommendations"
            },
            "walking_info": {
                "walkability": "Varies by area",
                "notes": "City center usually pedestrian-friendly"
            }
        }
    })
    
    # Get coordinates
    lat = city_data.get("lat", 48.8566)
    lon = city_data.get("lon", 2.3522)
    
    try:
        # 1. Weather
        weather = await _get_city_weather(city_data["name"], travel_start)
        
        # 2. Flights
        flights = await _get_city_flights(city_data["name"], origin, travel_start)
        
        # 3. Attractions
        attractions = await attractions_service.get_all_attractions(lat, lon, limit=10)
        
        # 4. Events
        start_date = datetime.strptime(travel_start, "%Y-%m-%d").date() if travel_start else datetime.now().date()
        end_date = datetime.strptime(travel_end, "%Y-%m-%d").date() if travel_end else datetime.now().date()
        events = await events_service.get_events(city_data["name"], start_date, end_date)
        
        # 5. Hotels
        check_in_date = datetime.strptime(travel_start, "%Y-%m-%d").date() if travel_start else datetime.now().date()
        check_out_date = datetime.strptime(travel_end, "%Y-%m-%d").date() if travel_end else datetime.now().date()
        hotels = await hotel_service.search_hotels(
            city=city_data["name"],
            check_in=check_in_date,
            check_out=check_out_date,
            adults=2
        )
        
        # 6. Restaurants
        restaurants_data = restaurants_service.get_restaurants(
            destination=city_data["name"],
            cuisine_types=["local"],
            budget_level=budget_level
        )
        food_scene = restaurants_service.get_food_scene(city_data["name"])
        
        # 7. Transport
        transport = get_transport_guide(city_data["name"], duration_days=7)
        
        # 8. Costs
        affordability = await affordability_service.get_affordability(
            country_code=city_data["country"][:2].upper() if city_data["country"] else "US",
            travel_style=budget_level
        )
        
        # 9. Visa
        visa_info = await visa_service.get_visa_requirements(passport_country, city_data["country"])
        
        # Build response
        return CityDetailsResponse(
            overview=CityOverview(
                name=city_data["name"],
                country=city_data["country"],
                description=city_data["description"],
                best_time_to_visit=city_data["best_time_to_visit"],
                language=city_data["language"],
                currency=city_data["currency"],
                time_zone=city_data["time_zone"],
                emergency_number=city_data["emergency_number"]
            ),
            weather=weather,
            flights=flights,
            attractions=CityAttractions(
                top_attractions=[
                    {
                        "name": a.name,
                        "description": a.description,
                        "category": a.type,
                        "rating": a.rating,
                        "price_level": f"${a.entry_fee:.0f}" if a.entry_fee else "Free",
                        "location": a.location
                    }
                    for a in attractions[:10]
                ],
                categories=list(set(a.type for a in attractions)),
                total_count=len(attractions)
            ),
            events=CityEvents(
                upcoming_events=[
                    {
                        "name": e.name,
                        "date": e.date.isoformat() if e.date else "",
                        "type": e.type.value if e.type else "event",
                        "description": e.description or ""
                    }
                    for e in events[:5]
                ],
                festivals=[
                    {
                        "name": e.name,
                        "date": e.date.isoformat() if e.date else "",
                        "type": e.type.value if e.type else "festival",
                        "description": e.description or ""
                    }
                    for e in events[:3]
                ],
                total_count=len(events)
            ),
            hotels=_format_hotels(hotels, budget_level),
            restaurants=CityRestaurants(
                must_try_dishes=food_scene.get("food_scene", {}).get("signature_dishes", [])[:5],
                top_restaurants=restaurants_data[:5],
                food_scene=food_scene.get("food_scene", {}).get("description", "Delicious local cuisine"),
                price_range="$" if budget_level == "low" else "$$" if budget_level == "moderate" else "$$$"
            ),
            transport=CityTransport(
                from_airport=transport.get("airport_transfer", {}),
                public_transport=transport.get("public_transport", {}),
                taxi_rideshare=transport.get("taxi_rideshare", {}),
                recommended_pass=transport.get("recommended_pass", "Check local options"),
                metro_lines=city_data.get("transport", {}).get("metro_lines"),
                bus_network=city_data.get("transport", {}).get("bus_network"),
                cab_companies=city_data.get("transport", {}).get("cab_companies"),
                bike_scooter=city_data.get("transport", {}).get("bike_scooter"),
                walking_info=city_data.get("transport", {}).get("walking_info"),
                transport_apps=city_data.get("transport", {}).get("transport_apps"),
                payment_methods=city_data.get("transport", {}).get("payment_methods")
            ),
            costs=CityCosts(
                budget_daily=affordability.daily_cost_estimate * 0.7 if affordability.cost_level == "budget" else affordability.daily_cost_estimate * 0.8,
                moderate_daily=affordability.daily_cost_estimate,
                luxury_daily=affordability.daily_cost_estimate * 2.5,
                meal_average=affordability.food_avg,
                transport_average=affordability.transport_avg
            ),
            visa=CityVisa(
                visa_required=visa_info.required,
                visa_type=visa_info.type,
                duration=f"{visa_info.visa_free_days} days" if visa_info.visa_free_days else None,
                cost=f"${visa_info.cost_usd}" if visa_info.cost_usd else None,
                processing_time=f"{visa_info.processing_days} days" if visa_info.processing_days else None
            ),
            tips=city_data["tips"],
            weather_alerts=[],
            images=city_data.get("images", {
                "hero": "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1200",
                "gallery": [
                    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=600",
                    "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=600",
                ],
                "attractions": {}
            })
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching city details: {str(e)}")


@router.get("/{city_name}/flights")
async def get_city_flights(
    city_name: str,
    origin: str = Query(..., description="Origin city (required)"),
    departure_date: Optional[str] = Query(None, description="Departure date (YYYY-MM-DD)"),
    return_date: Optional[str] = Query(None, description="Return date (YYYY-MM-DD)")
):
    """Get flight options to a specific city from an origin."""
    flights = flight_service.search_flights(
        origin=origin,
        destination=city_name,
        departure_date=departure_date or datetime.now().strftime("%Y-%m-%d"),
        return_date=return_date,
        passengers=1
    )
    return {
        "city": city_name,
        "origin": origin,
        "flights": flights,
        "cheapest": min((f.get("price", 9999) for f in flights), default=None),
        "airlines": list(set(f.get("airline", "") for f in flights))
    }


@router.get("/{city_name}/attractions")
async def get_city_attractions(
    city_name: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    interests: Optional[List[str]] = Query(None, description="Filter by interests")
):
    """Get attractions for a specific city."""
    city_key = city_name.lower().replace(" ", "")
    city_data = CITY_DATABASE.get(city_key, {"lat": 48.8566, "lon": 2.3522})
    
    attractions = attractions_service.get_attractions(
        city_data.get("lat", 48.8566),
        city_data.get("lon", 2.3522),
        interests=interests or ["sightseeing"]
    )
    
    if category:
        attractions = [a for a in attractions if a.get("category") == category]
    
    return {
        "city": city_name,
        "attractions": attractions,
        "total": len(attractions),
        "categories": list(set(a.get("category", "other") for a in attractions))
    }


@router.get("/{city_name}/events")
async def get_city_events(
    city_name: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get events happening in a specific city."""
    city_key = city_name.lower().replace(" ", "")
    city_data = CITY_DATABASE.get(city_key, {"lat": 48.8566, "lon": 2.3522})
    
    events = events_service.get_events(
        city_data.get("lat", 48.8566),
        city_data.get("lon", 2.3522),
        start_date,
        end_date
    )
    
    return {
        "city": city_name,
        "events": events,
        "total": len(events),
        "date_range": {"start": start_date, "end": end_date}
    }


@router.get("/search")
async def search_cities(query: str = Query(..., min_length=2)):
    """Search for cities by name."""
    results = []
    query_lower = query.lower()
    
    for key, city in CITY_DATABASE.items():
        if query_lower in city["name"].lower() or query_lower in city["country"].lower():
            results.append({
                "name": city["name"],
                "country": city["country"],
                "description": city["description"][:100] + "...",
                "best_time": city["best_time_to_visit"]
            })
    
    # Also search for similar cities in our database
    similar_cities = [
        {"name": "Barcelona", "country": "Spain", "description": "Vibrant city with stunning architecture and beaches.", "best_time": "May to June, September"},
        {"name": "Dubai", "country": "UAE", "description": "Modern metropolis in the desert with luxury shopping.", "best_time": "November to March"},
        {"name": "Singapore", "country": "Singapore", "description": "Clean, green city-state with amazing food.", "best_time": "February to April"},
        {"name": "Sydney", "country": "Australia", "description": "Harbor city with iconic opera house and beaches.", "best_time": "September to November, March to May"},
        {"name": "Rome", "country": "Italy", "description": "Eternal City with ancient history and amazing food.", "best_time": "April to June, September to October"},
        {"name": "Bangkok", "country": "Thailand", "description": "Bustling city with temples, street food, and nightlife.", "best_time": "November to February"},
        {"name": "Istanbul", "country": "Turkey", "description": "Where East meets West, rich in history and culture.", "best_time": "April to May, September to November"},
        {"name": "Cape Town", "country": "South Africa", "description": "Stunning coastal city with Table Mountain.", "best_time": "October to April"},
    ]
    
    for city in similar_cities:
        if query_lower in city["name"].lower() or query_lower in city["country"].lower():
            if city not in results:
                results.append(city)
    
    return {"query": query, "results": results[:10]}


# ============ Helper Functions ============

async def _get_city_weather(city_name: str, travel_date: Optional[str]) -> CityWeather:
    """Get weather for a city."""
    # Mock weather data based on city
    weather_map = {
        "paris": {"temp": 18, "condition": "Partly Cloudy", "humidity": 65},
        "tokyo": {"temp": 22, "condition": "Sunny", "humidity": 55},
        "bali": {"temp": 29, "condition": "Sunny", "humidity": 80},
        "london": {"temp": 15, "condition": "Cloudy", "humidity": 70},
        "new york": {"temp": 20, "condition": "Clear", "humidity": 60},
    }
    
    city_key = city_name.lower().replace(" ", "")
    w = weather_map.get(city_key, {"temp": 20, "condition": "Pleasant", "humidity": 60})
    
    return CityWeather(
        current_temp=w["temp"],
        condition=w["condition"],
        humidity=w["humidity"],
        forecast=[
            {"day": "Today", "temp": w["temp"], "condition": w["condition"]},
            {"day": "Tomorrow", "temp": w["temp"] + 2, "condition": "Sunny"},
            {"day": "Day 3", "temp": w["temp"] - 1, "condition": "Partly Cloudy"},
        ],
        best_time_to_visit="Spring and Fall" if city_key not in ["bali"] else "Dry season",
        climate_overview="Mediterranean climate with mild winters" if city_key == "paris" else "Varies by season"
    )


async def _get_city_flights(city_name: str, origin: Optional[str], travel_date: Optional[str]) -> CityFlights:
    """Get flight info for a city."""
    if not origin:
        return CityFlights(
            from_origin=None,
            cheapest_price=None,
            duration_hours=None,
            airlines=[],
            flight_options=[]
        )
    
    flight_date = datetime.strptime(travel_date, "%Y-%m-%d").date() if travel_date else datetime.now().date()
    flights = await flight_service.search_flights(
        origin=origin,
        destination=city_name,
        departure_date=flight_date,
        adults=1
    )
    
    # Convert FlightOption objects to dictionaries
    flight_dicts = []
    for f in flights:
        flight_dicts.append({
            "airline": f.airline,
            "price": f.price,
            "duration_hours": f.duration_minutes / 60,
            "departure_time": f.departure_time.strftime("%H:%M") if f.departure_time else "",
            "arrival_time": f.arrival_time.strftime("%H:%M") if f.arrival_time else "",
            "stops": f.stops,
        })
    
    cheapest = min(flight_dicts, key=lambda x: x["price"]) if flight_dicts else None
    
    return CityFlights(
        from_origin=origin,
        cheapest_price=cheapest["price"] if cheapest else None,
        duration_hours=cheapest["duration_hours"] if cheapest else None,
        airlines=list(set(f["airline"] for f in flight_dicts)),
        flight_options=flight_dicts[:5]
    )


def _format_hotels(hotels: list, budget_level: str) -> CityHotels:
    """Format hotel data for response."""
    if not hotels:
        return CityHotels(
            price_range={"min": 50, "max": 300},
            top_rated=[],
            budget_options=[],
            luxury_options=[]
        )
    
    sorted_by_rating = sorted(hotels, key=lambda x: x.rating, reverse=True)
    sorted_by_price = sorted(hotels, key=lambda x: x.price_per_night)
    
    def hotel_to_dict(h):
        return {
            "name": h.name,
            "rating": h.rating,
            "price_per_night": h.price_per_night,
            "location": f"{h.distance_from_center:.1f}km from center"
        }
    
    return CityHotels(
        price_range={
            "min": sorted_by_price[0].price_per_night if sorted_by_price else 50,
            "max": sorted_by_price[-1].price_per_night if sorted_by_price else 300
        },
        top_rated=[hotel_to_dict(h) for h in sorted_by_rating[:3]],
        budget_options=[hotel_to_dict(h) for h in sorted_by_price[:3]],
        luxury_options=[hotel_to_dict(h) for h in (sorted_by_rating[-3:] if len(sorted_by_rating) >= 3 else sorted_by_rating)]
    )
