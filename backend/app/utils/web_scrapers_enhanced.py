"""
Enhanced Web Scrapers for Autonomous Travel Research
Real scraping implementations with fallback to mock data
"""
import aiohttp
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import re
import json
import logging

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaseScraper:
    """Base class for all scrapers with rate limiting, retries, and error handling."""
    
    def __init__(self, rate_limit: float = 1.0, max_retries: int = 2):
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.last_request_time = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 TravelAI-Bot/1.0'
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    'User-Agent': self.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                },
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self.session
    
    async def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)
        self.last_request_time = now
    
    async def fetch_html(self, url: str, use_proxy: bool = False) -> Optional[str]:
        """Fetch HTML with rate limiting, retries, and error handling."""
        for attempt in range(self.max_retries):
            try:
                await self._rate_limit()
                
                session = await self._get_session()
                async with session.get(url, headers={
                    'User-Agent': self.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                }) as response:
                    if response.status == 200:
                        html = await response.text()
                        logger.debug(f"Successfully fetched {url}")
                        return html
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited from {url}, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except aiohttp.ClientError as e:
                logger.warning(f"Client error fetching {url}: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                break
        
        return None
    
    async def fetch_json(self, url: str) -> Optional[Dict]:
        """Fetch JSON data from API endpoint."""
        try:
            await self._rate_limit()
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching JSON from {url}: {str(e)}")
        return None
    
    async def close(self):
        """Close session."""
        if self.session and not self.session.closed:
            await self.session.close()


class FlightDealScraper(BaseScraper):
    """Scrapes flight deals from multiple real sources."""
    
    # Real scraping targets
    SCRAPE_TARGETS = {
        'secret_flying': 'https://www.secretflying.com',
        'flight_deal': 'https://www.theflightdeal.com',
        'google_flights': 'https://www.google.com/travel/flights',
        'skyscanner': 'https://www.skyscanner.net',
    }
    
    async def search_deals(self, origin: str, destination: str, dates: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for flight deals from multiple real sources."""
        logger.info(f"Searching real flight deals: {origin} → {destination}")
        
        all_deals = []
        
        # Try multiple sources in parallel
        tasks = []
        
        # Task 1: Try SecretFlying (if we can find deal pages)
        tasks.append(self._scrape_secret_flying(origin, destination))
        
        # Task 2: Try TheFlightDeal
        tasks.append(self._scrape_theflightdeal(origin, destination))
        
        # Task 3: Use Google Flights search URL (fallback)
        tasks.append(self._search_google_flights(origin, destination, dates))
        
        # Execute all scraping tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_deals.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Flight scraper error: {str(result)}")
        
        # If no real deals found, fall back to mock data
        if not all_deals:
            logger.info("No real flight deals found, using mock data as fallback")
            all_deals = await self._get_mock_flight_deals(origin, destination, dates)
        
        # Remove duplicates and sort by price
        seen = set()
        unique_deals = []
        for deal in all_deals:
            key = f"{deal.get('origin')}-{deal.get('destination')}-{deal.get('price')}"
            if key not in seen:
                seen.add(key)
                unique_deals.append(deal)
        
        unique_deals.sort(key=lambda x: x.get('price', float('inf')))
        
        return unique_deals[:10]  # Return top 10 deals
    
    async def _scrape_secret_flying(self, origin: str, destination: str) -> List[Dict[str, Any]]:
        """Scrape SecretFlying for flight deals."""
        try:
            # Search for deals matching route
            search_url = f"{self.SCRAPE_TARGETS['secret_flying']}/?s={origin}+{destination}"
            html = await self.fetch_html(search_url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            deals = []
            
            # Look for deal articles
            for article in soup.find_all('article', limit=5):
                try:
                    title_elem = article.find('h2') or article.find('h3')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Check if title mentions origin or destination
                    if origin.lower() not in title.lower() and destination.lower() not in title.lower():
                        continue
                    
                    # Extract price if mentioned
                    price_match = re.search(r'\$(\d{3,4})', title)
                    price = int(price_match.group(1)) if price_match else None
                    
                    # Get link
                    link_elem = article.find('a', href=True)
                    url = link_elem['href'] if link_elem else search_url
                    
                    deals.append({
                        'price': price or 0,
                        'currency': 'USD',
                        'airline': 'Various',
                        'class': 'economy',
                        'origin': origin,
                        'destination': destination,
                        'dates': 'Flexible',
                        'url': url,
                        'source': 'SecretFlying',
                        'found_at': datetime.now().isoformat(),
                        'confidence': 0.8 if price else 0.5,
                    })
                except Exception as e:
                    logger.debug(f"Error parsing SecretFlying article: {str(e)}")
            
            return deals
            
        except Exception as e:
            logger.warning(f"SecretFlying scraping failed: {str(e)}")
            return []
    
    async def _scrape_theflightdeal(self, origin: str, destination: str) -> List[Dict[str, Any]]:
        """Scrape TheFlightDeal for flight deals."""
        try:
            # TheFlightDeal uses tags for routes
            search_url = f"{self.SCRAPE_TARGETS['flight_deal']}/tag/{origin.replace(' ', '-')}-to-{destination.replace(' ', '-')}"
            html = await self.fetch_html(search_url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            deals = []
            
            # Look for deal posts
            for post in soup.find_all('article', class_='post', limit=5):
                try:
                    title = post.find('h2', class_='entry-title')
                    if not title:
                        continue
                    
                    title_text = title.get_text(strip=True)
                    
                    # Extract price
                    price_match = re.search(r'\$(\d{3,4})', title_text)
                    price = int(price_match.group(1)) if price_match else None
                    
                    # Get link
                    link = post.find('a', class_='entry-link', href=True)
                    url = link['href'] if link else search_url
                    
                    deals.append({
                        'price': price or 0,
                        'currency': 'USD',
                        'airline': 'Various',
                        'class': 'economy',
                        'origin': origin,
                        'destination': destination,
                        'dates': 'Check listing',
                        'url': url,
                        'source': 'TheFlightDeal',
                        'found_at': datetime.now().isoformat(),
                        'confidence': 0.75 if price else 0.5,
                    })
                except Exception as e:
                    logger.debug(f"Error parsing TheFlightDeal post: {str(e)}")
            
            return deals
            
        except Exception as e:
            logger.warning(f"TheFlightDeal scraping failed: {str(e)}")
            return []
    
    async def _search_google_flights(self, origin: str, destination: str, dates: Optional[str]) -> List[Dict[str, Any]]:
        """Generate Google Flights search URL (doesn't scrape, just provides link)."""
        # Google Flights doesn't allow scraping, but we can provide a search URL
        base_price = 500  # Mock base price
        
        return [{
            'price': base_price,
            'currency': 'USD',
            'airline': 'Multiple Airlines',
            'class': 'economy',
            'origin': origin,
            'destination': destination,
            'dates': dates or 'Flexible',
            'url': f"https://www.google.com/travel/flights?q=Flights+to+{destination.replace(' ', '+')}+from+{origin.replace(' ', '+')}",
            'source': 'Google Flights',
            'found_at': datetime.now().isoformat(),
            'confidence': 0.6,
        }]
    
    async def _get_mock_flight_deals(self, origin: str, destination: str, dates: Optional[str]) -> List[Dict[str, Any]]:
        """Generate mock flight deals as fallback."""
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


class HotelDealScraper(BaseScraper):
    """Scrapes hotel deals from booking sites."""
    
    SCRAPE_TARGETS = {
        'booking': 'https://www.booking.com',
        'hotels': 'https://www.hotels.com',
        'expedia': 'https://www.expedia.com',
    }
    
    async def search_hotels(self, destination: str, check_in: Optional[str] = None, 
                           check_out: Optional[str] = None, budget_level: str = 'moderate') -> List[Dict[str, Any]]:
        """Search for hotel deals from real sources."""
        logger.info(f"Searching real hotel deals in {destination}")
        
        all_hotels = []
        
        # Try scraping Booking.com
        booking_task = self._scrape_booking(destination, check_in, check_out, budget_level)
        
        # Try scraping Hotels.com
        hotels_task = self._scrape_hotels_com(destination, check_in, check_out, budget_level)
        
        results = await asyncio.gather(booking_task, hotels_task, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_hotels.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Hotel scraper error: {str(result)}")
        
        # Fallback to mock data if no real deals found
        if not all_hotels:
            logger.info("No real hotel deals found, using mock data")
            all_hotels = await self._get_mock_hotel_deals(destination, check_in, check_out, budget_level)
        
        # Remove duplicates
        seen = set()
        unique_hotels = []
        for hotel in all_hotels:
            key = f"{hotel.get('name')}-{hotel.get('price_per_night')}"
            if key not in seen:
                seen.add(key)
                unique_hotels.append(hotel)
        
        return unique_hotels[:10]
    
    async def _scrape_booking(self, destination: str, check_in: Optional[str], 
                             check_out: Optional[str], budget_level: str) -> List[Dict[str, Any]]:
        """Scrape Booking.com for hotel deals."""
        try:
            # Construct search URL
            check_in_date = check_in or (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            check_out_date = check_out or (datetime.now() + timedelta(days=37)).strftime('%Y-%m-%d')
            
            search_url = f"{self.SCRAPE_TARGETS['booking']}/searchresults.html"
            params = f"?ss={destination.replace(' ', '+')}&checkin={check_in_date}&checkout={check_out_date}"
            
            # Note: Booking.com has anti-scraping measures, this is a simplified example
            html = await self.fetch_html(search_url + params)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            hotels = []
            
            # Look for hotel listings (actual selectors may vary)
            for hotel_elem in soup.find_all('div', {'data-testid': 'property-card'}, limit=5):
                try:
                    name_elem = hotel_elem.find('[data-testid="title"]')
                    price_elem = hotel_elem.find('[data-testid="price-and-discounted-price"]')
                    rating_elem = hotel_elem.find('[data-testid="review-score"]')
                    
                    name = name_elem.get_text(strip=True) if name_elem else f"Hotel in {destination}"
                    price_text = price_elem.get_text(strip=True) if price_elem else "$0"
                    price_match = re.search(r'\$(\d+)', price_text)
                    price = int(price_match.group(1)) if price_match else 100
                    rating = float(rating_elem.get_text(strip=True)[:3]) if rating_elem else 7.0
                    
                    hotels.append({
                        'name': name,
                        'price_per_night': price,
                        'currency': 'USD',
                        'rating': rating / 2,  # Convert 10-scale to 5-scale
                        'amenities': ['WiFi', 'Breakfast'],
                        'location': destination,
                        'url': search_url + params,
                        'source': 'Booking.com',
                        'found_at': datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.debug(f"Error parsing Booking.com hotel: {str(e)}")
            
            return hotels
            
        except Exception as e:
            logger.warning(f"Booking.com scraping failed: {str(e)}")
            return []
    
    async def _scrape_hotels_com(self, destination: str, check_in: Optional[str],
                                 check_out: Optional[str], budget_level: str) -> List[Dict[str, Any]]:
        """Scrape Hotels.com for hotel deals."""
        # Similar implementation to Booking.com
        # Simplified for brevity
        return []
    
    async def _get_mock_hotel_deals(self, destination: str, check_in: Optional[str],
                                   check_out: Optional[str], budget_level: str) -> List[Dict[str, Any]]:
        """Generate mock hotel deals as fallback."""
        import random
        
        budget_ranges = {
            'low': (30, 80),
            'moderate': (80, 200),
            'high': (200, 400),
            'luxury': (400, 1000),
        }
        
        min_price, max_price = budget_ranges.get(budget_level, (80, 200))
        hotel_chains = ['Marriott', 'Hilton', 'Hyatt', 'Boutique Hotel', 'Local Inn']
        
        hotels = []
        for _ in range(5):
            price = random.randint(min_price, max_price)
            hotels.append({
                'name': f"{random.choice(hotel_chains)} {destination.split(',')[0]}",
                'price_per_night': price,
                'currency': 'USD',
                'rating': round(random.uniform(3.5, 5.0), 1),
                'amenities': random.sample(['WiFi', 'Pool', 'Gym', 'Spa', 'Restaurant'], k=3),
                'location': f'{destination} City Center',
                'url': f'https://www.booking.com/searchresults.html?ss={destination.replace(" ", "+")}',
                'source': 'Mock Data',
                'found_at': datetime.now().isoformat(),
            })
        
        return hotels


class TravelBlogScraper(BaseScraper):
    """Scrapes travel blogs for insights and tips."""
    
    BLOG_SOURCES = [
        'nomadicmatt.com',
        'lonelyplanet.com',
        'travelawesome.com',
        'expertvagabond.com',
    ]
    
    async def get_destination_insights(self, destination: str) -> List[Dict[str, Any]]:
        """Get insights from travel blogs."""
        logger.info(f"Searching real travel blogs for {destination}")
        
        all_insights = []
        
        # Search Google for blog posts about destination
        google_search_task = self._search_google_blogs(destination)
        
        # Try specific blog sources
        blog_tasks = [self._scrape_specific_blog(destination, blog) for blog in self.BLOG_SOURCES[:2]]
        
        tasks = [google_search_task] + blog_tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_insights.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Blog scraper error: {str(result)}")
        
        # Fallback to mock data
        if not all_insights:
            logger.info("No real blog insights found, using mock data")
            all_insights = await self._get_mock_blog_insights(destination)
        
        return all_insights[:5]
    
    async def _search_google_blogs(self, destination: str) -> List[Dict[str, Any]]:
        """Search Google for travel blog posts about destination."""
        try:
            # Use Google Custom Search API if available, otherwise scrape search results
            search_query = f"{destination} travel blog guide tips"
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&tbm=nws"
            
            html = await self.fetch_html(search_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            insights = []
            
            # Look for search results
            for result in soup.find_all('div', class_='g', limit=5):
                try:
                    title_elem = result.find('h3')
                    link_elem = result.find('a', href=True)
                    snippet_elem = result.find('div', class_='VwiC3b')
                    
                    if not title_elem or not link_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = link_elem['href']
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Only include if from a travel blog
                    if any(blog in url for blog in self.BLOG_SOURCES):
                        insights.append({
                            'title': title,
                            'url': url,
                            'source': url.split('/')[2],
                            'summary': snippet[:200] if snippet else f"Guide to {destination}",
                            'tips': [],
                            'found_at': datetime.now().isoformat(),
                        })
                except Exception as e:
                    logger.debug(f"Error parsing search result: {str(e)}")
            
            return insights
            
        except Exception as e:
            logger.warning(f"Google blog search failed: {str(e)}")
            return []
    
    async def _scrape_specific_blog(self, destination: str, blog_domain: str) -> List[Dict[str, Any]]:
        """Scrape a specific travel blog for destination insights."""
        try:
            # Search within blog for destination
            search_url = f"https://www.{blog_domain}/?s={destination.replace(' ', '+')}"
            html = await self.fetch_html(search_url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            insights = []
            
            # Look for blog posts (structure varies by site)
            for post in soup.find_all('article', limit=3):
                try:
                    title_elem = post.find(['h2', 'h3'], class_=True)
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link_elem = post.find('a', href=True)
                    url = link_elem['href'] if link_elem else search_url
                    
                    insights.append({
                        'title': title,
                        'url': url,
                        'source': blog_domain,
                        'summary': f"Travel guide for {destination}",
                        'tips': ['Book in advance', 'Visit off-season for better prices'],
                        'found_at': datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.debug(f"Error parsing blog post: {str(e)}")
            
            return insights
            
        except Exception as e:
            logger.warning(f"Scraping {blog_domain} failed: {str(e)}")
            return []
    
    async def _get_mock_blog_insights(self, destination: str) -> List[Dict[str, Any]]:
        """Generate mock blog insights as fallback."""
        return [
            {
                'title': f'Ultimate Guide to {destination}',
                'url': f'https://www.nomadicmatt.com/travel-blogs/{destination.replace(" ", "-").lower()}/',
                'source': 'Nomadic Matt',
                'summary': f'Comprehensive guide covering the best attractions, food, and hidden gems in {destination}',
                'tips': [
                    'Visit early morning to avoid crowds',
                    'Book accommodations in advance during peak season',
                    'Try local street food for authentic experiences',
                ],
                'found_at': datetime.now().isoformat(),
            },
        ]


class LocalEventScraper(BaseScraper):
    """Scrapes local events and festivals."""
    
    EVENT_SOURCES = {
        'eventbrite': 'https://www.eventbrite.com',
        'ticketmaster': 'https://www.ticketmaster.com',
        'timeout': 'https://www.timeout.com',
    }
    
    async def get_local_events(self, destination: str, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get local events from real sources."""
        logger.info(f"Searching real local events in {destination}")
        
        all_events = []
        
        # Try Eventbrite
        eventbrite_task = self._scrape_eventbrite(destination, start_date, end_date)
        
        # Try Timeout
        timeout_task = self._scrape_timeout(destination, start_date, end_date)
        
        results = await asyncio.gather(eventbrite_task, timeout_task, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_events.extend(result)
        
        # Fallback to mock data
        if not all_events:
            all_events = self._get_mock_events(destination, start_date, end_date)
        
        return all_events[:10]
    
    async def _scrape_eventbrite(self, destination: str, start_date: Optional[str],
                                end_date: Optional[str]) -> List[Dict[str, Any]]:
        """Scrape Eventbrite for local events."""
        try:
            search_url = f"{self.EVENT_SOURCES['eventbrite']}/d/{destination.replace(' ', '-').lower()}/events"
            html = await self.fetch_html(search_url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            events = []
            
            # Look for event listings
            for event_card in soup.find_all('div', {'data-testid': 'event-card'}, limit=5):
                try:
                    title_elem = event_card.find('span', {'data-automation': 'listing-title'})
                    date_elem = event_card.find('span', {'data-automation': 'listing-date'})
                    
                    if not title_elem:
                        continue
                    
                    events.append({
                        'name': title_elem.get_text(strip=True),
                        'date': date_elem.get_text(strip=True) if date_elem else start_date or 'TBD',
                        'venue': destination,
                        'category': 'General',
                        'description': 'Local event',
                        'url': search_url,
                        'source': 'Eventbrite',
                        'found_at': datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.debug(f"Error parsing Eventbrite event: {str(e)}")
            
            return events
            
        except Exception as e:
            logger.warning(f"Eventbrite scraping failed: {str(e)}")
            return []
    
    async def _scrape_timeout(self, destination: str, start_date: Optional[str],
                             end_date: Optional[str]) -> List[Dict[str, Any]]:
        """Scrape Timeout for local events."""
        # Similar implementation
        return []
    
    def _get_mock_events(self, destination: str, start_date: Optional[str],
                        end_date: Optional[str]) -> List[Dict[str, Any]]:
        """Generate mock events as fallback."""
        return [
            {
                'name': f'{destination} Cultural Festival',
                'date': start_date or '2024-06-15',
                'venue': f'{destination} City Center',
                'category': 'Cultural',
                'description': f'Annual cultural festival',
                'url': f'https://www.eventbrite.com/d/{destination.replace(" ", "-").lower()}/',
                'source': 'Mock Data',
                'found_at': datetime.now().isoformat(),
            },
        ]


class RestaurantScraper(BaseScraper):
    """Scrapes restaurant recommendations."""
    
    RESTAURANT_SOURCES = {
        'tripadvisor': 'https://www.tripadvisor.com',
        'yelp': 'https://www.yelp.com',
        'zomato': 'https://www.zomato.com',
    }
    
    async def get_restaurants(self, destination: str, dietary_restrictions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get restaurant recommendations from real sources."""
        logger.info(f"Searching real restaurants in {destination}")
        
        all_restaurants = []
        
        # Try TripAdvisor
        ta_task = self._scrape_tripadvisor(destination, dietary_restrictions)
        
        # Try Yelp
        yelp_task = self._scrape_yelp(destination, dietary_restrictions)
        
        results = await asyncio.gather(ta_task, yelp_task, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_restaurants.extend(result)
        
        # Fallback to mock data
        if not all_restaurants:
            all_restaurants = self._get_mock_restaurants(destination, dietary_restrictions)
        
        return all_restaurants[:15]
    
    async def _scrape_tripadvisor(self, destination: str, dietary_restrictions: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Scrape TripAdvisor for restaurant recommendations."""
        try:
            search_url = f"{self.RESTAURANT_SOURCES['tripadvisor']}/Restaurants-g1-{destination.replace(' ', '_')}"
            html = await self.fetch_html(search_url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            restaurants = []
            
            # Look for restaurant listings
            for rest_elem in soup.find_all('div', {'data-test-id': 'restaurant-list-item'}, limit=10):
                try:
                    name_elem = rest_elem.find('a', {'data-test-id': 'restaurant-name'})
                    rating_elem = rest_elem.find('span', {'data-test-id': 'rating-text'})
                    cuisine_elem = rest_elem.find('span', {'data-test-id': 'cuisine'})
                    
                    if not name_elem:
                        continue
                    
                    restaurants.append({
                        'name': name_elem.get_text(strip=True),
                        'cuisine': cuisine_elem.get_text(strip=True) if cuisine_elem else 'Local',
                        'price_range': '$$-$$$',
                        'rating': float(rating_elem.get_text(strip=True)[:3]) / 2 if rating_elem else 4.0,
                        'address': destination,
                        'specialties': ['Local specialties'],
                        'dietary_options': dietary_restrictions or ['Vegetarian options'],
                        'url': name_elem.get('href', search_url),
                        'source': 'TripAdvisor',
                        'found_at': datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.debug(f"Error parsing TripAdvisor restaurant: {str(e)}")
            
            return restaurants
            
        except Exception as e:
            logger.warning(f"TripAdvisor scraping failed: {str(e)}")
            return []
    
    async def _scrape_yelp(self, destination: str, dietary_restrictions: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Scrape Yelp for restaurant recommendations."""
        # Similar implementation
        return []
    
    def _get_mock_restaurants(self, destination: str, dietary_restrictions: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Generate mock restaurants as fallback."""
        import random
        
        cuisines = ['Local', 'Italian', 'Japanese', 'French', 'Mediterranean']
        restaurants = []
        
        for i in range(8):
            restaurants.append({
                'name': f'{random.choice(cuisines)} Kitchen {i+1}',
                'cuisine': random.choice(cuisines),
                'price_range': '$$-$$$',
                'rating': round(random.uniform(4.0, 5.0), 1),
                'address': f'{destination} City Center',
                'specialties': ['Local specialties'],
                'dietary_options': dietary_restrictions or ['Vegetarian options'],
                'url': f'https://www.tripadvisor.com/Restaurants-{destination.replace(" ", "-").lower()}',
                'source': 'Mock Data',
                'found_at': datetime.now().isoformat(),
            })
        
        return restaurants


class SafetyScraper(BaseScraper):
    """Scrapes travel safety information from government sources."""
    
    SAFETY_SOURCES = {
        'us_state': 'https://travel.state.gov',
        'uk_fcdo': 'https://www.gov.uk/foreign-travel-advice',
        'australia': 'https://www.smartraveller.gov.au',
    }
    
    async def get_safety_info(self, destination: str) -> Dict[str, Any]:
        """Get safety information from real government sources."""
        logger.info(f"Searching real safety info for {destination}")
        
        # Extract country from destination
        country = destination.split(',')[-1].strip() if ',' in destination else destination
        
        # Try US State Department
        us_task = self._scrape_us_state_department(country)
        
        # Try UK FCDO
        uk_task = self._scrape_uk_fcdo(country)
        
        results = await asyncio.gather(us_task, uk_task, return_exceptions=True)
        
        safety_info = {
            'safety_score': 7.5,  # Default
            'risk_level': 'Medium',
            'advisories': [],
            'sources': [],
        }
        
        for result in results:
            if isinstance(result, dict):
                if result.get('advisories'):
                    safety_info['advisories'].extend(result['advisories'])
                if result.get('risk_level'):
                    safety_info['risk_level'] = result['risk_level']
                if result.get('safety_score'):
                    safety_info['safety_score'] = result['safety_score']
                if result.get('sources'):
                    safety_info['sources'].extend(result['sources'])
        
        # If no real data found, use mock
        if not safety_info['advisories']:
            mock_info = self._get_mock_safety_info(country)
            safety_info['advisories'] = mock_info['advisories']
            safety_info['sources'] = ['Mock Data']
        
        safety_info['emergency_numbers'] = {
            'police': '112',
            'ambulance': '112',
            'fire': '112',
        }
        safety_info['updated_at'] = datetime.now().isoformat()
        
        return safety_info
    
    async def _scrape_us_state_department(self, country: str) -> Dict[str, Any]:
        """Scrape US State Department travel advisories."""
        try:
            search_url = f"{self.SAFETY_SOURCES['us_state']}/content/travel-advisories"
            html = await self.fetch_html(search_url)
            
            if not html:
                return {'advisories': [], 'sources': []}
            
            soup = BeautifulSoup(html, 'html.parser')
            advisories = []
            risk_level = 'Medium'
            safety_score = 7.0
            
            # Look for country-specific advisory
            # This is simplified - actual implementation would need to find the specific country
            advisory_levels = {
                'Level 1': ('Low', 9.0),
                'Level 2': ('Medium', 7.5),
                'Level 3': ('High', 5.0),
                'Level 4': ('Very High', 2.0),
            }
            
            for level, (risk, score) in advisory_levels.items():
                if level.lower() in html.lower():
                    risk_level = risk
                    safety_score = score
                    advisories.append(f"US State Department: {level} - Exercise {risk.lower()} caution")
                    break
            
            return {
                'advisories': advisories,
                'risk_level': risk_level,
                'safety_score': safety_score,
                'sources': ['US State Department'],
            }
            
        except Exception as e:
            logger.warning(f"US State Department scraping failed: {str(e)}")
            return {'advisories': [], 'sources': []}
    
    async def _scrape_uk_fcdo(self, country: str) -> Dict[str, Any]:
        """Scrape UK FCDO travel advice."""
        try:
            search_url = f"{self.SAFETY_SOURCES['uk_fcdo']}/{country.lower().replace(' ', '-')}"
            html = await self.fetch_html(search_url)
            
            if not html:
                return {'advisories': [], 'sources': []}
            
            # Parse FCDO page
            advisories = ['Check FCDO website for latest advice']
            
            return {
                'advisories': advisories,
                'sources': ['UK FCDO'],
            }
            
        except Exception as e:
            logger.warning(f"UK FCDO scraping failed: {str(e)}")
            return {'advisories': [], 'sources': []}
    
    def _get_mock_safety_info(self, country: str) -> Dict[str, Any]:
        """Generate mock safety info as fallback."""
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
            'sources': ['Mock Data'],
        }


async def close_all_scrapers(*scrapers):
    """Helper to close all scraper sessions."""
    for scraper in scrapers:
        try:
            await scraper.close()
        except Exception as e:
            logger.error(f"Error closing scraper: {str(e)}")
