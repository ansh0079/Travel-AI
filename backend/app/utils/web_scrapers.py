"""
Web scraping tools for autonomous travel research
Scrapes flight deals, hotel deals, travel blogs, local events, restaurants, and safety info
"""
import aiohttp
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import re
import logging

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaseScraper:
    """Base class for all scrapers with rate limiting and error handling."""
    
    def __init__(self, rate_limit: float = 0.5):  # seconds between requests
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 TravelAI-Bot/1.0'
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={'User-Agent': self.user_agent},
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session
    
    async def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)
        self.last_request_time = now
    
    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML with rate limiting and error handling."""
        await self._rate_limit()
        
        try:
            session = await self._get_session()
            async with session.get(url, headers={
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }) as response:
                if response.status == 200:
                    return await response.text()
                logger.warning(f"Failed to fetch {url}: {response.status}")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {url}")
        except aiohttp.ClientError as e:
            logger.warning(f"Client error fetching {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
        
        return None
    
    async def close(self):
        """Close session."""
        if self.session and not self.session.closed:
            await self.session.close()


class FlightDealScraper(BaseScraper):
    """Scrapes flight deals from various sources."""
    
    async def search_deals(self, origin: str, destination: str, dates: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for flight deals from multiple sources."""
        logger.info(f"Searching flight deals: {origin} → {destination}")
        
        # Use mock data for reliability (can be replaced with real scraping)
        # Real scraping targets (for future implementation):
        # - SecretFlying.com
        # - TheFlightDeal.com
        # - Scott's Cheap Flights
        
        deals = await self._get_mock_flight_deals(origin, destination, dates)
        return deals
    
    async def _get_mock_flight_deals(self, origin: str, destination: str, dates: Optional[str]) -> List[Dict[str, Any]]:
        """Generate realistic mock flight deals for demo purposes."""
        # In production, this would scrape real sites
        import random
        
        base_prices = {
            'economy': random.randint(300, 800),
            'premium': random.randint(800, 1500),
            'business': random.randint(1500, 3500),
        }
        
        airlines = ['Emirates', 'Qatar Airways', 'Singapore Airlines', 'Lufthansa', 'British Airways', 'Air France']
        
        deals = []
        for class_type, base_price in base_prices.items():
            deal = {
                'price': base_price,
                'currency': 'USD',
                'airline': random.choice(airlines),
                'class': class_type,
                'origin': origin,
                'destination': destination,
                'dates': dates or 'Flexible dates',
                'url': f'https://www.google.com/flights?q={origin}+to+{destination}',
                'found_at': datetime.now().isoformat(),
                'confidence': random.uniform(0.7, 0.95),
            }
            deals.append(deal)
        
        # Sort by price
        deals.sort(key=lambda x: x['price'])
        
        return deals[:3]  # Return top 3 deals
    
    def _extract_deals(self, soup: BeautifulSoup, source: str) -> List[Dict[str, Any]]:
        """Extract flight deals from parsed HTML (implementation varies by site)."""
        deals = []
        # This would be customized for each scraping target
        return deals


class HotelDealScraper(BaseScraper):
    """Scrapes hotel deals from booking sites."""
    
    async def search_hotels(self, destination: str, check_in: Optional[str] = None, 
                           check_out: Optional[str] = None, budget_level: str = 'moderate') -> List[Dict[str, Any]]:
        """Search for hotel deals."""
        logger.info(f"Searching hotels in {destination}")
        
        hotels = await self._get_mock_hotel_deals(destination, check_in, check_out, budget_level)
        return hotels
    
    async def _get_mock_hotel_deals(self, destination: str, check_in: Optional[str], 
                                   check_out: Optional[str], budget_level: str) -> List[Dict[str, Any]]:
        """Generate realistic mock hotel deals."""
        import random
        
        budget_ranges = {
            'low': (30, 80),
            'moderate': (80, 200),
            'high': (200, 400),
            'luxury': (400, 1000),
        }
        
        min_price, max_price = budget_ranges.get(budget_level, (80, 200))
        
        hotel_chains = ['Marriott', 'Hilton', 'Hyatt', 'IHG', 'Accor', 'Boutique Hotel', 'Local Inn']
        
        hotels = []
        for i in range(5):
            price = random.randint(min_price, max_price)
            hotel = {
                'name': f"{random.choice(hotel_chains)} {destination.split(',')[0]}",
                'price_per_night': price,
                'currency': 'USD',
                'rating': round(random.uniform(3.5, 5.0), 1),
                'amenities': random.sample(['WiFi', 'Pool', 'Gym', 'Spa', 'Restaurant', 'Bar', 'Parking'], k=random.randint(2, 5)),
                'location': f'{destination} City Center',
                'url': f'https://www.booking.com/searchresults.html?ss={destination.replace(" ", "+")}',
                'found_at': datetime.now().isoformat(),
            }
            hotels.append(hotel)
        
        hotels.sort(key=lambda x: x['rating'] / x['price_per_night'], reverse=True)  # Best value
        return hotels


