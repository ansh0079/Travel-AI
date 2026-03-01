import httpx
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel
from app.config import get_settings
from app.utils.cache import cache_result
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class FlightOption(BaseModel):
    id: str
    airline: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    price: float
    currency: str
    stops: int
    booking_url: str
    cabin_class: str

class FlightService:
    def __init__(self):
        self.settings = get_settings()
        self.amadeus_url = "https://test.api.amadeus.com/v2"
        self._access_token = None
        self._token_expiry = None
    
    async def _get_amadeus_token(self) -> str:
        """Get or refresh Amadeus API token"""
        if self._access_token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._access_token
        
        if not self.settings.amadeus_api_key or not self.settings.amadeus_api_secret:
            raise Exception("Amadeus API credentials not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://test.api.amadeus.com/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.amadeus_api_key,
                    "client_secret": self.settings.amadeus_api_secret
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            self._token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 1800))
            return self._access_token
    
    @cache_result(ttl=1800)
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        adults: int = 1
    ) -> List[FlightOption]:
        """Search for flights between destinations"""
        # Check if API credentials are configured
        if not self.settings.amadeus_api_key or not self.settings.amadeus_api_secret:
            logger.info("Amadeus API not configured, returning mock flights")
            return self._get_mock_flights(origin, destination, departure_date, return_date, adults)
        
        try:
            token = await self._get_amadeus_token()
            
            async with httpx.AsyncClient() as client:
                params = {
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDate": departure_date.isoformat(),
                    "adults": adults,
                    "max": 10
                }
                
                if return_date:
                    params["returnDate"] = return_date.isoformat()
                
                response = await client.get(
                    f"{self.amadeus_url}/shopping/flight-offers",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                flights = []
                for offer in data.get("data", [])[:10]:
                    itinerary = offer["itineraries"][0]
                    segments = itinerary["segments"]
                    
                    departure = datetime.fromisoformat(segments[0]["departure"]["at"].replace("Z", "+00:00"))
                    arrival = datetime.fromisoformat(segments[-1]["arrival"]["at"].replace("Z", "+00:00"))
                    duration = (arrival - departure).total_seconds() / 60
                    
                    flights.append(FlightOption(
                        id=offer["id"],
                        airline=segments[0]["carrierCode"],
                        departure_time=departure,
                        arrival_time=arrival,
                        duration_minutes=int(duration),
                        price=float(offer["price"]["total"]),
                        currency=offer["price"]["currency"],
                        stops=len(segments) - 1,
                        booking_url=offer.get("lastTicketingDate", ""),
                        cabin_class="economy"
                    ))
                
                return flights
        except Exception as e:
            logger.warning("Flight API error", error=str(e), origin=origin, destination=destination)
            return self._get_mock_flights(origin, destination, departure_date)
    
    def _get_mock_flights(
        self, 
        origin: str, 
        destination: str, 
        departure_date: date
    ) -> List[FlightOption]:
        """Generate mock flight data"""
        import random
        
        airlines = ["AA", "DL", "UA", "BA", "LH", "AF", "KL", "EK", "QR", "SQ"]
        
        return [
            FlightOption(
                id=f"flight_{i}",
                airline=random.choice(airlines),
                departure_time=datetime.combine(departure_date, datetime.min.time().replace(hour=8+i)),
                arrival_time=datetime.combine(departure_date, datetime.min.time().replace(hour=12+i)),
                duration_minutes=random.randint(180, 720),
                price=random.uniform(200, 1500),
                currency="USD",
                stops=random.randint(0, 2),
                booking_url="https://example.com/book",
                cabin_class="economy"
            )
            for i in range(5)
        ]
    
    async def get_airport_code(self, city: str) -> Optional[str]:
        """Get IATA airport code from city name"""
        # Skip API call if credentials not configured
        if not self.settings.amadeus_api_key or not self.settings.amadeus_api_secret:
            logger.debug("Amadeus API not configured, using mock airport codes")
            return self._get_mock_airport_code(city)
        
        try:
            token = await self._get_amadeus_token()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.amadeus_url}/reference-data/locations/cities",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"keyword": city, "max": 1},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get("data"):
                    return data["data"][0].get("iataCode")
        except Exception as e:
            logger.warning("Airport lookup error", error=str(e), city=city)
        
        # Fallback to common mappings
        return self._get_mock_airport_code(city)
    
    def _get_mock_airport_code(self, city: str) -> Optional[str]:
        """Return mock airport code for city"""
        city_codes = {
            "new york": "JFK", "london": "LHR", "paris": "CDG",
            "tokyo": "NRT", "sydney": "SYD", "dubai": "DXB",
            "los angeles": "LAX", "san francisco": "SFO",
            "chicago": "ORD", "miami": "MIA", "boston": "BOS",
            "singapore": "SIN", "hong kong": "HKG", "bangkok": "BKK",
            "seoul": "ICN", "beijing": "PEK", "shanghai": "PVG",
            "amsterdam": "AMS", "frankfurt": "FRA", "madrid": "MAD",
            "rome": "FCO", "milan": "MXP", "zurich": "ZRH",
            "toronto": "YYZ", "vancouver": "YVR", "sydney": "SYD",
            "melbourne": "MEL", "auckland": "AKL", "rio": "GIG",
            "cairo": "CAI", "istanbul": "IST", "dubai": "DXB",
            "bali": "DPS", "phuket": "HKT", "koh samui": "USM",
        }
        return city_codes.get(city.lower().strip())

from datetime import timedelta