# 📱 Instagram & Influencer Integration

## Overview

This feature integrates Instagram and travel influencer content into the TravelAI platform, providing users with social proof, inspiration, and authentic travel recommendations from trusted creators.

---

## ✨ Key Features

### 1. Social Feed
- **For You Feed**: Personalized content based on user preferences
- **Following Feed**: Content from followed influencers
- **Trending Feed**: Popular content across the platform
- **Interactive Cards**: Like, save, share, and explore content

### 2. Influencer Hub
- **Influencer Profiles**: Detailed stats, specialties, and content
- **Categories**: Filter by travel style (luxury, budget, adventure, etc.)
- **Tier System**: Nano to Mega influencer classification
- **Follow System**: Follow favorite creators

### 3. Trending Destinations
- **Real-time Trends**: AI-powered trending algorithm
- **Growth Metrics**: Week-over-week growth percentages
- **Social Proof**: Post counts, engagement stats
- **Featured Content**: Best posts from each destination

### 4. Trip Inspiration
- **Curated Collections**: Guides, itineraries, bucket lists
- **Save for Later**: Build personal inspiration boards
- **Add to Trip**: Directly add inspired items to itineraries
- **Smart Recommendations**: AI-suggested content

### 5. Instagram Integration
- **Account Connection**: Link Instagram profiles
- **Content Import**: Import travel posts automatically
- **Share to Instagram**: Share trips to stories/posts
- **Cross-platform Sync**: Unified experience

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                         │
├─────────────────────────────────────────────────────────────────┤
│  SocialFeed      InfluencerHub    TrendingNow    TripInspiration │
│  ├─ PhotoGrid    ├─ Profiles      ├─ Hashtags    ├─ Curated     │
│  ├─ Stories      ├─ Guides        ├─ Locations   ├─ Collections │
│  └─ Reels        └─ LiveStreams   └─ Challenges  └─ Wishlists   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │ Instagram   │  │ Influencer  │  │ Social      │  │ Trend  │ │
│  │ API Service │  │ Service     │  │ Feed Service│  │ Engine │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌────────────────┐    ┌────────────────┐
│ Instagram/   │    │ Influencer     │    │ External APIs  │
│ Meta Graph   │    │ CMS/Database   │    │ (YouTube,      │
│ API          │    │                │    │  TikTok, etc)  │
└──────────────┘    └────────────────┘    └────────────────┘
```

---

## 📁 Files Created

### Backend
```
backend/
├── app/
│   ├── models/
│   │   └── social.py              # Pydantic models for social features
│   ├── api/
│   │   └── social_routes.py       # API endpoints
│   └── services/
│       ├── instagram_service.py   # Instagram API integration
│       ├── influencer_service.py  # Influencer management
│       ├── social_feed_service.py # Feed generation
│       └── trending_service.py    # Trending algorithm
```

### Frontend
```
frontend/src/
├── components/
│   ├── SocialFeed.tsx             # Main social feed component
│   ├── InfluencerHub.tsx          # Influencer discovery
│   ├── TrendingDestinations.tsx   # Trending destinations
│   └── TripInspiration.tsx        # Inspiration board
├── services/
│   └── socialApi.ts               # API client for social features
└── hooks/
    ├── useSocialFeed.ts           # React Query hook for feed
    ├── useInfluencer.ts           # Hook for influencer data
    └── useTrending.ts             # Hook for trending data
