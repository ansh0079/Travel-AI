"""
Nightlife & Entertainment Service
Provides information about evening activities, bars, clubs, and entertainment
"""

from typing import List, Dict, Any, Optional


class NightlifeService:
    """Service for nightlife and entertainment information"""
    
    def get_nightlife_scene(self, destination: str) -> Dict[str, Any]:
        """Get overview of nightlife in a destination"""
        
        nightlife_db = {
            "tokyo": {
                "scene": "Incredible variety - from tiny izakayas to massive clubs",
                "areas": ["Shibuya", "Shinjuku", "Roppongi", "Golden Gai", "Ebisu"],
                "styles": ["Izakayas", "Karaoke", "Clubs", "Jazz bars", "Themed cafes"],
                "famous_for": "Tiny bars in Golden Gai, karaoke everywhere, robot restaurants",
                "closing_time": "Most places 11 PM - 5 AM (no last call!)",
                "price_range": "$$-$$$$",
                "safety": "Very safe, even at night",
                "notes": "Last trains around midnight, taxis expensive after"
            },
            "bangkok": {
                "scene": "Famous nightlife - from street bars to rooftop clubs",
                "areas": ["Khao San Road", "Sukhumvit", "Thonglor", "RCA", "Chinatown"],
                "styles": ["Rooftop bars", "Nightclubs", "Street bars", "Gogo bars", "Live music"],
                "famous_for": "Rooftop bars, street drinking, full moon parties",
                "closing_time": "2 AM officially (often later)",
                "price_range": "$-$$$",
                "safety": "Generally safe, watch drinks",
                "notes": "Great happy hours, ladyboy shows famous"
            },
            "berlin": {
                "scene": "Legendary club scene, techno capital of the world",
                "areas": ["Kreuzberg", "Friedrichshain", "Neukölln", "Mitte"],
                "styles": ["Techno clubs", "Beer gardens", "Live music", "Alternative bars"],
                "famous_for": "Berghain, 24-hour clubs, warehouse parties",
                "closing_time": "Weekend clubs often open 48+ hours",
                "price_range": "$-$$",
                "safety": "Very safe",
                "notes": "Clubs are selective at door, no photos policy common"
            },
            "ibiza": {
                "scene": "Party capital of the world",
                "areas": ["Ibiza Town", "San Antonio", "Playa d'en Bossa"],
                "styles": ["Superclubs", "Beach clubs", "Sunset bars", "Boat parties"],
                "famous_for": "World's best DJs, foam parties, sunset at Café del Mar",
                "closing_time": "Clubs 6 AM, after-parties continue",
                "price_range": "$$$-$$$$",
                "safety": "Safe but expensive",
                "notes": "Entry fees €30-80, drinks €15+, pre-party at hostels"
            },
            "new york": {
                "scene": "Something for everyone - jazz, rooftop, speakeasies",
                "areas": ["Lower East Side", "Williamsburg", "Meatpacking", "East Village"],
                "styles": ["Speakeasies", "Rooftop bars", "Jazz clubs", "Dive bars", "Clubs"],
                "famous_for": "Rooftop views, jazz history, endless options",
                "closing_time": "4 AM last call",
                "price_range": "$$-$$$$",
                "safety": "Generally safe, stick to populated areas",
                "notes": "Check dress codes, reservations recommended"
            },
            "london": {
                "scene": "Historic pubs, trendy bars, world-class clubs",
                "areas": ["Soho", "Shoreditch", "Camden", "Brixton", "Notting Hill"],
                "styles": ["Pubs", "Cocktail bars", "Clubs", "Live music venues"],
                "famous_for": "Historic pubs, pub crawls, diverse music scene",
                "closing_time": "11 PM pubs, 3-6 AM clubs",
                "price_range": "$$-$$$$",
                "safety": "Very safe",
                "notes": "Pubs close early - plan accordingly!"
            },
            "las vegas": {
                "scene": "24/7 party, world-famous clubs and shows",
                "areas": ["The Strip", "Downtown/Fremont St"],
                "styles": ["Mega clubs", "Pool parties", "Casino bars", "Shows"],
                "famous_for": "DJ residencies, pool parties, endless entertainment",
                "closing_time": "24 hours - never closes!",
                "price_range": "$$$-$$$$",
                "safety": "Safe on Strip, watch belongings",
                "notes": "Guest list for clubs, drink prices high"
            },
            "rio de janeiro": {
                "scene": "Samba, beach bars, vibrant street life",
                "areas": ["Lapa", "Ipanema", "Copacabana", "Leblon"],
                "styles": ["Samba clubs", "Beach kiosks", "Live music", "Street parties"],
                "famous_for": "Samba, Carnival, caipirinhas on the beach",
                "closing_time": "5 AM, street parties go all night",
                "price_range": "$-$$",
                "safety": "Be cautious, avoid displaying valuables",
                "notes": "Street parties (blocos) are amazing"
            }
        }
        
        dest_lower = destination.lower()
        for key, scene in nightlife_db.items():
            if key in dest_lower:
                return {
                    "destination": destination,
                    "nightlife": scene,
                    "source": "local_knowledge"
                }
        
        return {
            "destination": destination,
            "nightlife": {
                "scene": "Research local options",
                "areas": ["City center", "Ask locals"],
                "styles": ["Varies by destination"],
                "famous_for": "Discover local favorites",
                "closing_time": "Varies",
                "price_range": "$$",
                "safety": "Research safety advice",
                "notes": "Ask your accommodation for recommendations"
            },
            "source": "general"
        }
    
    def get_venue_recommendations(
        self,
        destination: str,
        venue_type: str = "any",  # bar, club, lounge, live_music, any
        budget: str = "moderate",
        style: str = "any"  # upscale, casual, trendy, local, any
    ) -> List[Dict[str, Any]]:
        """Get specific venue recommendations"""
        
        # Mock venue database
        venues = self._generate_mock_venues(destination, venue_type)
        
        # Filter by budget
        price_ranges = {
            "low": ["$", "$$"],
            "moderate": ["$$", "$$$"],
            "high": ["$$$", "$$$$"],
            "luxury": ["$$$$"]
        }
        allowed_prices = price_ranges.get(budget, ["$$", "$$$"])
        venues = [v for v in venues if v.get("price_level") in allowed_prices]
        
        # Filter by style
        if style != "any":
            venues = [v for v in venues if v.get("style") == style]
        
        # Sort by rating
        venues.sort(key=lambda x: x.get("rating", 0), reverse=True)
        
        return venues[:8]
    
    def get_happy_hours(self, destination: str) -> List[Dict[str, Any]]:
        """Get happy hour deals in a destination"""
        
        happy_hours_db = {
            "bangkok": [
                {"venue": "Sky Bar at Lebua", "time": "5-7 PM", "deal": "2-for-1 cocktails", "price": "400 THB"},
                {"venue": "Octave Rooftop", "time": "5-7 PM", "deal": "Buy 1 get 1 drinks", "price": "300 THB"},
                {"venue": "The Speakeasy", "time": "4-8 PM", "deal": "Half price drinks", "price": "200 THB"},
            ],
            "new york": [
                {"venue": "Rooftop bars", "time": "4-7 PM", "deal": "$5-8 drinks", "price": "$8"},
                {"venue": "Dive bars", "time": "All day", "deal": "Cheap beer", "price": "$4"},
                {"venue": "Hotel bars", "time": "5-8 PM", "deal": "Complimentary snacks", "price": "$12"},
            ],
            "london": [
                {"venue": "Wetherspoons", "time": "Before 11 PM", "deal": "Cheap pints", "price": "£3"},
                {"venue": "Happy hour bars", "time": "5-8 PM", "deal": "2-for-1", "price": "£8"},
            ],
            "default": [
                {"venue": "Local bars", "time": "5-7 PM", "deal": "Happy hour specials", "price": "Check locally"},
            ]
        }
        
        dest_lower = destination.lower()
        for key, deals in happy_hours_db.items():
            if key in dest_lower:
                return deals
        
        return happy_hours_db["default"]
    
    def get_safety_tips(self, destination: str) -> List[str]:
        """Get nightlife safety tips for a destination"""
        
        general_tips = [
            "Watch your drink at all times - spiking can happen anywhere",
            "Stay with friends and have a meeting point if separated",
            "Use official taxis or rideshare apps, avoid unlicensed cabs",
            "Keep valuables secure and minimize what you carry",
            "Know the emergency number for your destination",
            "Let someone know where you're going",
            "Trust your instincts - leave if something feels off"
        ]
        
        destination_specific = {
            "bangkok": [
                "Be careful on Khao San Road - many scams",
                "Ping pong shows are scams - avoid",
                "Tuk-tuks at night may overcharge significantly"
            ],
            "barcelona": [
                "Watch for pickpockets in busy nightlife areas",
                "Las Ramblas at night can be sketchy",
                "Stick to well-lit, populated streets"
            ],
            "rio de janeiro": [
                "Don't walk on beaches at night",
                "Avoid flashing expensive items",
                "Stick to busy areas in Lapa"
            ]
        }
        
        dest_lower = destination.lower()
        specific = []
        for key, tips in destination_specific.items():
            if key in dest_lower:
                specific = tips
                break
        
        return specific + general_tips
    
    def _generate_mock_venues(self, destination: str, venue_type: str) -> List[Dict[str, Any]]:
        """Generate mock venue data"""
        import random
        
        venue_templates = {
            "bar": [
                {"name": "The Local Pub", "type": "bar", "style": "casual"},
                {"name": "Skyline Rooftop", "type": "bar", "style": "upscale"},
                {"name": "Craft Beer Corner", "type": "bar", "style": "trendy"},
                {"name": "Cocktail Lounge", "type": "bar", "style": "upscale"},
            ],
            "club": [
                {"name": "Pulse Nightclub", "type": "club", "style": "trendy"},
                {"name": "Underground Warehouse", "type": "club", "style": "local"},
                {"name": "VIP Club", "type": "club", "style": "upscale"},
            ],
            "live_music": [
                {"name": "Jazz Corner", "type": "live_music", "style": "local"},
                {"name": "Rock Arena", "type": "live_music", "style": "trendy"},
                {"name": "Acoustic Cafe", "type": "live_music", "style": "casual"},
            ],
            "lounge": [
                {"name": "Chill Lounge", "type": "lounge", "style": "upscale"},
                {"name": "Hookah Garden", "type": "lounge", "style": "trendy"},
            ]
        }
        
        if venue_type == "any":
            all_venues = []
            for venues in venue_templates.values():
                all_venues.extend(venues)
            templates = all_venues
        else:
            templates = venue_templates.get(venue_type, venue_templates["bar"])
        
        venues = []
        for i in range(8):
            base = random.choice(templates).copy()
            base["id"] = f"venue_{i}"
            base["rating"] = round(random.uniform(3.8, 4.9), 1)
            base["price_level"] = random.choice(["$", "$$", "$$$", "$$$$"])
            base["review_count"] = random.randint(50, 2000)
            base["address"] = f"{random.randint(1, 999)} Night Street"
            base["open_hours"] = "8 PM - 4 AM"
            base["music_type"] = random.choice(["Top 40", "Electronic", "Hip Hop", "Rock", "Jazz", "Mixed"])
            base["age_requirement"] = "18+" if random.random() > 0.3 else "21+"
            base["cover_charge"] = random.choice(["Free", "$10", "$20", "$30", "Varies"])
            venues.append(base)
        
        return venues


# Convenience function
def get_nightlife_guide(destination: str, interests: List[str] = None) -> Dict[str, Any]:
    """Get comprehensive nightlife guide"""
    service = NightlifeService()
    
    # Determine preferred venue types from interests
    venue_type = "any"
    if interests:
        if "nightlife" in interests and "music" in interests:
            venue_type = "live_music"
        elif "nightlife" in interests:
            venue_type = "club"
    
    return {
        "destination": destination,
        "scene_overview": service.get_nightlife_scene(destination),
        "venue_recommendations": service.get_venue_recommendations(destination, venue_type),
        "happy_hours": service.get_happy_hours(destination),
        "safety_tips": service.get_safety_tips(destination)
    }
