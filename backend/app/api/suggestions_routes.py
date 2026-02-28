"""Smart Suggestions — returns similar / alternative cities based on a curated map.

Endpoint:  GET /api/v1/suggestions/similar?cities=paris,tokyo&limit=4

No LLM required — pure static data so it works on the free Render tier.
"""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/v1/suggestions", tags=["suggestions"])

# ---------------------------------------------------------------------------
# Curated similarity map
# key   = normalised city name (lower, spaces)
# value = list of (city, country, one-line reason) tuples
# ---------------------------------------------------------------------------
SIMILAR: dict[str, list[dict]] = {
    "paris": [
        {"city": "Lyon", "country": "France", "reason": "Vibrant food scene and beautiful old town — Paris without the crowds"},
        {"city": "Bruges", "country": "Belgium", "reason": "Romantic medieval city with canals and world-class chocolate"},
        {"city": "Prague", "country": "Czech Republic", "reason": "Stunning baroque architecture and buzzing nightlife at half the cost"},
    ],
    "tokyo": [
        {"city": "Osaka", "country": "Japan", "reason": "Japan's kitchen city — livelier street food scene and friendlier locals"},
        {"city": "Seoul", "country": "South Korea", "reason": "K-pop culture, fantastic street food, and cutting-edge tech"},
        {"city": "Taipei", "country": "Taiwan", "reason": "Night markets, bubble tea, and a blend of Japanese and Chinese culture"},
    ],
    "bali": [
        {"city": "Lombok", "country": "Indonesia", "reason": "Quieter beaches and volcanic scenery — Bali a decade ago"},
        {"city": "Phuket", "country": "Thailand", "reason": "Tropical beaches with more nightlife options and easier connections"},
        {"city": "Koh Samui", "country": "Thailand", "reason": "Relaxed island vibe, clear waters, and great beach clubs"},
    ],
    "london": [
        {"city": "Dublin", "country": "Ireland", "reason": "English-speaking with a friendlier pub culture and rich literary history"},
        {"city": "Edinburgh", "country": "Scotland", "reason": "Stunning castle, whisky culture, and dramatic Highland scenery"},
        {"city": "Amsterdam", "country": "Netherlands", "reason": "Beautiful canals, world-class museums, and easy cycling culture"},
    ],
    "new york": [
        {"city": "Chicago", "country": "USA", "reason": "Deep-dish pizza, stunning architecture, and a laid-back Midwestern feel"},
        {"city": "Toronto", "country": "Canada", "reason": "Diverse, multicultural, and safe — with a fantastic food scene"},
        {"city": "Montreal", "country": "Canada", "reason": "French flair, fantastic bagels, and a legendary festival calendar"},
    ],
    "dubai": [
        {"city": "Abu Dhabi", "country": "UAE", "reason": "More cultural depth with the Louvre and stunning Sheikh Zayed Mosque"},
        {"city": "Doha", "country": "Qatar", "reason": "Ultra-modern city with world-class museums and a revamped souq"},
        {"city": "Muscat", "country": "Oman", "reason": "Authentic Gulf culture, dramatic mountains, and pristine beaches"},
    ],
    "singapore": [
        {"city": "Kuala Lumpur", "country": "Malaysia", "reason": "Similar multicultural food scene at a fraction of the cost"},
        {"city": "Hong Kong", "country": "China", "reason": "Vertical cityscape, dim sum brunches, and incredible hiking trails"},
        {"city": "Bangkok", "country": "Thailand", "reason": "Vibrant street food, ornate temples, and legendary nightlife"},
    ],
    "bangkok": [
        {"city": "Chiang Mai", "country": "Thailand", "reason": "Thailand's cultural capital with a cooler climate and night bazaars"},
        {"city": "Ho Chi Minh City", "country": "Vietnam", "reason": "Dynamic city with French colonial history and incredible street food"},
        {"city": "Hanoi", "country": "Vietnam", "reason": "Atmospheric Old Quarter, egg coffee, and gateway to Ha Long Bay"},
    ],
    "rome": [
        {"city": "Florence", "country": "Italy", "reason": "Cradle of the Renaissance — the Uffizi and Brunelleschi's Dome"},
        {"city": "Naples", "country": "Italy", "reason": "The birthplace of pizza and gateway to Pompeii and the Amalfi Coast"},
        {"city": "Athens", "country": "Greece", "reason": "Ancient ruins, vibrant street art, and incredible food at lower prices"},
    ],
    "barcelona": [
        {"city": "Valencia", "country": "Spain", "reason": "Birthplace of paella, futuristic City of Arts, and lovely beaches"},
        {"city": "San Sebastián", "country": "Spain", "reason": "Pintxos capital with some of the world's best restaurants"},
        {"city": "Lisbon", "country": "Portugal", "reason": "Hilly charm, tram rides, and the world's best pastéis de nata"},
    ],
    "lisbon": [
        {"city": "Porto", "country": "Portugal", "reason": "Port wine, colourful azulejos, and a stunning riverside scene"},
        {"city": "Seville", "country": "Spain", "reason": "Passionate flamenco, stunning Alcázar palace, and tapas culture"},
        {"city": "Valencia", "country": "Spain", "reason": "Sunny, vibrant, with beautiful beaches and the birthplace of paella"},
    ],
    "amsterdam": [
        {"city": "Copenhagen", "country": "Denmark", "reason": "World-class food, cycling culture, and cosy 'hygge' lifestyle"},
        {"city": "Brussels", "country": "Belgium", "reason": "Chocolate, waffles, Art Nouveau, and the EU's beating heart"},
        {"city": "Ghent", "country": "Belgium", "reason": "Underrated medieval gem — fewer tourists than Bruges"},
    ],
    "istanbul": [
        {"city": "Athens", "country": "Greece", "reason": "Ancient ruins, lively market culture, and stunning island proximity"},
        {"city": "Tbilisi", "country": "Georgia", "reason": "Emerging gem with ancient bathhouses, great wine, and warm hospitality"},
        {"city": "Marrakech", "country": "Morocco", "reason": "Vibrant souks, stunning riads, and the Atlas Mountains on the doorstep"},
    ],
    "sydney": [
        {"city": "Melbourne", "country": "Australia", "reason": "Australia's cultural capital with renowned coffee and street art"},
        {"city": "Auckland", "country": "New Zealand", "reason": "Stunning harbour city with easy access to geothermal wonders"},
        {"city": "Cape Town", "country": "South Africa", "reason": "Table Mountain, world-class wine, and Africa's most cosmopolitan city"},
    ],
    "miami": [
        {"city": "Cancún", "country": "Mexico", "reason": "Caribbean beaches, Mayan ruins, and year-round sunshine"},
        {"city": "San Juan", "country": "Puerto Rico", "reason": "Historic old city walls, salsa culture, and beautiful beaches"},
        {"city": "Havana", "country": "Cuba", "reason": "Vintage cars, cigar factories, and one of the world's most unique cities"},
    ],
    "maldives": [
        {"city": "Palawan", "country": "Philippines", "reason": "Stunning lagoons and pristine beaches at a fraction of the cost"},
        {"city": "Zanzibar", "country": "Tanzania", "reason": "Turquoise waters, spice history, and coral reefs"},
        {"city": "Seychelles", "country": "Seychelles", "reason": "Granite boulders, powder-white beaches, and incredible biodiversity"},
    ],
    "santorini": [
        {"city": "Mykonos", "country": "Greece", "reason": "Iconic whitewashed villages with vibrant beach clubs and nightlife"},
        {"city": "Paros", "country": "Greece", "reason": "Quieter Greek island charm with beautiful villages and clear waters"},
        {"city": "Dubrovnik", "country": "Croatia", "reason": "Dramatic clifftop old city and crystal-clear Adriatic waters"},
    ],
    "kyoto": [
        {"city": "Nara", "country": "Japan", "reason": "Ancient temples, free-roaming deer, and only 45 minutes from Kyoto"},
        {"city": "Hiroshima", "country": "Japan", "reason": "Moving Peace Memorial, delicious okonomiyaki, and Miyajima island"},
        {"city": "Nikko", "country": "Japan", "reason": "Ornate Toshogu shrine and stunning mountain scenery near Tokyo"},
    ],
    "seoul": [
        {"city": "Busan", "country": "South Korea", "reason": "Korea's second city with colourful Gamcheon Village and seafood markets"},
        {"city": "Gyeongju", "country": "South Korea", "reason": "Ancient Silla kingdom capital — Korea's answer to Kyoto"},
        {"city": "Jeju Island", "country": "South Korea", "reason": "Volcanic island with stunning waterfalls and Hallasan crater hike"},
    ],
    "marrakech": [
        {"city": "Fes", "country": "Morocco", "reason": "The world's oldest university city and Morocco's cultural heart"},
        {"city": "Chefchaouen", "country": "Morocco", "reason": "The breathtaking Blue City in the Rif Mountains"},
        {"city": "Tunis", "country": "Tunisia", "reason": "North Africa's most laid-back medina with Carthage ruins nearby"},
    ],
    "cape town": [
        {"city": "Johannesburg", "country": "South Africa", "reason": "Vibrant arts scene, Soweto history, and the Cradle of Humankind"},
        {"city": "Nairobi", "country": "Kenya", "reason": "Safari gateway with world-class National Park on the city's edge"},
        {"city": "Mauritius", "country": "Mauritius", "reason": "Stunning beaches, diverse cultures, and one of Africa's safest islands"},
    ],
    "prague": [
        {"city": "Vienna", "country": "Austria", "reason": "Imperial palaces, Mozart, and the world's best coffee house culture"},
        {"city": "Krakow", "country": "Poland", "reason": "Beautiful market square, Wawel Castle, and moving Auschwitz visits"},
        {"city": "Budapest", "country": "Hungary", "reason": "Dramatic thermal baths, ruin bars, and stunning Danube panorama"},
    ],
    "phuket": [
        {"city": "Koh Lanta", "country": "Thailand", "reason": "Quieter beaches with a laid-back atmosphere and excellent diving"},
        {"city": "Langkawi", "country": "Malaysia", "reason": "Duty-free island paradise with cable car views and mangrove tours"},
        {"city": "Goa", "country": "India", "reason": "Portuguese-influenced beaches with unique spice market culture"},
    ],
}