```

---

## 🔌 API Endpoints

### Feed
```
POST   /api/v1/social/feed              # Get personalized feed
GET    /api/v1/social/feed/trending     # Trending content
GET    /api/v1/social/feed/explore      # Location-based exploration
```

### Influencers
```
GET    /api/v1/social/influencers              # List influencers
GET    /api/v1/social/influencers/{id}         # Get profile
GET    /api/v1/social/influencers/{id}/content # Get content
GET    /api/v1/social/influencers/{id}/guides  # Get guides
GET    /api/v1/social/influencers/recommended  # Personalized recommendations
POST   /api/v1/social/influencers/{id}/follow  # Follow influencer
POST   /api/v1/social/influencers/{id}/unfollow # Unfollow influencer
```

### Content
```
GET    /api/v1/social/content/{id}           # Get content details
POST   /api/v1/social/content/{id}/save      # Save content
POST   /api/v1/social/content/{id}/unsave    # Unsave content
GET    /api/v1/social/content/{id}/related   # Related content
```

### Trending
```
GET    /api/v1/social/trending/destinations  # Trending destinations
GET    /api/v1/social/trending/hashtags      # Trending hashtags
GET    /api/v1/social/trending/experiences   # Trending experiences
```

### Collections
```
GET    /api/v1/social/collections            # List collections
GET    /api/v1/social/collections/{id}       # Get collection
POST   /api/v1/social/collections/{id}/save  # Save collection
```

### Instagram Integration
```
POST   /api/v1/social/instagram/connect      # Connect account
POST   /api/v1/social/instagram/disconnect   # Disconnect account
GET    /api/v1/social/instagram/import       # Import posts
POST   /api/v1/social/share/instagram        # Share to Instagram
```

---

## 🗄️ Database Schema

### Tables

#### influencers
- `id` (PK)
- `username`, `display_name`, `bio`
- `profile_image_url`, `website`
- `followers_count`, `following_count`, `posts_count`
- `tier` (nano/micro/mid/macro/mega)
- `categories` (JSON array)
- `top_destinations` (JSON array)
- `specialties` (JSON array)
- `engagement_rate`, `avg_likes`, `avg_comments`
- `is_verified`, `is_featured`
- `platforms` (JSON array)
- `created_at`, `updated_at`

#### social_content
- `id` (PK)
- `influencer_id` (FK)
- `platform`, `content_type`
- `external_id` (Instagram media ID)
- `caption`, `hashtags` (JSON), `mentions` (JSON)
- `media_urls` (JSON), `thumbnail_url`, `video_url`
- `location_name`, `location_lat`, `location_lng`
- `city`, `country`
- `likes_count`, `comments_count`, `shares_count`, `saves_count`, `views_count`
- `posted_at`
- `ai_tags` (JSON), `sentiment_score`
- `is_sponsored`, `sponsor_brand`

#### user_influencer_follows
- `user_id` (FK)
- `influencer_id` (FK)
- `followed_at`

#### saved_content
- `id` (PK)
- `user_id` (FK)
- `content_id` (FK)
- `saved_at`, `notes`, `collection_name`

#### collections
- `id` (PK)
- `title`, `description`, `cover_image_url`
- `collection_type`, `destinations` (JSON)
- `creator_type`, `creator_id`
- `view_count`, `save_count`, `share_count`
- `is_featured`, `is_public`

---

## 📊 Trending Algorithm

The trending score is calculated using:

```python
trending_score = (
    (post_growth * 0.3) +
    (engagement_rate * 0.25) +
    (influencer_activity * 0.2) +
    (hashtag_velocity * 0.15) +
    (sentiment_score * 0.1)
)
```

Factors:
1. **Post Growth** (30%): Week-over-week increase in posts
2. **Engagement Rate** (25%): Average likes, comments, shares
3. **Influencer Activity** (20%): Posts from verified influencers
4. **Hashtag Velocity** (15%): Speed of hashtag adoption
5. **Sentiment Score** (10%): Positive vs negative mentions

---

## 🎨 UI Components

### SocialFeed
- Tab navigation (For You, Following, Trending)
- Filter sidebar
- Masonry/grid layout
- Infinite scroll
- Pull-to-refresh

### InfluencerHub
- Category filter pills
- Search bar
- Influencer cards with stats
- Follow buttons
- Detail modal with tabs

### TrendingDestinations
- Hero section for #1 trending
- Ranking cards
- Growth indicators
- Featured content preview

### TripInspiration
- Category tabs
- Inspiration cards
- Save/Add actions
- Detail modal with trip planning

---

## 🔐 Instagram API Integration

### Required Permissions
- `instagram_basic`: Read Instagram profile info
- `instagram_content_publish`: Publish content
- `pages_read_engagement`: Read page engagement

### OAuth Flow
1. User clicks "Connect Instagram"
2. Redirect to Instagram OAuth
3. User authorizes app
4. Receive access token
5. Exchange for long-lived token
6. Store and use for API calls

### Rate Limits
- 200 calls/hour for user data
- 1000 calls/hour for media
- Implement caching to respect limits

---

## 🚀 Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Set up database models
- [ ] Create API endpoints
- [ ] Basic frontend components
- [ ] Mock data for testing

### Phase 2: Feed & Content (Week 3-4)
- [ ] Social feed implementation
- [ ] Content cards and interactions
- [ ] Save/bookmark functionality
- [ ] User preferences

### Phase 3: Influencers (Week 5-6)
- [ ] Influencer profiles
- [ ] Follow/unfollow system
- [ ] Influencer discovery
- [ ] Recommended influencers

### Phase 4: Trending (Week 7-8)
- [ ] Trending algorithm
- [ ] Real-time updates
- [ ] Trending destinations page
- [ ] Hashtag tracking

### Phase 5: Instagram Integration (Week 9-10)
- [ ] OAuth connection
- [ ] Content import
- [ ] Share to Instagram
- [ ] Webhook handling

### Phase 6: Polish & Launch (Week 11-12)
- [ ] Performance optimization
- [ ] Analytics
- [ ] Documentation
- [ ] Launch

---

## 💡 Future Enhancements

- **TikTok Integration**: Short-form video content
- **YouTube Integration**: Long-form travel vlogs
- **Live Streams**: Real-time travel experiences
- **AR Filters**: Destination preview filters
- **Collab Features**: Plan trips with friends
- **Monetization**: Influencer marketplace
- **AI Caption Generator**: Auto-generate travel captions

---

## 📈 Success Metrics

- User engagement time on social features
- Number of saved content items
- Influencer follow rate
- Content share rate
- Trip bookings from social content
- Instagram connection rate

---

**Note**: This is a comprehensive design document. Implementation should follow the existing patterns in the codebase for consistency.
