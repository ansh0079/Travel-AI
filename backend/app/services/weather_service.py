import httpx
from typing import Optional, Dict
from datetime import datetime, timedelta
from app.config import get_settings
from app.models.destination import Weather
import asyncio

class WeatherService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    async def get_weather(
        self, 
        lat: float, 
        lon: float, 
        date: Optional[datetime] = None
    ) -> Optional[Weather]:
        """Get weather forecast for a location"""
        try:
            # Try OpenWeatherMap API
            if self.settings.openweather_api_key:
                return await self._fetch_openweather(lat, lon, date)
            
            # Fallback to mock data
            return self._get_mock_weather(lat, lon, date)
        except Exception as e:
            print(f"Weather API error: {e}")
            return self._get_mock_weather(lat, lon, date)
    
    async def _fetch_openweather(
        self, 
        lat: float, 
        lon: float, 
        date: Optional[datetime] = None
    ) -> Optional[Weather]:
        """Fetch weather from OpenWeatherMap API"""
        async with httpx.AsyncClient() as client:
            # Get 5-day forecast
            response = await client.get(
                f"{self.base_url}/forecast",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.settings.openweather_api_key,
                    "units": "metric"
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Get current weather
            current_response = await client.get(
                f"{self.base_url}/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.settings.openweather_api_key,
                    "units": "metric"
                },
                timeout=10.0
            )
            current_response.raise_for_status()
            current_data = current_response.json()
            
            # Parse forecast
            forecast_days = []
            for item in data.get("list", [])[:5]:
                forecast_days.append({
                    "date": item["dt_txt"],
                    "temp": item["main"]["temp"],
                    "condition": item["weather"][0]["main"],
                    "description": item["weather"][0]["description"]
                })
            
            current = current_data.get("main", {})
            weather_condition = current_data.get("weather", [{}])[0].get("main", "Unknown")
            
            return Weather(
                condition=weather_condition,
                temperature=current.get("temp", 20),
                humidity=current.get("humidity", 50),
                wind_speed=current_data.get("wind", {}).get("speed", 0),
                forecast_days=forecast_days,
                recommendation=self._get_weather_recommendation(weather_condition, current.get("temp", 20))
            )
    
    def _get_mock_weather(
        self, 
        lat: float, 
        lon: float, 
        date: Optional[datetime] = None
    ) -> Weather:
        """Generate mock weather based on location and season"""
        month = date.month if date else datetime.now().month
        
        # Determine season based on hemisphere and month
        is_northern = lat > 0
        
        if is_northern:
            if month in [12, 1, 2]:
                season = "winter"
                temp_range = (-5, 15)
            elif month in [3, 4, 5]:
                season = "spring"
                temp_range = (10, 25)
            elif month in [6, 7, 8]:
                season = "summer"
                temp_range = (20, 35)
            else:
                season = "autumn"
                temp_range = (10, 20)
        else:
            if month in [12, 1, 2]:
                season = "summer"
                temp_range = (20, 35)
            elif month in [3, 4, 5]:
                season = "autumn"
                temp_range = (10, 25)
            elif month in [6, 7, 8]:
                season = "winter"
                temp_range = (0, 15)
            else:
                season = "spring"
                temp_range = (15, 25)
        
        # Adjust for latitude (colder as you go further from equator)
        abs_lat = abs(lat)
        temp_adjustment = -abs_lat / 10
        
        import random
        base_temp = random.uniform(*temp_range) + temp_adjustment
        
        conditions = ["Clear", "Clouds", "Rain", "Snow"] if season == "winter" else ["Clear", "Clouds", "Rain"]
        condition = random.choice(conditions)
        
        return Weather(
            condition=condition,
            temperature=round(base_temp, 1),
            humidity=random.randint(40, 90),
            wind_speed=round(random.uniform(0, 20), 1),
            forecast_days=[],
            recommendation=self._get_weather_recommendation(condition, base_temp)
        )
    
    def _get_weather_recommendation(self, condition: str, temp: float) -> str:
        """Generate weather-based recommendation"""
        if condition == "Rain":
            return "Pack rain gear and consider indoor attractions"
        elif condition == "Snow":
            return "Great for winter sports, pack warm clothing"
        elif temp > 30:
            return "Hot weather - stay hydrated, plan indoor activities midday"
        elif temp < 5:
            return "Cold weather - pack warm layers"
        elif 20 <= temp <= 28 and condition == "Clear":
            return "Perfect weather for outdoor activities and sightseeing"
        else:
            return "Mild weather - comfortable for most activities"
    
    def calculate_weather_score(
        self, 
        weather: Weather, 
        preferred_weather: Optional[str] = None
    ) -> float:
        """Calculate a weather desirability score (0-100)"""
        score = 50.0
        
        # Base score on temperature
        temp = weather.temperature
        if 20 <= temp <= 28:
            score += 25  # Ideal temperature
        elif 15 <= temp < 20 or 28 < temp <= 32:
            score += 10  # Good temperature
        elif 5 <= temp < 15 or 32 < temp <= 35:
            score -= 10  # Less ideal
        else:
            score -= 25  # Extreme temperature
        
        # Condition adjustment
        condition_scores = {
            "Clear": 15,
            "Clouds": 5,
            "Rain": -15,
            "Snow": -5,
            "Thunderstorm": -25,
            "Drizzle": -10,
            "Mist": -5
        }
        score += condition_scores.get(weather.condition, 0)
        
        # Match user preference
        if preferred_weather:
            pref_map = {
                "hot": temp > 30,
                "warm": 25 <= temp <= 30,
                "mild": 15 <= temp < 25,
                "cold": 5 <= temp < 15,
                "snowy": weather.condition == "Snow"
            }
            if pref_map.get(preferred_weather, False):
                score += 10
        
        return max(0, min(100, score))