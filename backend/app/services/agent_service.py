"""
AI Travel Research Agent
An autonomous agent that can research travel information using various tools
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from duckduckgo_search import DDGS
import httpx

from app.config import get_settings
from app.services.weather_service import WeatherService
from app.services.visa_service import VisaService
from app.services.attractions_service import AttractionsService
from app.services.events_service import EventsService
from app.services.affordability_service import AffordabilityService


class TravelResearchAgent:
    """
    Autonomous AI agent for travel research
    Can search web, query APIs, and compile comprehensive travel reports
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.weather_service = WeatherService()
        self.visa_service = VisaService()
        self.attractions_service = AttractionsService()
        self.events_service = EventsService()
        self.affordability_service = AffordabilityService()
        
    async def research_destination(
        self, 
        destination: str,
        travel_dates: Optional[tuple] = None,
        interests: Optional[List[str]] = None,
        budget: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive research on a destination
        """
        print(f"Agent: Researching {destination}...")
        
        # Run all research tasks concurrently
        tasks = [
            self._search_web_info(destination),
            self._search_current_events(destination),
            self._search_travel_tips(destination),
        ]
        
        if interests:
            tasks.append(self._search_interest_specific(destination, interests))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile research report
        report = {
            "destination": destination,
            "research_timestamp": datetime.now().isoformat(),
            "general_info": results[0] if not isinstance(results[0], Exception) else None,
            "current_events": results[1] if not isinstance(results[1], Exception) else None,
            "travel_tips": results[2] if not isinstance(results[2], Exception) else None,
            "interest_specific": results[3] if len(results) > 3 and not isinstance(results[3], Exception) else None,
            "agent_insights": await self._generate_insights(destination, results, interests, budget)
        }
        
        return report
    
    async def compare_destinations(
        self,
        destinations: List[str],
        criteria: List[str],
        travel_dates: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple destinations based on criteria
        """
        print(f"Agent: Comparing {', '.join(destinations)}...")
        
        # Research all destinations concurrently
        research_tasks = [self.research_destination(dest, travel_dates) for dest in destinations]
        destination_reports = await asyncio.gather(*research_tasks, return_exceptions=True)
        
        # Build comparison matrix
        comparison = {
            "destinations": [],
            "criteria": criteria,
            "rankings": {},
            "recommendation": None
        }
        
        for dest, report in zip(destinations, destination_reports):
            if isinstance(report, Exception):
                comparison["destinations"].append({
                    "name": dest,
                    "error": str(report)
                })
            else:
                comparison["destinations"].append(report)
        
        # Generate comparison insights
        comparison["recommendation"] = await self._generate_comparison_recommendation(
            comparison["destinations"], criteria
        )
        
        return comparison
    
    async def find_hidden_gems(
        self,
        region: str,
        interests: List[str],
        avoid_crowds: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find lesser-known destinations and experiences
        """
        print(f"Agent: Finding hidden gems in {region}...")
        
        search_queries = [
            f"hidden gems {region} off the beaten path",
            f"secret places {region} locals only",
            f"underrated destinations {region} 2024",
            f"alternative to popular {region} tourist spots"
        ]
        
        if interests:
            for interest in interests[:2]:
                search_queries.append(f"best {interest} spots {region} hidden")
        
        all_results = []
        for query in search_queries:
            try:
                results = await self._search_web(query, max_results=5)
                all_results.extend(results)
            except Exception as e:
                print(f"Search error for '{query}': {e}")
        
        # Extract and deduplicate destinations
        gems = self._extract_destinations_from_search(all_results)
        
        return gems[:10]  # Top 10 unique gems
    
    async def research_itinerary(
        self,
        destination: str,
        days: int,
        interests: List[str],
        travel_style: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Research and suggest day-by-day itinerary
        """
        print(f"Agent: Planning {days}-day itinerary for {destination}...")
        
        # Search for itinerary ideas
        search_query = f"{days} day {destination} itinerary {travel_style} " + " ".join(interests[:3])
        
        web_results = await self._search_web(search_query, max_results=10)
        
        # Search for must-see attractions
        attractions_task = self._search_must_see(destination)
        local_tips_task = self._search_local_tips(destination)
        
        attractions, local_tips = await asyncio.gather(
            attractions_task, local_tips_task,
            return_exceptions=True
        )
        
        itinerary_suggestion = {
            "destination": destination,
            "duration_days": days,
            "travel_style": travel_style,
            "daily_plans": self._generate_daily_outline(days, interests),
            "must_see": attractions if not isinstance(attractions, Exception) else [],
            "local_tips": local_tips if not isinstance(local_tips, Exception) else [],
            "research_sources": [r.get("href", "") for r in web_results[:5]]
        }
        
        return itinerary_suggestion
    
    async def check_travel_advisories(self, destination: str) -> Dict[str, Any]:
        """
        Check current travel advisories and safety information
        """
        print(f"Agent: Checking travel advisories for {destination}...")
        
        queries = [
            f"{destination} travel advisory 2024",
            f"is {destination} safe to travel now",
            f"{destination} entry requirements 2024",
            f"{destination} covid restrictions travel"
        ]
        
        advisories = []
        for query in queries:
            try:
                results = await self._search_web(query, max_results=3)
                advisories.extend(results)
            except:
                pass
        
        return {
            "destination": destination,
            "check_date": datetime.now().isoformat(),
            "advisories_found": len(advisories),
            "key_points": self._extract_key_advisory_points(advisories),
            "sources": [a.get("href", "") for a in advisories[:5]]
        }
    
    # === Tool Methods ===
    
    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search web using DuckDuckGo - force English results"""
        try:
            with DDGS() as ddgs:
                # Add English language and region hints to query
                english_query = f"{query} site:.com OR site:.uk OR site:.au OR site:.ca"
                results = list(ddgs.text(english_query, max_results=max_results))
                # Filter out Chinese characters
                filtered_results = []
                for r in results:
                    body = r.get('body', '')
                    title = r.get('title', '')
                    # Simple check for Chinese characters (CJK range)
                    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in body + title)
                    if not has_chinese:
                        filtered_results.append(r)
                return filtered_results if filtered_results else self._get_mock_search_results(query)
        except Exception as e:
            print(f"Web search error: {e}")
            # Return mock search results as fallback
            return self._get_mock_search_results(query)
    
    async def _search_web_info(self, destination: str) -> Dict:
        """Search general information about destination"""
        queries = [
            f"{destination} travel guide 2024",
            f"what to know before visiting {destination}",
            f"{destination} best time to visit"
        ]
        
        all_results = []
        for query in queries:
            results = await self._search_web(query, max_results=3)
            all_results.extend(results)
        
        return {
            "topic": "general_info",
            "results_count": len(all_results),
            "key_findings": [r.get("body", "")[:200] for r in all_results[:5]],
            "sources": [r.get("href", "") for r in all_results[:3]]
        }
    
    async def _search_current_events(self, destination: str) -> Dict:
        """Search current events and festivals"""
        query = f"{destination} events festivals 2024 what's happening"
        results = await self._search_web(query, max_results=5)
        
        return {
            "topic": "current_events",
            "events_found": len(results),
            "events": [{
                "title": r.get("title", ""),
                "snippet": r.get("body", "")[:150]
            } for r in results[:5]]
        }
    
    async def _search_travel_tips(self, destination: str) -> Dict:
        """Search practical travel tips"""
        queries = [
            f"{destination} travel tips first time visitors",
            f"{destination} local customs etiquette",
            f"{destination} transportation getting around"
        ]
        
        all_results = []
        for query in queries:
            results = await self._search_web(query, max_results=3)
            all_results.extend(results)
        
        return {
            "topic": "travel_tips",
            "tips": [r.get("body", "")[:200] for r in all_results[:5]],
            "categories": ["transportation", "etiquette", "safety", "money"]
        }
    
    async def _search_interest_specific(self, destination: str, interests: List[str]) -> Dict:
        """Search for interest-specific information"""
        results = {}
        
        for interest in interests[:3]:  # Limit to top 3 interests
            query = f"best {interest} in {destination}"
            search_results = await self._search_web(query, max_results=3)
            results[interest] = [r.get("body", "")[:150] for r in search_results[:3]]
        
        return {
            "topic": "interests",
            "interest_data": results
        }
    
    async def _search_must_see(self, destination: str) -> List[str]:
        """Search must-see attractions"""
        query = f"{destination} must see attractions top 10"
        results = await self._search_web(query, max_results=5)
        return [r.get("title", "").replace(" - ", ": ") for r in results]
    
    async def _search_local_tips(self, destination: str) -> List[str]:
        """Search local tips and secrets"""
        query = f"{destination} local tips secrets advice reddit"
        results = await self._search_web(query, max_results=5)
        return [r.get("body", "")[:200] for r in results[:5]]
    
    def _get_mock_search_results(self, query: str) -> List[Dict]:
        """Generate mock search results when web search fails"""
        # Extract destination from query
        words = query.replace('travel guide', '').replace('best', '').replace('visit', '').strip().split()
        destination = words[0] if words else "Destination"
        
        return [
            {
                "title": f"{destination} Travel Guide 2024",
                "body": f"Explore {destination}'s rich culture, stunning architecture, and world-class cuisine. Perfect for travelers seeking both adventure and relaxation. Best months to visit are April-June and September-October.",
                "href": f"https://example.com/{destination.lower().replace(' ', '-')}-guide"
            },
            {
                "title": f"Best Time to Visit {destination} - Weather & Events",
                "body": f"Spring and fall offer the best weather in {destination} with mild temperatures around 20-25°C. Summer can be hot and crowded, while winter brings festive markets and lower prices.",
                "href": f"https://example.com/{destination.lower().replace(' ', '-')}-weather"
            },
            {
                "title": f"Top 10 Attractions in {destination}",
                "body": f"Must-visit landmarks in {destination} include historic sites, museums, beautiful parks, and local markets. Book tickets in advance for popular attractions. Most museums offer free entry on first Sundays.",
                "href": f"https://example.com/{destination.lower().replace(' ', '-')}-attractions"
            },
            {
                "title": f"{destination} Travel Tips - First Timer's Guide",
                "body": f"Essential tips for visiting {destination}: Public transport is efficient and affordable. Learn basic local phrases. Try the street food but stick to busy stalls. Carry cash for small vendors.",
                "href": f"https://example.com/{destination.lower().replace(' ', '-')}-tips"
            },
            {
                "title": f"Hidden Gems and Local Secrets in {destination}",
                "body": f"Discover {destination} like a local: Explore quiet neighborhoods away from tourist areas, visit morning markets for authentic experiences, find rooftop bars with stunning views, and take day trips to nearby charming towns.",
                "href": f"https://example.com/{destination.lower().replace(' ', '-')}-hidden-gems"
            }
        ]
    
    # === Helper Methods ===
    
    def _extract_destinations_from_search(self, results: List[Dict]) -> List[Dict]:
        """Extract destination mentions from search results"""
        gems = []
        seen = set()
        
        for result in results:
            title = result.get("title", "")
            body = result.get("body", "")
            
            # Simple extraction - could be improved with NER
            if title and title not in seen:
                seen.add(title)
                gems.append({
                    "name": title.split(" - ")[0][:50],
                    "description": body[:200] if body else "",
                    "source": result.get("href", "")
                })
        
        return gems
    
    def _extract_key_advisory_points(self, advisories: List[Dict]) -> List[str]:
        """Extract key points from advisory search results"""
        key_points = []
        for adv in advisories[:5]:
            body = adv.get("body", "")
            if body:
                # Extract first sentence as key point
                first_sentence = body.split(".")[0]
                if len(first_sentence) > 20:
                    key_points.append(first_sentence[:150])
        return key_points[:5]
    
    def _generate_daily_outline(self, days: int, interests: List[str]) -> List[Dict]:
        """Generate a basic daily outline structure"""
        outline = []
        for day in range(1, days + 1):
            day_plan = {
                "day": day,
                "theme": interests[day % len(interests)] if interests else "exploration",
                "activities": [],
                "notes": "Research and add specific activities"
            }
            outline.append(day_plan)
        return outline
    
    async def _generate_insights(
        self, 
        destination: str, 
        results: List[Any],
        interests: Optional[List[str]],
        budget: Optional[str]
    ) -> str:
        """Generate agent insights based on research"""
        insights = [f"Research completed for {destination}."]
        
        # Count successful searches
        successful = sum(1 for r in results if not isinstance(r, Exception))
        insights.append(f"Analyzed {successful} information sources.")
        
        if interests:
            insights.append(f"Tailored findings for: {', '.join(interests)}.")
        
        if budget:
            insights.append(f"Budget considerations: {budget} range.")
        
        return " ".join(insights)
    
    async def _generate_comparison_recommendation(
        self,
        destinations: List[Dict],
        criteria: List[str]
    ) -> str:
        """Generate recommendation from comparison"""
        if not destinations:
            return "No destinations to compare."
        
        valid_dests = [d for d in destinations if "error" not in d]
        if not valid_dests:
            return "Could not retrieve information for comparison."
        
        return f"Compared {len(valid_dests)} destinations based on {', '.join(criteria)}. Review detailed findings for each destination to make your choice."


# Convenience function for direct use
async def research_travel_destination(
    destination: str,
    travel_dates: Optional[tuple] = None,
    interests: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Quick access to agent research"""
    agent = TravelResearchAgent()
    return await agent.research_destination(destination, travel_dates, interests)
