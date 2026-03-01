# 🚀 Instagram & Influencer Integration Guide

Complete step-by-step guide to integrate social features into your TravelAI app.

---

## Phase 1: Backend Setup

### Step 1.1: Update Database Models

Add the social models to `backend/app/database/models.py`:

```python
# Add these classes to backend/app/database/models.py

class Influencer(Base):
    """Travel influencers and content creators"""
    __tablename__ = "influencers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    profile_image_url = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # Social stats
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    
    # Categorization
    tier = Column(String, default="micro")  # nano, micro, mid, macro, mega
    categories = Column(Text, default="[]")  # JSON array
    top_destinations = Column(Text, default="[]")  # JSON array
    specialties = Column(Text, default="[]")  # JSON array
    
    # Engagement
    engagement_rate = Column(Float, nullable=True)
    avg_likes = Column(Integer, nullable=True)
    avg_comments = Column(Integer, nullable=True)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    
    # Platforms
    platforms = Column(Text, default="[\"instagram\"]")  # JSON array
    platform_links = Column(Text, default="{}")  # JSON object
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    content = relationship("SocialContent", back_populates="influencer")


class SocialContent(Base):
    """Social media content from influencers"""
    __tablename__ = "social_content"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    influencer_id = Column(String, ForeignKey("influencers.id"))
    
    # Platform info
    platform = Column(String, default="instagram")  # instagram, youtube, tiktok
    content_type = Column(String, default="photo")  # photo, video, reel, carousel
    external_id = Column(String, nullable=True)  # Instagram media ID
    
    # Content
    caption = Column(Text, nullable=True)
    hashtags = Column(Text, default="[]")  # JSON array
    mentions = Column(Text, default="[]")  # JSON array
    
    # Media
    media_urls = Column(Text, default="[]")  # JSON array
    thumbnail_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    
    # Location
    location_name = Column(String, nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    
    # Engagement stats
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    saves_count = Column(Integer, default=0)
    views_count = Column(Integer, nullable=True)
    
    # Timestamps
    posted_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # AI/ML enriched data
    ai_tags = Column(Text, default="[]")  # JSON array
    sentiment_score = Column(Float, nullable=True)
    is_sponsored = Column(Boolean, default=False)
    sponsor_brand = Column(String, nullable=True)
    
    # Relationships
    influencer = relationship("Influencer", back_populates="content")


class UserInfluencerFollow(Base):
    """Users following influencers"""
    __tablename__ = "user_influencer_follows"
    
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    influencer_id = Column(String, ForeignKey("influencers.id"), primary_key=True)
    followed_at = Column(DateTime, default=datetime.utcnow)


class SavedSocialContent(Base):
    """User's saved social content"""
    __tablename__ = "saved_social_content"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    content_id = Column(String, ForeignKey("social_content.id"))
    saved_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    collection_name = Column(String, nullable=True)


class Collection(Base):
    """Curated travel collections/guides"""
    __tablename__ = "collections"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String, nullable=True)
    
    # Categorization
    collection_type = Column(String, default="guide")  # guide, itinerary, bucket_list
    destinations = Column(Text, default="[]")  # JSON array
    tags = Column(Text, default="[]")  # JSON array
    
    # Creator
    creator_type = Column(String, default="influencer")  # influencer, staff, community
    creator_id = Column(String, ForeignKey("influencers.id"), nullable=True)
    
    # Stats
    view_count = Column(Integer, default=0)
    save_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    
    # Visibility
    is_featured = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserInstagramConnection(Base):
    """User's connected Instagram account"""
    __tablename__ = "user_instagram_connections"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    instagram_user_id = Column(String, nullable=False)
    instagram_username = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Imported data
    imported_posts_count = Column(Integer, default=0)
    last_import_at = Column(DateTime, nullable=True)
    
    # Timestamps
    connected_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

### Step 1.2: Create Social Services

Create `backend/app/services/social_service.py`:

```python
"""
Social Service - Core business logic for social features
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import json

from app.database.models import (
    Influencer, SocialContent, UserInfluencerFollow, 
    SavedSocialContent, Collection, UserInstagramConnection
)
from app.models.social import (
    InfluencerResponse, SocialContentResponse, TrendingDestination
)


class SocialService:
    """Main service for social features"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== INFLUENCER METHODS ==========
    
    def get_influencers(
        self,
        category: Optional[str] = None,
        tier: Optional[str] = None,
        featured_only: bool = False,
        sort_by: str = "followers",
        limit: int = 20,
        offset: int = 0
    ) -> List[Influencer]:
        """Get influencers with filters"""
        query = self.db.query(Influencer)
        
        if category:
            query = query.filter(Influencer.categories.contains(category))
        
        if tier:
            query = query.filter(Influencer.tier == tier)
        
        if featured_only:
            query = query.filter(Influencer.is_featured == True)
        
        # Sorting
        if sort_by == "followers":
            query = query.order_by(desc(Influencer.followers_count))
        elif sort_by == "engagement":
            query = query.order_by(desc(Influencer.engagement_rate))
        elif sort_by == "recent":
            query = query.order_by(desc(Influencer.created_at))
        
        return query.offset(offset).limit(limit).all()
    
    def get_influencer_by_id(self, influencer_id: str) -> Optional[Influencer]:
        """Get single influencer by ID"""
        return self.db.query(Influencer).filter(Influencer.id == influencer_id).first()
    
    def get_influencer_content(
        self,
        influencer_id: str,
        content_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[SocialContent]:
        """Get content for an influencer"""
        query = self.db.query(SocialContent).filter(
            SocialContent.influencer_id == influencer_id
        )
        
        if content_type:
            query = query.filter(SocialContent.content_type == content_type)
        
        return query.order_by(desc(SocialContent.posted_at)).offset(offset).limit(limit).all()
    
    def follow_influencer(self, user_id: str, influencer_id: str) -> bool:
        """Follow an influencer"""
        existing = self.db.query(UserInfluencerFollow).filter(
            UserInfluencerFollow.user_id == user_id,
            UserInfluencerFollow.influencer_id == influencer_id
        ).first()
        
        if existing:
            return False
        
        follow = UserInfluencerFollow(user_id=user_id, influencer_id=influencer_id)
        self.db.add(follow)
        self.db.commit()
        return True
    
    def unfollow_influencer(self, user_id: str, influencer_id: str) -> bool:
        """Unfollow an influencer"""
        follow = self.db.query(UserInfluencerFollow).filter(
            UserInfluencerFollow.user_id == user_id,
            UserInfluencerFollow.influencer_id == influencer_id
        ).first()
        
        if not follow:
            return False
        
        self.db.delete(follow)
        self.db.commit()
        return True
    
    # ========== CONTENT METHODS ==========
    
    def get_feed_content(
        self,
        user_id: Optional[str],
        feed_type: str = "foryou",
        limit: int = 20,
        offset: int = 0
    ) -> List[SocialContent]:
        """Get content for feed"""
        if feed_type == "following" and user_id:
            # Get content from followed influencers
            followed_ids = self.db.query(UserInfluencerFollow.influencer_id).filter(
                UserInfluencerFollow.user_id == user_id
            ).all()
            followed_ids = [f[0] for f in followed_ids]
            
            return self.db.query(SocialContent).filter(
                SocialContent.influencer_id.in_(followed_ids)
            ).order_by(desc(SocialContent.posted_at)).offset(offset).limit(limit).all()
        
        elif feed_type == "trending":
            # Get trending content (high engagement, recent)
            week_ago = datetime.utcnow() - timedelta(days=7)
            return self.db.query(SocialContent).filter(
                SocialContent.posted_at >= week_ago
            ).order_by(
                desc(SocialContent.likes_count + SocialContent.comments_count * 2)
            ).offset(offset).limit(limit).all()
        
        else:  # foryou - personalized
            # TODO: Implement personalized feed based on user preferences
            return self.db.query(SocialContent).order_by(
                desc(SocialContent.posted_at)
            ).offset(offset).limit(limit).all()
    
    def save_content(
        self,
        user_id: str,
        content_id: str,
        collection_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> SavedSocialContent:
        """Save content for later"""
        saved = SavedSocialContent(
            user_id=user_id,
            content_id=content_id,
            collection_name=collection_name,
            notes=notes
        )
        self.db.add(saved)
        self.db.commit()
        self.db.refresh(saved)
        return saved
    
    def unsave_content(self, user_id: str, content_id: str) -> bool:
        """Remove saved content"""
        saved = self.db.query(SavedSocialContent).filter(
            SavedSocialContent.user_id == user_id,
            SavedSocialContent.content_id == content_id
        ).first()
        
        if saved:
            self.db.delete(saved)
            self.db.commit()
            return True
        return False
    
    # ========== TRENDING METHODS ==========
    
    def get_trending_destinations(
        self,
        period: str = "week",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get trending destinations based on social activity
        This is a simplified version - enhance with ML later
        """
        if period == "today":
            since = datetime.utcnow() - timedelta(days=1)
        elif period == "week":
            since = datetime.utcnow() - timedelta(days=7)
        else:  # month
            since = datetime.utcnow() - timedelta(days=30)
        
        # Count posts per destination
        results = self.db.query(
            SocialContent.country,
            SocialContent.city,
            func.count(SocialContent.id).label("post_count"),
            func.sum(SocialContent.likes_count + SocialContent.comments_count).label("engagement")
        ).filter(
            SocialContent.posted_at >= since,
            SocialContent.city.isnot(None)
        ).group_by(
            SocialContent.country,
            SocialContent.city
        ).order_by(
            desc("engagement")
        ).limit(limit).all()
        
        trending = []
        for country, city, post_count, engagement in results:
            trending.append({
                "destination_name": city,
                "country": country,
                "posts_count": post_count,
                "total_engagement": engagement or 0,
                "trending_score": (engagement or 0) / max(post_count, 1),
                # TODO: Calculate actual growth percentage
                "growth_percentage": 0
            })
        
        return trending
    
    # ========== COLLECTIONS METHODS ==========
    
    def get_collections(
        self,
        collection_type: Optional[str] = None,
        featured_only: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> List[Collection]:
        """Get curated collections"""
        query = self.db.query(Collection).filter(Collection.is_public == True)
        
        if collection_type:
            query = query.filter(Collection.collection_type == collection_type)
        
        if featured_only:
            query = query.filter(Collection.is_featured == True)
        
        return query.order_by(desc(Collection.created_at)).offset(offset).limit(limit).all()


class InstagramService:
    """Service for Instagram API integration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.base_url = "https://graph.instagram.com"
    
    async def get_user_media(self, access_token: str, limit: int = 50) -> List[Dict]:
        """Fetch user's media from Instagram API"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me/media",
                params={
                    "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp",
                    "access_token": access_token,
                    "limit": limit
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
    
    async def import_user_posts(
        self,
        user_id: str,
        access_token: str,
        max_posts: int = 50
    ) -> Dict[str, Any]:
        """Import posts from Instagram and create social content"""
        # Get connection record
        connection = self.db.query(UserInstagramConnection).filter(
            UserInstagramConnection.user_id == user_id
        ).first()
        
        if not connection:
            raise ValueError("Instagram account not connected")
        
        # Fetch media from Instagram
        media_items = await self.get_user_media(access_token, max_posts)
        
        imported_count = 0
        for item in media_items:
            # TODO: Use AI to detect if post is travel-related
            # TODO: Extract location from caption or AI analysis
            # TODO: Create SocialContent records
            imported_count += 1
        
        # Update connection record
        connection.imported_posts_count += imported_count
        connection.last_import_at = datetime.utcnow()
        self.db.commit()
        
        return {
            "imported_count": imported_count,
            "total_posts": len(media_items)
        }
```

---

### Step 1.3: Wire Up API Routes

Update `backend/app/main.py` to include social routes:

```python
# Add this import at the top
from app.api.social_routes import router as social_router

# Add this line with other router includes
app.include_router(social_router)
```

Create `backend/app/api/social_routes.py` (simplified working version):

```python
"""
Social Media & Influencer API Routes - Simplified Implementation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User, Influencer, SocialContent
from app.services.social_service import SocialService
from app.utils.security import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/v1/social", tags=["social"])


@router.get("/feed")
async def get_social_feed(
    feed_type: str = Query("foryou", enum=["foryou", "following", "trending"]),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get social feed content"""
    service = SocialService(db)
    content = service.get_feed_content(
        user_id=current_user.id if current_user else None,
        feed_type=feed_type,
        limit=limit,
        offset=offset
    )
    
    return {
        "items": [
            {
                "id": c.id,
                "platform": c.platform,
                "content_type": c.content_type,
                "thumbnail_url": c.thumbnail_url,
                "caption": c.caption,
                "hashtags": json.loads(c.hashtags) if c.hashtags else [],
                "location_name": c.location_name,
                "city": c.city,
                "country": c.country,
                "likes_count": c.likes_count,
                "posted_at": c.posted_at.isoformat(),
                "influencer": {
                    "id": c.influencer.id,
                    "username": c.influencer.username,
                    "display_name": c.influencer.display_name,
                    "profile_image_url": c.influencer.profile_image_url,
                    "followers_count": c.influencer.followers_count,
                    "is_verified": c.influencer.is_verified,
                }
            }
            for c in content
        ],
        "has_more": len(content) == limit,
        "offset": offset + len(content)
    }


@router.get("/influencers")
async def list_influencers(
    category: Optional[str] = Query(None),
    tier: Optional[str] = Query(None, enum=["nano", "micro", "mid", "macro", "mega"]),
    featured_only: bool = Query(False),
    sort_by: str = Query("followers", enum=["followers", "engagement", "recent"]),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List travel influencers"""
    service = SocialService(db)
    influencers = service.get_influencers(
        category=category,
        tier=tier,
        featured_only=featured_only,
        sort_by=sort_by,
        limit=limit,
        offset=offset
    )
    
    return [
        {
            "id": inf.id,
            "username": inf.username,
            "display_name": inf.display_name,
            "profile_image_url": inf.profile_image_url,
            "followers_count": inf.followers_count,
            "tier": inf.tier,
            "categories": json.loads(inf.categories) if inf.categories else [],
            "is_verified": inf.is_verified,
            "is_featured": inf.is_featured,
        }
        for inf in influencers
    ]


@router.get("/influencers/{influencer_id}")
async def get_influencer_profile(
    influencer_id: str,
    db: Session = Depends(get_db)
):
    """Get influencer profile details"""
    service = SocialService(db)
    influencer = service.get_influencer_by_id(influencer_id)
    
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer not found")
    
    # Get recent content
    recent_content = service.get_influencer_content(influencer_id, limit=6)
    
    return {
        "id": influencer.id,
        "username": influencer.username,
        "display_name": influencer.display_name,
        "bio": influencer.bio,
        "profile_image_url": influencer.profile_image_url,
        "website": influencer.website,
        "followers_count": influencer.followers_count,
        "following_count": influencer.following_count,
        "posts_count": influencer.posts_count,
        "tier": influencer.tier,
        "categories": json.loads(influencer.categories) if influencer.categories else [],
        "top_destinations": json.loads(influencer.top_destinations) if influencer.top_destinations else [],
        "specialties": json.loads(influencer.specialties) if influencer.specialties else [],
        "engagement_rate": influencer.engagement_rate,
        "avg_likes": influencer.avg_likes,
        "is_verified": influencer.is_verified,
        "is_featured": influencer.is_featured,
        "platforms": json.loads(influencer.platforms) if influencer.platforms else ["instagram"],
        "recent_content": [
            {
                "id": c.id,
                "content_type": c.content_type,
                "thumbnail_url": c.thumbnail_url,
                "location_name": c.location_name,
                "likes_count": c.likes_count,
            }
            for c in recent_content
        ]
    }


@router.post("/influencers/{influencer_id}/follow")
async def follow_influencer(
    influencer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Follow an influencer"""
    service = SocialService(db)
    success = service.follow_influencer(current_user.id, influencer_id)
    
    if not success:
        return {"success": False, "message": "Already following"}
    
    return {"success": True, "message": "Now following influencer"}


@router.get("/trending/destinations")
async def get_trending_destinations(
    period: str = Query("week", enum=["today", "week", "month"]),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get trending destinations"""
    service = SocialService(db)
    trending = service.get_trending_destinations(period=period, limit=limit)
    return trending


# Import json at the top
import json
```

---

## Phase 2: Frontend Integration

### Step 2.1: Add Social API Service

Create `frontend/src/services/socialApi.ts`:

```typescript
import { apiClient } from "./api";

// Types
export interface Influencer {
  id: string;
  username: string;
  display_name: string;
  profile_image_url?: string;
  followers_count: number;
  tier: "nano" | "micro" | "mid" | "macro" | "mega";
  categories: string[];
  is_verified: boolean;
  is_featured: boolean;
}

export interface SocialContent {
  id: string;
  platform: string;
  content_type: "photo" | "video" | "reel" | "carousel";
  thumbnail_url: string;
  caption?: string;
  hashtags: string[];
  location_name?: string;
  city?: string;
  country?: string;
  likes_count: number;
  posted_at: string;
  influencer: {
    id: string;
    username: string;
    display_name: string;
    profile_image_url?: string;
    followers_count: number;
    is_verified: boolean;
  };
}

// API Functions
export const getSocialFeed = async (
  feedType: "foryou" | "following" | "trending" = "foryou",
  limit: number = 20,
  offset: number = 0
) => {
  const response = await apiClient.get(
    `/social/feed?feed_type=${feedType}&limit=${limit}&offset=${offset}`
  );
  return response.data;
};

export const getInfluencers = async (params?: {
  category?: string;
  tier?: string;
  featured_only?: boolean;
  sort_by?: string;
  limit?: number;
  offset?: number;
}) => {
  const response = await apiClient.get("/social/influencers", { params });
  return response.data;
};

export const getInfluencerProfile = async (influencerId: string) => {
  const response = await apiClient.get(`/social/influencers/${influencerId}`);
  return response.data;
};

export const followInfluencer = async (influencerId: string) => {
  const response = await apiClient.post(`/social/influencers/${influencerId}/follow`);
  return response.data;
};

export const getTrendingDestinations = async (
  period: "today" | "week" | "month" = "week",
  limit: number = 10
) => {
  const response = await apiClient.get(
    `/social/trending/destinations?period=${period}&limit=${limit}`
  );
  return response.data;
};

// React Query Keys
export const socialQueryKeys = {
  feed: (type: string) => ["social", "feed", type],
  influencers: (params?: any) => ["social", "influencers", params],
  influencer: (id: string) => ["social", "influencer", id],
  trending: (period: string) => ["social", "trending", period],
};
```

---

### Step 2.2: Create React Hooks

Create `frontend/src/hooks/useSocial.ts`:

```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSocialFeed,
  getInfluencers,
  getInfluencerProfile,
  followInfluencer,
  getTrendingDestinations,
  socialQueryKeys,
} from "@/services/socialApi";

// Hook for social feed
export const useSocialFeed = (
  feedType: "foryou" | "following" | "trending" = "foryou",
  limit: number = 20
) => {
  return useQuery({
    queryKey: socialQueryKeys.feed(feedType),
    queryFn: () => getSocialFeed(feedType, limit),
  });
};

// Hook for influencers list
export const useInfluencers = (params?: Parameters<typeof getInfluencers>[0]) => {
  return useQuery({
    queryKey: socialQueryKeys.influencers(params),
    queryFn: () => getInfluencers(params),
  });
};

// Hook for single influencer
export const useInfluencer = (influencerId: string) => {
  return useQuery({
    queryKey: socialQueryKeys.influencer(influencerId),
    queryFn: () => getInfluencerProfile(influencerId),
    enabled: !!influencerId,
  });
};

// Hook for follow/unfollow
export const useFollowInfluencer = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: followInfluencer,
    onSuccess: (_, influencerId) => {
      // Invalidate influencer queries
      queryClient.invalidateQueries({
        queryKey: socialQueryKeys.influencer(influencerId),
      });
      queryClient.invalidateQueries({
        queryKey: ["social", "influencers"],
      });
    },
  });
};

// Hook for trending destinations
export const useTrendingDestinations = (
  period: "today" | "week" | "month" = "week"
) => {
  return useQuery({
    queryKey: socialQueryKeys.trending(period),
    queryFn: () => getTrendingDestinations(period),
  });
};
```

---

### Step 2.3: Add Routes to Navigation

Update `frontend/src/app/page.tsx` or create new pages:

```typescript
// In your main navigation or add these links:

const navItems = [
  { href: "/", label: "Home" },
  { href: "/discover", label: "Discover" },  // Social Feed
  { href: "/influencers", label: "Influencers" },
  { href: "/trending", label: "Trending" },
  { href: "/inspiration", label: "Inspiration" },
];
```

Create new pages:

```typescript
// frontend/src/app/discover/page.tsx
import SocialFeed from "@/components/SocialFeed";

export default function DiscoverPage() {
  return <SocialFeed />;
}

// frontend/src/app/influencers/page.tsx
import InfluencerHub from "@/components/InfluencerHub";

export default function InfluencersPage() {
  return <InfluencerHub />;
}

// frontend/src/app/trending/page.tsx
import TrendingDestinations from "@/components/TrendingDestinations";

export default function TrendingPage() {
  return <TrendingDestinations />;
}

// frontend/src/app/inspiration/page.tsx
import TripInspiration from "@/components/TripInspiration";

export default function InspirationPage() {
  return <TripInspiration />;
}
```

---

## Phase 3: Third-Party Setup (Instagram API)

### Step 3.1: Create Meta Developer Account

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create a developer account
3. Create a new app (type: "Consumer" or "Business")
4. Add "Instagram Basic Display" product
5. Configure OAuth settings

### Step 3.2: Configure Instagram App

In your Meta Developer Dashboard:

1. **Basic Display Settings**:
   - Add `https://yourdomain.com/auth/instagram/callback` to Valid OAuth Redirect URIs
   - Add your website to Deauthorize Callback URL
   - Add your privacy policy URL

2. **App Review**:
   - Request `instagram_basic` permission
   - Request `instagram_content_publish` (for posting)
   - Submit for review with screencast

### Step 3.3: Add Environment Variables

Add to `backend/.env`:

```bash
# Instagram API
INSTAGRAM_APP_ID=your_app_id
INSTAGRAM_APP_SECRET=your_app_secret
INSTAGRAM_REDIRECT_URI=http://localhost:3000/auth/instagram/callback
```

---

## Phase 4: Data Seeding (For Testing)

### Step 4.1: Create Seed Script

Create `backend/scripts/seed_social_data.py`:

```python
"""
Seed script for social data
Run with: python -m scripts.seed_social_data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, engine
from app.database.models import Base, Influencer, SocialContent
from datetime import datetime, timedelta
import json

# Create tables
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    
    try:
        # Clear existing data
        db.query(SocialContent).delete()
        db.query(Influencer).delete()
        
        # Create influencers
        influencers = [
            Influencer(
                id="inf-001",
                username="wanderlust_sarah",
                display_name="Sarah Mitchell",
                bio="Travel photographer capturing the world's hidden gems | 50+ countries",
                profile_image_url="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400",
                website="https://example.com",
                followers_count=245000,
                following_count=890,
                posts_count=1243,
                tier="micro",
                categories=json.dumps(["luxury", "food", "culture", "photography"]),
                top_destinations=json.dumps(["France", "Italy", "Japan", "Greece"]),
                specialties=json.dumps(["hidden gems", "luxury hotels", "local cuisine"]),
                engagement_rate=4.2,
                avg_likes=12500,
                is_verified=True,
                is_featured=True,
                platforms=json.dumps(["instagram", "youtube"]),
            ),
            Influencer(
                id="inf-002",
                username="adventure_mike",
                display_name="Mike Chen",
                bio="Adventure seeker | Mountain climber | Drone pilot",
                profile_image_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400",
                followers_count=890000,
                following_count=450,
                posts_count=892,
                tier="macro",
                categories=json.dumps(["adventure", "photography", "mountains"]),
                top_destinations=json.dumps(["Nepal", "New Zealand", "Iceland"]),
                specialties=json.dumps(["hiking trails", "drone photography"]),
                engagement_rate=3.8,
                avg_likes=32000,
                is_verified=True,
                is_featured=True,
            ),
            Influencer(
                id="inf-003",
                username="budget_backpacker",
                display_name="Alex & Emma",
                bio="Couple traveling the world on $50/day",
                profile_image_url="https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=400",
                followers_count=156000,
                posts_count=2100,
                tier="micro",
                categories=json.dumps(["budget", "backpacker", "food"]),
                top_destinations=json.dumps(["Thailand", "Vietnam", "Mexico"]),
                specialties=json.dumps(["budget tips", "hostel reviews"]),
                engagement_rate=5.1,
                avg_likes=8900,
            ),
        ]
        
        for inf in influencers:
            db.add(inf)
        
        db.commit()
        
        # Create social content
        contents = [
            SocialContent(
                id="content-001",
                influencer_id="inf-001",
                platform="instagram",
                content_type="photo",
                external_id="mock_001",
                caption="Paris in the spring is absolutely magical! ✨",
                hashtags=json.dumps(["paris", "france", "travel", "spring"]),
                media_urls=json.dumps(["https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800"]),
                thumbnail_url="https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800",
                location_name="Seine River, Paris",
                city="Paris",
                country="France",
                likes_count=45231,
                comments_count=892,
                saves_count=3400,
                posted_at=datetime.utcnow() - timedelta(days=2),
            ),
            SocialContent(
                id="content-002",
                influencer_id="inf-002",
                platform="instagram",
                content_type="reel",
                caption="POV: You finally made it to Bali's most Instagrammable waterfall 💦",
                hashtags=json.dumps(["bali", "indonesia", "waterfall", "travelreels"]),
                thumbnail_url="https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800",
                location_name="Tegenungan Waterfall",
                city="Ubud",
                country="Indonesia",
                likes_count=128500,
                comments_count=2341,
                views_count=2500000,
                posted_at=datetime.utcnow() - timedelta(days=3),
            ),
            SocialContent(
                id="content-003",
                influencer_id="inf-001",
                platform="instagram",
                content_type="carousel",
                caption="Cinque Terre is even more beautiful in person 😍",
                hashtags=json.dumps(["cinqueterre", "italy", "mediterranean"]),
                thumbnail_url="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800",
                location_name="Cinque Terre",
                city="La Spezia",
                country="Italy",
                likes_count=67342,
                comments_count=1567,
                posted_at=datetime.utcnow() - timedelta(days=5),
            ),
            SocialContent(
                id="content-004",
                influencer_id="inf-003",
                platform="instagram",
                content_type="photo",
                caption="$10 hostel with this view? Yes please! 🏔️",
                hashtags=json.dumps(["budgettravel", "hostellife", "vietnam"]),
                thumbnail_url="https://images.unsplash.com/photo-1528127269322-539801943592?w=800",
                location_name="Ha Giang",
                city="Ha Giang",
                country="Vietnam",
                likes_count=34500,
                comments_count=567,
                posted_at=datetime.utcnow() - timedelta(days=1),
            ),
        ]
        
        for content in contents:
            db.add(content)
        
        db.commit()
        
        print("✅ Social data seeded successfully!")
        print(f"   Created {len(influencers)} influencers")
        print(f"   Created {len(contents)} content items")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
```

Run the seed script:
```bash
cd backend
python -m scripts.seed_social_data
```

---

## Phase 5: Testing

### Step 5.1: Test API Endpoints

```bash
# Test feed
curl http://localhost:8000/api/v1/social/feed?feed_type=foryou

# Test influencers
curl http://localhost:8000/api/v1/social/influencers

# Test trending
curl http://localhost:8000/api/v1/social/trending/destinations
```

### Step 5.2: Frontend Testing

1. Navigate to `/discover` - should see social feed
2. Navigate to `/influencers` - should see influencer list
3. Click on influencer - should open profile modal
4. Test follow/unfollow buttons

---

## Phase 6: Deployment Checklist

- [ ] Database migrations run on production
- [ ] Environment variables configured
- [ ] Instagram app in Live mode (not Development)
- [ ] Rate limiting configured
- [ ] CDN for images
- [ ] Analytics tracking

---

## Quick Start Commands

```bash
# 1. Backend setup
cd backend
pip install -r requirements.txt

# 2. Update models and create migration
alembic revision --autogenerate -m "add social tables"
alembic upgrade head

# 3. Seed test data
python -m scripts.seed_social_data

# 4. Start backend
uvicorn app.main:app --reload

# 5. Frontend (new terminal)
cd frontend
npm install  # if new dependencies needed
npm run dev

# 6. Test
# Open http://localhost:3000/discover
```

---

## Troubleshooting

### Issue: Tables not created
**Fix**: Ensure `Base.metadata.create_all(bind=engine)` runs on startup

### Issue: 404 on social endpoints
**Fix**: Verify router is included in `main.py`

### Issue: CORS errors
**Fix**: Add frontend origin to `ALLOWED_ORIGINS` env variable

### Issue: Images not loading
**Fix**: Use placeholder images or configure image CDN

---

**Need help?** Check the browser console for frontend errors and the backend logs for API errors.
