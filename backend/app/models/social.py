"""
Social Media & Influencer Models
For Instagram integration and travel influencer content
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    REEL = "reel"
    CAROUSEL = "carousel"
    STORY = "story"
    GUIDE = "guide"
    LIVE = "live"


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    BLOG = "blog"


class InfluencerTier(str, Enum):
    NANO = "nano"         # 1K-10K followers
    MICRO = "micro"       # 10K-100K followers
    MID = "mid"           # 100K-500K followers
    MACRO = "macro"       # 500K-1M followers
    MEGA = "mega"         # 1M+ followers


class InfluencerCategory(str, Enum):
    LUXURY = "luxury"
    BUDGET = "budget"
    ADVENTURE = "adventure"
    FOOD = "food"
    SOLO_FEMALE = "solo_female"
    FAMILY = "family"
    DIGITAL_NOMAD = "digital_nomad"
    BACKPACKER = "backpacker"
    SUSTAINABLE = "sustainable"
    PHOTOGRAPHY = "photography"
    WELLNESS = "wellness"
    CULTURE = "culture"


# ============== Influencer Models ==============

class InfluencerBase(BaseModel):
    """Base influencer data"""
    username: str
    display_name: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    location: Optional[str] = None  # Home base
    website: Optional[str] = None
    
    # Social stats
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    
    # Categorization
    tier: InfluencerTier = InfluencerTier.MICRO
    categories: List[InfluencerCategory] = []
    
    # Travel focus
    top_destinations: List[str] = []  # Countries/cities they frequently visit
    specialties: List[str] = []  # e.g., "hidden gems", "food tours", "luxury hotels"
    
    # Engagement
    engagement_rate: Optional[float] = None  # Average engagement rate
    avg_likes: Optional[int] = None
    avg_comments: Optional[int] = None
    
    # Verification
    is_verified: bool = False
    is_featured: bool = False
    
    # Platforms
    platforms: List[Platform] = [Platform.INSTAGRAM]
    platform_links: Dict[Platform, str] = {}  # username/handle per platform


class InfluencerCreate(InfluencerBase):
    pass


class InfluencerResponse(InfluencerBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    total_content_count: int = 0
    recent_posts: List["SocialContentSummary"] = []
    
    class Config:
        from_attributes = True


class InfluencerSummary(BaseModel):
    """Lightweight influencer info for listings"""
    id: str
    username: str
    display_name: str
    profile_image_url: Optional[str] = None
    tier: InfluencerTier
    followers_count: int
    categories: List[InfluencerCategory]
    is_featured: bool


# ============== Social Content Models ==============

class SocialContentBase(BaseModel):
    """Base model for social media content"""
    # Source info
    platform: Platform
    content_type: ContentType
    external_id: str  # Instagram media ID, YouTube video ID, etc.
    
    # Content
    caption: Optional[str] = None
    hashtags: List[str] = []
    mentions: List[str] = []
    
    # Media URLs
    media_urls: List[str] = []  # Multiple for carousels
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    
    # Location
    location_name: Optional[str] = None  # e.g., "Eiffel Tower, Paris"
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    
    # Engagement stats
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    saves_count: int = 0
    views_count: Optional[int] = None  # For videos/reels
    
    # Timestamps
    posted_at: datetime
    
    # AI/ML enriched data
    ai_tags: List[str] = []  # Auto-detected content tags
    sentiment_score: Optional[float] = None  -1 to 1
    is_sponsored: bool = False
    sponsor_brand: Optional[str] = None


class SocialContentCreate(SocialContentBase):
    influencer_id: str


class SocialContentResponse(SocialContentBase):
    id: str
    influencer_id: str
    created_at: datetime
    
    # Related data
    influencer: InfluencerSummary
    related_destinations: List["DestinationMention"] = []
    
    # User interaction (if authenticated)
    user_saved: bool = False
    user_liked: bool = False
    
    class Config:
        from_attributes = True


class SocialContentSummary(BaseModel):
    """Lightweight content for feeds"""
    id: str
    content_type: ContentType
    thumbnail_url: str
    location_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    likes_count: int
    posted_at: datetime


class DestinationMention(BaseModel):
    """When content mentions a destination"""
    destination_id: str
    destination_name: str
    country: str
    mention_type: str  # "primary", "tagged", "background", "mentioned"
    confidence_score: float  # AI confidence this content features this destination


# ============== Curated Collections & Guides ==============

class CollectionBase(BaseModel):
    """Curated collections by influencers or staff"""
    title: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    
    # Categorization
    collection_type: str  # "guide", "itinerary", "bucket_list", "hidden_gems", "seasonal"
    destinations: List[str] = []  # Destination IDs
    tags: List[str] = []
    
    # Creator
    creator_type: str  # "influencer", "staff", "community", "brand"
    creator_id: Optional[str] = None  # Influencer ID if applicable
    
    # Content
    items: List["CollectionItem"] = []
    
    # Stats
    view_count: int = 0
    save_count: int = 0
    share_count: int = 0
    
    is_featured: bool = False
    is_public: bool = True


class CollectionItem(BaseModel):
    """Item within a collection"""
    order: int
    item_type: str  # "destination", "attraction", "restaurant", "hotel", "tip", "content"
    reference_id: Optional[str] = None  # ID of referenced entity
    
    # Content
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    
    # Location
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Linked social content
    related_content_ids: List[str] = []  # SocialContent IDs


class CollectionResponse(CollectionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    creator: Optional[InfluencerSummary] = None
    
    class Config:
        from_attributes = True


# ============== Trending & Discovery ==============

class TrendingDestination(BaseModel):
    """Trending destination based on social data"""
    destination_id: str
    destination_name: str
    country: str
    image_url: Optional[str] = None
    
    # Trend metrics
    trending_score: float
    growth_percentage: float  # Week over week growth
    
    # Social proof
    posts_count_7d: int
    total_engagement_7d: int
    top_influencers: List[InfluencerSummary]
    
    # Sample content
    featured_content: List[SocialContentSummary]
    
    # Why it's trending
    trending_reason: str  # "viral_reel", "influencer_feature", "event", "seasonal"
    related_hashtags: List[str]


class TrendingHashtag(BaseModel):
    """Trending travel hashtags"""
    hashtag: str
    post_count: int
    engagement_rate: float
    trending_score: float
    related_destinations: List[str]
    sample_posts: List[SocialContentSummary]


class InfluencerRecommendation(BaseModel):
    """Personalized influencer recommendations for a user"""
    influencer: InfluencerSummary
    match_score: float
    match_reasons: List[str]  # "similar_budget", "shared_interests", "destination_match"
    featured_content: List[SocialContentSummary]


# ============== User Social Interactions ==============

class UserSocialPreferences(BaseModel):
    """User's social content preferences"""
    followed_influencers: List[str]  # Influencer IDs
    followed_hashtags: List[str]
    followed_destinations: List[str]  # For destination-specific feeds
    
    # Content preferences
    preferred_content_types: List[ContentType]
    preferred_categories: List[InfluencerCategory]
    hide_sponsored: bool = False
    
    # Discovery
    discover_new_influencers: bool = True
    show_friend_activity: bool = True


