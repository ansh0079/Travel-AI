import httpx
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.config import get_settings
from app.utils.cache_service import cache_service, CacheService
from app.models.destination import Event, EventType
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class EventsService:
    def __init__(self):
        self.settings = get_settings()
        self.ticketmaster_url = "https://app.ticketmaster.com/discovery/v2"
        self.predicthq_url = "https://api.predicthq.com/v1"
        self.cache = cache_service

    async def get_events(
        self,
        city: str,
        start_date: date,
        end_date: date,
        country_code: str = "US"
    ) -> List[Event]:
        """Get events for a city during date range with caching"""
        cache_key = CacheService.events_key(city, start_date.isoformat(), end_date.isoformat())
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug("Events cache hit", city=city, start_date=start_date, end_date=end_date)
            return [Event(**e) for e in cached]
        
        logger.debug("Events cache miss", city=city, start_date=start_date, end_date=end_date)
        
        events = []

        # Fetch from Ticketmaster
        try:
            tm_events = await self._fetch_ticketmaster(city, start_date, end_date, country_code)
            events.extend(tm_events)
        except Exception as e:
            logger.warning("Ticketmaster error", city=city, error=str(e))

        # Fetch from PredictHQ
        try:
            ph_events = await self._fetch_predicthq(city, start_date, end_date)
            events.extend(ph_events)
        except Exception as e:
            logger.warning("PredictHQ error", city=city, error=str(e))
        
        # If no API results, use mock data
        if not events:
            events = self._get_mock_events(city, start_date, end_date)
        
        # Deduplicate and sort by date
        result = self._deduplicate_and_sort(events)
        
        # Cache for 30 minutes (events change frequently)
        await self.cache.set(cache_key, [e.model_dump() for e in result], expire=timedelta(minutes=30))
        
        return result
    
    async def _fetch_ticketmaster(
        self,
        city: str,
        start: date,
        end: date,
        country: str
    ) -> List[Event]:
        """Fetch events from Ticketmaster"""
        if not self.settings.ticketmaster_api_key:
            return []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.ticketmaster_url}/events.json",
                params={
                    "apikey": self.settings.ticketmaster_api_key,
                    "city": city,
                    "countryCode": country,
                    "startDateTime": f"{start.isoformat()}T00:00:00Z",
                    "endDateTime": f"{end.isoformat()}T23:59:59Z",
                    "size": 20,
                    "sort": "date,asc"
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            events = []
            for item in data.get("_embedded", {}).get("events", []):
                try:
                    event_type = self._map_ticketmaster_type(item.get("classifications", []))
                    
                    # Parse date
                    date_str = item["dates"]["start"].get("dateTime")
                    if date_str:
                        event_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        date_str = item["dates"]["start"].get("localDate", start.isoformat())
                        event_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    # Get venue
                    venues = item.get("_embedded", {}).get("venues", [{}])
                    venue_name = venues[0].get("name", "TBD") if venues else "TBD"
                    
                    # Get price
                    price_ranges = item.get("priceRanges", [])
                    price_range = None
                    if price_ranges:
                        price_range = f"${price_ranges[0].get('min', '?')} - ${price_ranges[0].get('max', '?')}"
                    
                    events.append(Event(
                        id=item["id"],
                        name=item["name"],
                        type=event_type,
                        date=event_date,
                        venue=venue_name,
                        description=item.get("description", ""),
                        price_range=price_range or "Varies",
                        url=item.get("url")
                    ))
                except Exception as e:
                    logger.warning("Error parsing Ticketmaster event", error=str(e))
                    continue

            return events
    
    async def _fetch_predicthq(
        self,
        city: str,
        start: date,
        end: date
    ) -> List[Event]:
        """Fetch events from PredictHQ"""
        if not self.settings.predicthq_api_key:
            return []
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.predicthq_url}/events/",
                headers={
                    "Authorization": f"Bearer {self.settings.predicthq_api_key}",
                    "Accept": "application/json"
                },
                params={
                    "q": city,
                    "start.gte": start.isoformat(),
                    "start.lte": end.isoformat(),
                    "limit": 20,
                    "sort": "start"
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            events = []
            for item in data.get("results", []):
                try:
                    event_type = self._map_predicthq_type(item.get("category", ""))
                    
                    events.append(Event(
                        id=item["id"],
                        name=item.get("title", "Unnamed Event"),
                        type=event_type,
                        date=datetime.fromisoformat(item["start"].replace("Z", "+00:00")),
                        venue=item.get("entities", [{}])[0].get("name", "TBD") if item.get("entities") else "TBD",
                        description=item.get("description", ""),
                        price_range="Varies",
                        url=item.get("url")
                    ))
                except Exception as e:
                    logger.warning("Error parsing PredictHQ event", error=str(e))
                    continue

            return events
    
    def _map_ticketmaster_type(self, classifications: list) -> EventType:
        """Map Ticketmaster classification to EventType"""
        if not classifications:
            return EventType.CULTURAL
        
        try:
            segment = classifications[0].get("segment", {}).get("name", "").lower()
            genre = classifications[0].get("genre", {}).get("name", "").lower()
            
            if "music" in segment or "concert" in genre:
                return EventType.MUSIC
            elif "arts" in segment or "theatre" in segment:
                return EventType.THEATRE
            elif "film" in segment or "movie" in genre:
                return EventType.FILM
            elif "sports" in segment:
                return EventType.SPORTS
            elif "festival" in genre:
                return EventType.FESTIVAL
            else:
                return EventType.CULTURAL
        except:
            return EventType.CULTURAL
    
    def _map_predicthq_type(self, category: str) -> EventType:
        """Map PredictHQ category to EventType"""
        category_lower = category.lower() if category else ""
        
        mapping = {
            "concerts": EventType.MUSIC,
            "performing-arts": EventType.THEATRE,
            "sports": EventType.SPORTS,
            "festivals": EventType.FESTIVAL,
            "expos": EventType.CULTURAL,
            "community": EventType.CULTURAL,
            "conferences": EventType.CULTURAL
        }
        
        return mapping.get(category_lower, EventType.CULTURAL)
    
    def _get_mock_events(self, city: str, start: date, end: date) -> List[Event]:
        """Generate mock events"""
        import random
        
        event_types = [
            (EventType.MUSIC, "Live Music Night", "City Concert Hall"),
            (EventType.CULTURAL, f"{city} Cultural Festival", "Central Plaza"),
            (EventType.FOOD, "Street Food Market", "Riverside Park"),
            (EventType.ART, "Art Exhibition Opening", "Modern Art Gallery"),
            (EventType.SPORTS, "Marathon 2024", "City Stadium"),
            (EventType.THEATRE, "Broadway Show", "Grand Theatre"),
            (EventType.MUSIC, "Jazz in the Park", "Central Gardens"),
            (EventType.FESTIVAL, "Summer Carnival", "Fairgrounds"),
        ]
        
        events = []
        num_days = (end - start).days + 1
        
        for i in range(min(5, num_days)):
            event_type, name, venue = random.choice(event_types)
            event_date = start + __import__('datetime').timedelta(days=i)
            
            events.append(Event(
                id=f"mock_event_{i}",
                name=name,
                type=event_type,
                date=datetime.combine(event_date, datetime.min.time().replace(hour=19)),
                venue=venue,
                description=f"A wonderful {event_type.value} event in {city}",
                price_range=random.choice(["Free", "$10-$30", "$30-$50", "$50+"]),
                url=None
            ))
        
        return events
    
    def _deduplicate_and_sort(self, events: List[Event]) -> List[Event]:
        """Remove duplicate events and sort by date"""
        seen = set()
        unique = []
        
        for event in events:
            # Create deduplication key
            key = f"{event.name}_{event.date.strftime('%Y-%m-%d')}"
            if key not in seen:
                seen.add(key)
                unique.append(event)
        
        # Sort by date
        unique.sort(key=lambda x: x.date)
        
        return unique[:15]  # Limit to top 15