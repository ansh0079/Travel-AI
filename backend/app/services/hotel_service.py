import httpx
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
from app.config import get_settings
from app.utils.cache import cache_result

class HotelOption(BaseModel):
    id: str
    name: str
    address: str
    rating: float
    price_per_night: float
    currency: str
    amenities: List[str]
    image_url: Optional[str] = None
    booking_url: str
    distance_from_center: float

class HotelService:
    def __init__(self):
        self.settings = get_settings()
        self.amadeus_url = "https://test.api.amadeus.com/v2"
    
    @cache_result(ttl=3600)
    async def search_hotels(
        self,
        city: str,
        check_in: date,
        check_out: date,
        adults: int = 1,
        rooms: int = 1,
        max_price: Optional[float] = None
    ) -> List[HotelOption]:
        """Search for hotels in a city"""
        try:
            token = await self._get_amadeus_token()
            
            async with httpx.AsyncClient() as client:
                # Get city code
                city_response = await client.get(
                    f"{self.amadeus_url}/reference-data/locations/cities",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"keyword": city, "max": 1},
                    timeout=10.0
                )
                city_response.raise_for_status()
                city_data = city_response.json()
                
                if not city_data.get("data"):
                    return self._get_mock_hotels(city, check_in, check_out, max_price)
                
                city_code = city_data["data"][0].get("geoCode")
                if not city_code:
                    return self._get_mock_hotels(city, check_in, check_out, max_price)
                
                # Search hotels
                response = await client.get(
                    f"{self.amadeus_url}/shopping/hotel-offers",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "latitude": city_code["latitude"],
                        "longitude": city_code["longitude"],
                        "checkInDate": check_in.isoformat(),
                        "checkOutDate": check_out.isoformat(),
                        "roomQuantity": rooms,
                        "adults": adults,
                        "radius": 10,
                        "radiusUnit": "KM",
                        "bestRateOnly": "true"
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                hotels = []
                for offer in data.get("data", [])[:10]:
                    hotel = offer.get("hotel", {})
                    room = offer.get("offers", [{}])[0] if offer.get("offers") else {}
                    
                    price_data = room.get("price", {})
                    price = float(price_data.get("total", 0)) if price_data else 0
                    
                    if max_price and price > max_price:
                        continue
                    
                    nights = (check_out - check_in).days or 1
                    
                    hotels.append(HotelOption(
                        id=hotel.get("hotelId", f"hotel_{len(hotels)}"),
                        name=hotel.get("name", "Unknown Hotel"),
                        address=", ".join(hotel.get("address", {}).get("lines", [])) or "Address unavailable",
                        rating=float(hotel.get("rating", 0)) or 4.0,
                        price_per_night=price / nights,
                        currency=price_data.get("currency", "USD"),
                        amenities=hotel.get("amenities", []),
                        image_url=None,
                        booking_url=room.get("self", ""),
                        distance_from_center=float(hotel.get("distance", {}).get("value", 0)) / 1000
                    ))
                
                return hotels
        except Exception as e:
            print(f"Hotel API error: {e}")
            return self._get_mock_hotels(city, check_in, check_out, max_price)
    
    async def _get_amadeus_token(self) -> str:
        """Get Amadeus API token from flight service"""
        from app.services.flight_service import FlightService
        return await FlightService()._get_amadeus_token()
    
    def _get_mock_hotels(
        self, 
        city: str, 
        check_in: date, 
        check_out: date, 
        max_price: Optional[float] = None
    ) -> List[HotelOption]:
        """Generate mock hotel data"""
        import random
        
        hotel_types = [
            {"name": f"{city} Grand Hotel", "rating": 4.5, "base_price": 150},
            {"name": f"{city} Boutique Inn", "rating": 4.2, "base_price": 120},
            {"name": f"{city} Budget Stay", "rating": 3.5, "base_price": 75},
            {"name": f"{city} Luxury Resort", "rating": 4.9, "base_price": 300},
            {"name": f"{city} Central Plaza", "rating": 4.0, "base_price": 100},
            {"name": f"{city} Riverside Hotel", "rating": 4.3, "base_price": 130},
        ]
        
        hotels = []
        for i, h in enumerate(hotel_types):
            price = h["base_price"] * random.uniform(0.9, 1.3)
            
            if max_price and price > max_price:
                continue
            
            hotels.append(HotelOption(
                id=f"hotel_{i}",
                name=h["name"],
                address=f"{random.randint(1, 999)} Main St, {city}",
                rating=h["rating"],
                price_per_night=round(price, 2),
                currency="USD",
                amenities=random.sample(
                    ["WiFi", "Pool", "Gym", "Spa", "Restaurant", "Bar", "Parking", "Breakfast"],
                    k=random.randint(3, 6)
                ),
                image_url=None,
                booking_url="https://example.com/book",
                distance_from_center=round(random.uniform(0.2, 5.0), 1)
            ))
        
        return hotels