class SavedContent(BaseModel):
    """User's saved social content (inspiration board)"""
    id: str
    user_id: str
    content_id: str
    saved_at: datetime
    notes: Optional[str] = None
    collection_name: Optional[str] = None  # For organizing saved content
    
    # Denormalized for quick access
    content_preview: SocialContentSummary


class UserGeneratedContent(BaseModel):
    """User's own travel content they share"""
    id: str
    user_id: str
    trip_id: Optional[str] = None
    
    # Content
    caption: str
    media_urls: List[str]
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Visibility
    is_public: bool = False
    share_to_instagram: bool = False
    
    # Engagement
    likes_count: int = 0
    comments_count: int = 0
    
    created_at: datetime


# ============== API Request/Response Models ==============

class SocialFeedRequest(BaseModel):
    """Request parameters for social feed"""
    feed_type: str = "foryou"  # "foryou", "following", "trending", "destination", "influencer"
    destination_id: Optional[str] = None  # For destination-specific feed
    influencer_id: Optional[str] = None  # For influencer profile feed
    content_types: List[ContentType] = []
    
    # Pagination
    cursor: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=50)


class SocialFeedResponse(BaseModel):
    """Social feed response"""
    items: List[SocialContentResponse]
    next_cursor: Optional[str] = None
    has_more: bool
    
    # Feed metadata
    trending_hashtags: List[TrendingHashtag] = []
    suggested_influencers: List[InfluencerRecommendation] = []


class DiscoverRequest(BaseModel):
    """Request for discovery/explore page"""
    category: Optional[InfluencerCategory] = None
    destination: Optional[str] = None
    hashtag: Optional[str] = None
    content_type: Optional[ContentType] = None
    
    # Filters
    min_engagement: Optional[float] = None
    date_range: Optional[str] = None  # "today", "week", "month", "year"
    
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class InstagramConnectRequest(BaseModel):
    """Connect Instagram account"""
    access_token: str
    instagram_user_id: Optional[str] = None


class ShareToInstagramRequest(BaseModel):
    """Share content to Instagram"""
    content_type: str  # "story", "post", "reel"
    media_url: str
    caption: Optional[str] = None
    hashtags: List[str] = []
    location_name: Optional[str] = None
