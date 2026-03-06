"""
API-Integrated Scrapers for Autonomous Travel Research
Uses official APIs first, falls back to web scraping if API fails
"""
import aiohttp
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import re
import logging

from app.utils.logging_config import get_logger
from app.config import get_settings

logger = get_logger(__name__)


class APIFlightScraper:
    """
    Flight deal scraper with API integration.
    Priority: Amadeus API → Scraping → Mock Data
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.amadeus_token = None
        self.amadeus_token_expiry = None
    
    async def search_deals(self, origin: str, destination: str, dates: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for flight deals using API first, then scraping."""
        logger.info(f"Searching flights: {origin} → {destination}")
        
        # Try Amadeus API first
        if self.settings.amadeus_api_key:
            try:
                api_deals = await self._search_amadeus_api(origin, destination, dates)
                if api_deals:
                    logger.info(f"Found {len(api_deals)} flights from Amadeus API")
                    return api_deals
            except Exception as e:
                logger.warning(f"Amadeus API failed, falling back to scraping: {str(e)}")
        
        # Fallback to web scraping
        try:
            scrape_deals = await self._scrape_flight_deals(origin, destination, dates)
            if scrape_deals:
                logger.info(f"Found {len(scrape_deals)} flights from scraping")
                return scrape_deals
        except Exception as e:
            logger.warning(f"Scraping failed, using mock data: {str(e)}")
        
        # Final fallback to mock data
        return await self._get_mock_flight_deals(origin, destination, dates)
    
    async def _get_amadeus_token(self) -> Optional[str]:
        """Get or refresh Amadeus API token."""
        if self.amadeus_token and self.amadeus_token_expiry and datetime.now() < self.amadeus_token_expiry:
            return self.amadeus_token
        
        try:
            url = "https://test.api.amadeus.com/v1/security/oauth2/token"
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.settings.amadeus_api_key,
                'client_secret': self.settings.amadeus_api_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.amadeus_token = result['access_token']
                        self.amadeus_token_expiry = datetime.now() + timedelta(seconds=result['expires_in'])
                        return self.amadeus_token
        except Exception as e:
            logger.error(f"Failed to get Amadeus token: {str(e)}")
        
        return None
    
    async def _search_amadeus_api(self, origin: str, destination: str, dates: Optional[str]) -> List[Dict[str, Any]]:
        """Search flights using Amadeus Flight Offers Search API."""
        token = await self._get_amadeus_token()
        if not token:
            return []
        
        try:
            # Parse dates
            departure_date = dates or (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Amadeus API endpoint
            url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
            params = {
                'originLocationCode': origin.upper()[:3],  # Extract airport code
                'destinationLocationCode': destination.upper()[:3],
                'departureDate': departure_date,
                'adults': 1,
                'max': 10
            }
            
            headers = {'Authorization': f'Bearer {token}'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._parse_amadeus_response(result.get('data', []))
                    else:
                        logger.warning(f"Amadeus API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Amadeus API search failed: {str(e)}")
            return []
    
    def _parse_amadeus_response(self, data: List[Dict]) -> List[Dict[str, Any]]:
        """Parse Amadeus API response into standardized format."""
        deals = []
        
        for offer in data[:10]:  # Top 10 offers
            try:
                price = float(offer.get('price', {}).get('total', 0))
                segments = offer.get('itineraries', [{}])[0].get('segments', [])
                
                # Extract airline from first segment
                airline = segments[0].get('carrier', {}).get('code', 'Unknown') if segments else 'Unknown'
                
                # Extract origin/destination from segments
                origin = segments[0].get('departure', {}).get('iataCode', '') if segments else ''
                destination = segments[-1].get('arrival', {}).get('iataCode', '') if segments else ''
                
                deals.append({
                    'price': price,
                    'currency': 'USD',
                    'airline': airline,
                    'class': 'economy',
                    'origin': origin,
                    'destination': destination,
                    'dates': offer.get('itineraries', [{}])[0].get('segments', [{}])[0].get('departure', {}).get('at', '')[:10],
                    'url': f"https://www.google.com/flights",
                    'source': 'Amadeus API',
                    'found_at': datetime.now().isoformat(),
                    'confidence': 0.95,  # High confidence from official API
                })
            except Exception as e:
                logger.debug(f"Error parsing Amadeus offer: {str(e)}")
        
        return deals
    
    async def _scrape_flight_deals(self, origin: str, destination: str, dates: Optional[str]) -> List[Dict[str, Any]]:
        """Fallback to web scraping if API fails."""
        # Import from enhanced scrapers
        from app.utils.web_scrapers_enhanced import FlightDealScraper
        
        scraper = FlightDealScraper()
        return await scraper.search_deals(origin, destination, dates)
    
    async def _get_mock_flight_deals(self, origin: str, destination: str, dates: Optional[str]) -> List[Dict[str, Any]]:
        """Final fallback to mock data."""
        import random
        
        airlines = ['Emirates', 'Qatar Airways', 'Singapore Airlines', 'Lufthansa', 'British Airways']
        
        deals = []
        for _ in range(3):
            deal = {
                'price': random.randint(400, 1200),
                'currency': 'USD',
                'airline': random.choice(airlines),
                'class': 'economy',
                'origin': origin,
                'destination': destination,
                'dates': dates or 'Flexible',
                'url': f"https://www.google.com/flights?q={origin}+to+{destination}",
                'source': 'Mock Data',
                'found_at': datetime.now().isoformat(),
                'confidence': 0.5,
            }
            deals.append(deal)
        
        return deals


class APIHotelScraper:
    """
    Hotel scraper with API integration.
    Priority: Booking API → Scraping → Mock Data
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def search_hotels(self, destination: str, check_in: Optional[str] = None, 
                           check_out: Optional[str] = None, budget_level: str = 'moderate') -> List[Dict[str, Any]]:
        """Search hotels using available APIs, then scraping."""
        logger.info(f"Searching hotels in {destination}")
        
        # Try Google Places API if available
        if self.settings.google_places_api_key:
            try:
                api_hotels = await self._search_google_places_api(destination, check_in, check_out)
                if api_hotels:
                    logger.info(f"Found {len(api_hotels)} hotels from Google Places API")
                    return api_hotels
            except Exception as e:
                logger.warning(f"Google Places API failed: {str(e)}")
        
        # Fallback to scraping
        from app.utils.web_scrapers_enhanced import HotelDealScraper
        
        scraper = HotelDealScraper()
        return await scraper.search_hotels(destination, check_in, check_out, budget_level)
    
    async def _search_google_places_api(self, destination: str, check_in: Optional[str], 
                                       check_out: Optional[str]) -> List[Dict[str, Any]]:
        """Search hotels using Google Places API."""
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': destination,
                'radius': 5000,
                'type': 'lodging',
                'key': self.settings.google_places_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._parse_places_response(result.get('results', []))
                    return []
        except Exception as e:
            logger.error(f"Google Places API error: {str(e)}")
            return []
    
    def _parse_places_response(self, places: List[Dict]) -> List[Dict[str, Any]]:
        """Parse Google Places API response."""
        hotels = []
        
        for place in places[:10]:
            try:
                # Extract price level (0-4)
                price_level = place.get('price_level', 2)
                price_map = {0: 50, 1: 100, 2: 200, 3: 350, 4: 500}
                
                hotels.append({
                    'name': place.get('name', 'Unknown Hotel'),
                    'price_per_night': price_map.get(price_level, 200),
                    'currency': 'USD',
                    'rating': place.get('rating', 4.0),
                    'amenities': place.get('types', []),
                    'location': place.get('vicinity', ''),
                    'url': f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id')}",
                    'source': 'Google Places API',
                    'found_at': datetime.now().isoformat(),
                })
            except Exception as e:
                logger.debug(f"Error parsing place: {str(e)}")
        
        return hotels


class APIRestaurantScraper:
    """
    Restaurant scraper with API integration.
    Priority: TripAdvisor API → Google Places → Scraping → Mock
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def get_restaurants(self, destination: str, dietary_restrictions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get restaurants using APIs first."""
        logger.info(f"Searching restaurants in {destination}")
        
        # Try TripAdvisor API
        if self.settings.tripadvisor_api_key:
            try:
                api_restaurants = await self._search_tripadvisor_api(destination)
                if api_restaurants:
                    logger.info(f"Found {len(api_restaurants)} restaurants from TripAdvisor API")
                    return api_restaurants
            except Exception as e:
                logger.warning(f"TripAdvisor API failed: {str(e)}")
        
        # Try Google Places
        if self.settings.google_places_api_key:
            try:
                api_restaurants = await self._search_google_places_restaurants(destination)
                if api_restaurants:
                    logger.info(f"Found {len(api_restaurants)} restaurants from Google Places API")
                    return api_restaurants
            except Exception as e:
                logger.warning(f"Google Places API failed: {str(e)}")
        
        # Fallback to scraping
        from app.utils.web_scrapers_enhanced import RestaurantScraper
        
        scraper = RestaurantScraper()
        return await scraper.get_restaurants(destination, dietary_restrictions)
    
    async def _search_tripadvisor_api(self, destination: str) -> List[Dict[str, Any]]:
        """Search restaurants using TripAdvisor API."""
        # Implementation depends on TripAdvisor API endpoints
        return []
    
    async def _search_google_places_restaurants(self, destination: str) -> List[Dict[str, Any]]:
        """Search restaurants using Google Places API."""
        try:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': destination,
                'radius': 3000,
                'type': 'restaurant',
                'key': self.settings.google_places_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._parse_restaurants_response(result.get('results', []))
                    return []
        except Exception as e:
            logger.error(f"Google Places API error: {str(e)}")
            return []
    
    def _parse_restaurants_response(self, places: List[Dict]) -> List[Dict[str, Any]]:
        """Parse Google Places restaurant response."""
        restaurants = []
        
        for place in places[:15]:
            try:
                restaurants.append({
                    'name': place.get('name', 'Unknown Restaurant'),
                    'cuisine': 'Various',
                    'price_range': '$' * place.get('price_level', 2) + '-' + '$' * (place.get('price_level', 2) + 1),
                    'rating': place.get('rating', 4.0),
                    'address': place.get('vicinity', ''),
                    'specialties': ['Local specialties'],
                    'dietary_options': ['Vegetarian options'],
                    'url': f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id')}",
                    'source': 'Google Places API',
                    'found_at': datetime.now().isoformat(),
                })
            except Exception as e:
                logger.debug(f"Error parsing restaurant: {str(e)}")
        
        return restaurants


class APIEventScraper:
    """
    Event scraper with API integration.
    Priority: Ticketmaster API → Eventbrite API → Scraping → Mock
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def get_local_events(self, destination: str, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get events using APIs first."""
        logger.info(f"Searching events in {destination}")
        
        # Try Ticketmaster API
        if self.settings.ticketmaster_api_key:
            try:
                api_events = await self._search_ticketmaster_api(destination, start_date, end_date)
                if api_events:
                    logger.info(f"Found {len(api_events)} events from Ticketmaster API")
                    return api_events
            except Exception as e:
                logger.warning(f"Ticketmaster API failed: {str(e)}")
        
        # Fallback to scraping
        from app.utils.web_scrapers_enhanced import LocalEventScraper
        
        scraper = LocalEventScraper()
        return await scraper.get_local_events(destination, start_date, end_date)
    
    async def _search_ticketmaster_api(self, destination: str, start_date: Optional[str],
                                      end_date: Optional[str]) -> List[Dict[str, Any]]:
        """Search events using Ticketmaster Discovery API."""
        try:
            url = "https://app.ticketmaster.com/discovery/v2/events.json"
            params = {
                'apikey': self.settings.ticketmaster_api_key,
                'city': destination,
                'size': 10
            }
            
            if start_date:
                params['startDateTime'] = start_date
            if end_date:
                params['endDateTime'] = end_date
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._parse_ticketmaster_response(result.get('_embedded', {}).get('events', []))
                    return []
        except Exception as e:
            logger.error(f"Ticketmaster API error: {str(e)}")
            return []
    
    def _parse_ticketmaster_response(self, events: List[Dict]) -> List[Dict[str, Any]]:
        """Parse Ticketmaster API response."""
        result = []
        
        for event in events[:10]:
            try:
                result.append({
                    'name': event.get('name', 'Unknown Event'),
                    'date': event.get('dates', {}).get('start', {}).get('localDate', 'TBD'),
                    'venue': event.get('_embedded', {}).get('venues', [{}])[0].get('name', 'Unknown Venue'),
                    'category': event.get('classifications', [{}])[0].get('segment', {}).get('name', 'General'),
                    'description': event.get('info', 'No description'),
                    'url': event.get('url', ''),
                    'source': 'Ticketmaster API',
                    'found_at': datetime.now().isoformat(),
                })
            except Exception as e:
                logger.debug(f"Error parsing event: {str(e)}")
        
        return result


# Convenience functions for use in auto_research_agent
async def search_flights(origin: str, destination: str, dates: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search flights using API-first approach."""
    scraper = APIFlightScraper()
    return await scraper.search_deals(origin, destination, dates)

async def search_hotels(destination: str, check_in: Optional[str] = None, 
                       check_out: Optional[str] = None, budget_level: str = 'moderate') -> List[Dict[str, Any]]:
    """Search hotels using API-first approach."""
    scraper = APIHotelScraper()
    return await scraper.search_hotels(destination, check_in, check_out, budget_level)

async def get_restaurants(destination: str, dietary_restrictions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Get restaurants using API-first approach."""
    scraper = APIRestaurantScraper()
    return await scraper.get_restaurants(destination, dietary_restrictions)

async def get_events(destination: str, start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get events using API-first approach."""
    scraper = APIEventScraper()
    return await scraper.get_local_events(destination, start_date, end_date)
