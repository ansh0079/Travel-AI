import httpx
from typing import Optional, Dict
from datetime import datetime, timedelta
from app.config import get_settings
from app.models.destination import Visa
from app.utils.cache_service import cache_service, CacheService
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class VisaService:
    def __init__(self):
        self.settings = get_settings()
        self.cache = cache_service
        # Visa requirements database (simplified)
        # In production, this would be a comprehensive database or API
        self.visa_db = self._load_visa_database()
    
    def _load_visa_database(self) -> Dict:
        """Load visa requirements database"""
        return {
            # Format: (passport_country, destination_country): visa_info
            ("US", "FR"): {"required": False, "visa_free_days": 90, "type": "Schengen", "notes": "90 days within 180-day period"},
            ("US", "JP"): {"required": False, "visa_free_days": 90, "type": None, "notes": "Tourist stay up to 90 days"},
            ("US", "ID"): {"required": True, "evisa_available": True, "processing_days": 3, "cost_usd": 35, "type": "e-VOA", "notes": "Visa on arrival or e-VOA available"},
            ("US", "GB"): {"required": False, "visa_free_days": 180, "type": None, "notes": "Up to 6 months as tourist"},
            ("US", "AE"): {"required": False, "visa_free_days": 30, "type": None, "notes": "Visa on arrival, extendable"},
            ("US", "SG"): {"required": False, "visa_free_days": 90, "type": None, "notes": "Up to 90 days"},
            ("US", "AU"): {"required": True, "evisa_available": True, "processing_days": 1, "cost_usd": 20, "type": "ETA", "notes": "Electronic Travel Authority"},
            ("US", "IT"): {"required": False, "visa_free_days": 90, "type": "Schengen", "notes": "90 days within 180-day period"},
            ("US", "ES"): {"required": False, "visa_free_days": 90, "type": "Schengen", "notes": "90 days within 180-day period"},
            ("US", "ZA"): {"required": False, "visa_free_days": 90, "type": None, "notes": "Up to 90 days"},
            ("US", "MA"): {"required": False, "visa_free_days": 90, "type": None, "notes": "Up to 90 days"},
            ("US", "TH"): {"required": False, "visa_free_days": 30, "type": None, "notes": "Visa exemption for tourism"},
            ("US", "TR"): {"required": True, "evisa_available": True, "processing_days": 1, "cost_usd": 50, "type": "e-Visa", "notes": "Apply online before travel"},
            ("US", "IS"): {"required": False, "visa_free_days": 90, "type": "Schengen", "notes": "90 days within 180-day period"},
            ("US", "BR"): {"required": True, "evisa_available": True, "processing_days": 5, "cost_usd": 44, "type": "e-Visa", "notes": "Apply online before travel"},
            ("US", "EG"): {"required": True, "evisa_available": True, "processing_days": 3, "cost_usd": 25, "type": "e-Visa", "notes": "Single entry, valid for 3 months"},
            ("US", "CZ"): {"required": False, "visa_free_days": 90, "type": "Schengen", "notes": "90 days within 180-day period"},
            ("US", "NZ"): {"required": True, "evisa_available": True, "processing_days": 3, "cost_usd": 12, "type": "NZeTA", "notes": "NZ Electronic Travel Authority"},
            
            # EU passport holders
            ("FR", "US"): {"required": False, "visa_free_days": 90, "type": "ESTA", "notes": "ESTA required for visa waiver"},
            ("GB", "US"): {"required": False, "visa_free_days": 90, "type": "ESTA", "notes": "ESTA required for visa waiver"},
            ("DE", "US"): {"required": False, "visa_free_days": 90, "type": "ESTA", "notes": "ESTA required for visa waiver"},
            
            # Asian countries
            ("JP", "US"): {"required": False, "visa_free_days": 90, "type": "ESTA", "notes": "ESTA required"},
            ("JP", "FR"): {"required": False, "visa_free_days": 90, "type": "Schengen", "notes": "90 days within 180-day period"},
            ("CN", "US"): {"required": True, "evisa_available": False, "processing_days": 3, "cost_usd": 140, "type": "B1/B2", "notes": "Interview required at US Embassy"},
            ("IN", "US"): {"required": True, "evisa_available": False, "processing_days": 3, "cost_usd": 160, "type": "B1/B2", "notes": "Interview required"},
        }
    
    async def get_visa_requirements(
        self, 
        passport_country: str, 
        destination_country: str
    ) -> Visa:
        """Get visa requirements for travel between countries with caching"""
        cache_key = CacheService.visa_key(passport_country, destination_country)
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug("Visa cache hit", passport=passport_country, destination=destination_country)
            return Visa(**cached)
        
        logger.debug("Visa cache miss", passport=passport_country, destination=destination_country)
        
        key = (passport_country, destination_country)
        
        # Check database
        if key in self.visa_db:
            data = self.visa_db[key]
            visa = Visa(
                required=data.get("required", True),
                type=data.get("type"),
                visa_free_days=data.get("visa_free_days"),
                processing_days=data.get("processing_days"),
                cost_usd=data.get("cost_usd"),
                evisa_available=data.get("evisa_available", False),
                notes=data.get("notes", "")
            )
            # Cache for 24 hours (visa requirements don't change often)
            await self.cache.set(cache_key, visa.model_dump(), expire=timedelta(hours=24))
            return visa
        
        # Try external API if available
        if self.settings.visa_requirements_api_key:
            try:
                visa = await self._fetch_visa_api(passport_country, destination_country)
                if visa:
                    await self.cache.set(cache_key, visa.model_dump(), expire=timedelta(hours=24))
                return visa
            except Exception as e:
                logger.warning("Visa API error", error=str(e), passport_country=passport_country, destination_country=destination_country)
        
        # Default: assume visa required
        return Visa(
            required=True,
            notes="Please check with the embassy for current requirements"
        )
    
    async def _fetch_visa_api(
        self, 
        passport_country: str, 
        destination_country: str
    ) -> Visa:
        """Fetch visa info from external API"""
        # This would integrate with a real visa API
        # For now, return default
        return Visa(
            required=True,
            notes="API integration required"
        )
    
    def calculate_visa_score(
        self, 
        visa: Visa, 
        visa_preference: str = "visa_free"
    ) -> float:
        """
        Calculate visa convenience score (0-100)
        Higher score = more convenient
        """
        if not visa.required:
            # Visa-free is best
            return 100.0
        
        base_score = 30.0  # Starting point if visa required
        
        # eVisa is better than traditional visa
        if visa.evisa_available:
            base_score += 30
        
        # Faster processing is better
        if visa.processing_days:
            if visa.processing_days <= 1:
                base_score += 20
            elif visa.processing_days <= 3:
                base_score += 10
            elif visa.processing_days <= 7:
                base_score += 5
        
        # Lower cost is better (max $200)
        if visa.cost_usd:
            cost_score = max(0, (200 - visa.cost_usd) / 200 * 20)
            base_score += cost_score
        
        # Apply user preference
        preference_adjustments = {
            "visa_free": 0,  # No adjustment, already reflected in base
            "evisa_ok": 10 if visa.evisa_available else -10,
            "visa_ok": 0  # Accepts any visa
        }
        base_score += preference_adjustments.get(visa_preference, 0)
        
        return max(0, min(100, base_score))
    
    def get_visa_summary(self, visa: Visa) -> str:
        """Get human-readable visa summary"""
        if not visa.required:
            days = f" up to {visa.visa_free_days} days" if visa.visa_free_days else ""
            return f"✅ Visa-free{days}"
        
        if visa.evisa_available:
            cost = f" (${visa.cost_usd})" if visa.cost_usd else ""
            processing = f", {visa.processing_days} days processing" if visa.processing_days else ""
            return f"📄 eVisa available{cost}{processing}"
        
        cost = f" (${visa.cost_usd})" if visa.cost_usd else ""
        processing = f", {visa.processing_days} days processing" if visa.processing_days else ""
        return f"🛂 Visa required{cost}{processing}"