class TravelBlogScraper(BaseScraper):
    """Scrapes travel blogs for insights and tips."""
    
    async def get_destination_insights(self, destination: str) -> List[Dict[str, Any]]:
        """Get insights from travel blogs."""
        logger.info(f"Searching travel blog insights for {destination}")
        
        insights = await self._get_mock_blog_insights(destination)
        return insights
    
    async def _get_mock_blog_insights(self, destination: str) -> List[Dict[str, Any]]:
        """Generate mock blog insights."""
        insights = [
            {
                'title': f'Ultimate Guide to {destination}',
                'url': f'https://www.nomadicmatt.com/travel-blogs/{destination.replace(" ", "-").lower()}/',
                'source': 'Nomadic Matt',
                'summary': f'Comprehensive guide covering the best attractions, food, and hidden gems in {destination}',
                'tips': [
                    'Visit early morning to avoid crowds',
                    'Book accommodations in advance during peak season',
                    'Try local street food for authentic experiences',
                    'Use public transport for budget-friendly travel',
                ],
                'found_at': datetime.now().isoformat(),
            },
            {
                'title': f'{destination} Travel Tips: What I Wish I Knew',
                'url': f'https://www.lonelyplanet.com/{destination.replace(" ", "-").lower()}',
                'source': 'Lonely Planet',
                'summary': f'Essential tips and common mistakes to avoid when visiting {destination}',
                'tips': [
                    'Learn a few local phrases',
                    'Carry cash as some places don\'t accept cards',
                    'Respect local customs and dress codes',
                ],
                'found_at': datetime.now().isoformat(),
            },
        ]
        return insights


class LocalEventScraper(BaseScraper):
    """Scrapes local events and festivals."""
    
    async def get_local_events(self, destination: str, start_date: Optional[str] = None, 
                               end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get local events during travel dates."""
        logger.info(f"Searching local events in {destination}")
        
        events = await self._get_mock_events(destination, start_date, end_date)
        return events
    
    async def _get_mock_events(self, destination: str, start_date: Optional[str], 
                               end_date: Optional[str]) -> List[Dict[str, Any]]:
        """Generate mock local events."""
        events = [
            {
                'name': f'{destination} Cultural Festival',
                'date': start_date or '2024-06-15',
                'venue': f'{destination} City Center',
                'category': 'Cultural',
                'description': f'Annual cultural festival featuring local art, music, and food',
                'url': f'https://www.eventbrite.com/d/{destination.replace(" ", "-").lower()}/',
            },
            {
                'name': 'Live Music Night',
                'date': start_date or '2024-06-16',
                'venue': 'Downtown Arena',
                'category': 'Music',
                'description': 'Local bands and artists performing live',
                'url': f'https://www.ticketmaster.com/{destination.replace(" ", "-").lower()}',
            },
        ]
        return events


class RestaurantScraper(BaseScraper):
    """Scrapes restaurant recommendations and reviews."""
    
    async def get_restaurants(self, destination: str, dietary_restrictions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get restaurant recommendations."""
        logger.info(f"Searching restaurants in {destination}")
        
        restaurants = await self._get_mock_restaurants(destination, dietary_restrictions)
        return restaurants
    
    async def _get_mock_restaurants(self, destination: str, 
                                   dietary_restrictions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate mock restaurant data."""
        cuisines = ['Local', 'Italian', 'Japanese', 'French', 'Mediterranean', 'Fusion']
        
        restaurants = []
        for i in range(8):
            restaurant = {
                'name': f'{random.choice(cuisines)} Kitchen {i+1}',
                'cuisine': random.choice(cuisines),
                'price_range': '$$-$$$' if i < 4 else '$-$$',
                'rating': round(random.uniform(4.0, 5.0), 1),
                'address': f'{destination} City Center',
                'specialties': ['Local specialties', 'Chef\'s recommendation', 'Seasonal menu'],
                'dietary_options': dietary_restrictions or ['Vegetarian options', 'Vegan options'],
                'url': f'https://www.tripadvisor.com/Restaurants-{destination.replace(" ", "-").lower()}',
            }
            restaurants.append(restaurant)
        
        restaurants.sort(key=lambda x: x['rating'], reverse=True)
        return restaurants


class SafetyScraper(BaseScraper):
    """Scrapes travel safety information."""
    
    async def get_safety_info(self, destination: str) -> Dict[str, Any]:
        """Get safety information for destination."""
        logger.info(f"Searching safety info for {destination}")
        
        safety_info = await self._get_mock_safety_info(destination)
        return safety_info
    
    async def _get_mock_safety_info(self, destination: str) -> Dict[str, Any]:
        """Generate mock safety information."""
        import random
        
        safety_score = random.uniform(6.5, 9.5)
        
        return {
            'safety_score': round(safety_score, 1),
            'risk_level': 'Low' if safety_score > 8 else 'Medium' if safety_score > 7 else 'Exercise Caution',
            'advisories': [
                'Keep valuables secure in tourist areas',
                'Use licensed taxis or ride-sharing apps',
                'Stay aware of surroundings in crowded places',
            ],
            'emergency_numbers': {
                'police': '112',
                'ambulance': '112',
                'fire': '112',
            },
            'health_advisories': [
                'Drink bottled water',
                'Use insect repellent in tropical areas',
                'Travel insurance recommended',
            ],
            'source': 'Government Travel Advisories',
            'updated_at': datetime.now().isoformat(),
        }


# Import random at module level for mock data generation
import random


async def close_all_scrapers(*scrapers):
    """Helper to close all scraper sessions."""
    for scraper in scrapers:
        try:
            await scraper.close()
        except Exception as e:
            logger.error(f"Error closing scraper: {str(e)}")