# Generic fallbacks used when no specific match is found
FALLBACK_SUGGESTIONS = [
    {"city": "Lisbon", "country": "Portugal", "reason": "Europe's sunniest capital with world-class food and low costs"},
    {"city": "Porto", "country": "Portugal", "reason": "Porto wine, azulejos, and a charming riverside old town"},
    {"city": "Tbilisi", "country": "Georgia", "reason": "Ancient silk road city with great wine, food, and warm hospitality"},
    {"city": "Chiang Mai", "country": "Thailand", "reason": "Thai culture, temple trails, and the world's best cooking schools"},
    {"city": "Oaxaca", "country": "Mexico", "reason": "Indigenous culture, mezcal, and Mexico's best traditional cuisine"},
]


def _normalise(city: str) -> str:
    return city.lower().strip().replace("-", " ").replace(",", "")


@router.get("/similar")
async def get_similar(
    cities: str = Query(..., description="Comma-separated city names e.g. paris,tokyo"),
    limit: int = Query(4, ge=1, le=8),
):
    """Return smart alternative city suggestions based on the provided destinations."""
    city_list = [_normalise(c) for c in cities.split(",") if c.strip()]
    seen: set[str] = set(city_list)
    results: list[dict] = []

    for city in city_list:
        for suggestion in SIMILAR.get(city, []):
            key = _normalise(suggestion["city"])
            if key not in seen:
                seen.add(key)
                results.append(suggestion)
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    # Fill up with fallbacks if needed
    if len(results) < min(limit, 3):
        for fb in FALLBACK_SUGGESTIONS:
            key = _normalise(fb["city"])
            if key not in seen:
                seen.add(key)
                results.append(fb)
            if len(results) >= limit:
                break

    return {"input_cities": city_list, "suggestions": results[:limit]}
