// Social API Service
// Handles all social media and influencer-related API calls
// NOTE: this file is reserved for future use and not currently wired up

// Minimal axios-like stub so this file compiles without a live apiClient
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const apiClient = {
  get: async (_url: string, _cfg?: any) => ({ data: {} }),
  post: async (_url: string, _body?: any, _cfg?: any) => ({ data: {} }),
};

// Types
export interface Influencer {
  id: string;
  username: string;
  display_name: string;
  bio?: string;
  profile_image_url?: string;
  followers_count: number;
  following_count: number;
  posts_count: number;
  tier: "nano" | "micro" | "mid" | "macro" | "mega";
  categories: string[];
  top_destinations: string[];
  specialties: string[];
  engagement_rate: number;
  avg_likes: number;
  is_verified: boolean;
  is_featured: boolean;
  platforms: string[];
  created_at: string;
  updated_at: string;
}

export interface SocialContent {
  id: string;
  platform: "instagram" | "youtube" | "tiktok" | "twitter" | "blog";
  content_type: "photo" | "video" | "reel" | "carousel" | "story" | "guide" | "live";
  external_id: string;
  caption?: string;
  hashtags: string[];
  mentions: string[];
  media_urls: string[];
  thumbnail_url: string;
  video_url?: string;
  location_name?: string;
  location_lat?: number;
  location_lng?: number;
  city?: string;
  country?: string;
  likes_count: number;
  comments_count: number;
  shares_count: number;
  saves_count: number;
  views_count?: number;
  posted_at: string;
  influencer_id: string;
  influencer: Influencer;
  ai_tags: string[];
  sentiment_score?: number;
  is_sponsored: boolean;
  sponsor_brand?: string;
  user_saved?: boolean;
  user_liked?: boolean;
}

export interface TrendingDestination {
  destination_id: string;
  destination_name: string;
  country: string;
  image_url?: string;
  trending_score: number;
  growth_percentage: number;
  posts_count_7d: number;
  total_engagement_7d: number;
  top_influencers: Influencer[];
  featured_content: SocialContent[];
  trending_reason: "viral_reel" | "influencer_feature" | "event" | "seasonal" | "hidden_gem";
  related_hashtags: string[];
  why_trending: string;
}

export interface Collection {
  id: string;
  title: string;
  description?: string;
  cover_image_url?: string;
  collection_type: "guide" | "itinerary" | "bucket_list" | "hidden_gems" | "seasonal";
  destinations: string[];
  tags: string[];
  creator_type: "influencer" | "staff" | "community" | "brand";
  creator_id?: string;
  creator?: Influencer;
  view_count: number;
  save_count: number;
  share_count: number;
  is_featured: boolean;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface TrendingHashtag {
  hashtag: string;
  post_count: number;
  engagement_rate: number;
  trending_score: number;
  related_destinations: string[];
  sample_posts: SocialContent[];
}

// Feed API
export const getSocialFeed = async (params: {
  feed_type?: "foryou" | "following" | "trending" | "destination" | "influencer";
  destination_id?: string;
  influencer_id?: string;
  content_types?: string[];
  cursor?: string;
  limit?: number;
}) => {
  const response = await apiClient.post("/social/feed", params);
  return response.data;
};

export const getTrendingContent = async (period: "today" | "week" | "month" = "week", limit: number = 20) => {
  const response = await apiClient.get(`/social/feed/trending?period=${period}&limit=${limit}`);
  return response.data;
};

export const exploreContent = async (params: {
  lat?: number;
  lng?: number;
  radius_km?: number;
  content_type?: string;
  limit?: number;
}) => {
  const response = await apiClient.get("/social/feed/explore", { params });
  return response.data;
};

// Influencer API
export const getInfluencers = async (params: {
  category?: string;
  tier?: string;
  destination?: string;
  featured_only?: boolean;
  sort_by?: "followers" | "engagement" | "recent" | "trending";
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

export const getInfluencerContent = async (
  influencerId: string,
  params?: {
    content_type?: string;
    destination?: string;
    limit?: number;
    cursor?: string;
  }
) => {
  const response = await apiClient.get(`/social/influencers/${influencerId}/content`, { params });
  return response.data;
};

export const getInfluencerGuides = async (influencerId: string) => {
  const response = await apiClient.get(`/social/influencers/${influencerId}/guides`);
  return response.data;
};

export const getRecommendedInfluencers = async (limit: number = 10) => {
  const response = await apiClient.get(`/social/influencers/recommended?limit=${limit}`);
  return response.data;
};

export const followInfluencer = async (influencerId: string) => {
  const response = await apiClient.post(`/social/influencers/${influencerId}/follow`);
  return response.data;
};

export const unfollowInfluencer = async (influencerId: string) => {
  const response = await apiClient.post(`/social/influencers/${influencerId}/unfollow`);
  return response.data;
};

// Content API
export const getContentDetails = async (contentId: string) => {
  const response = await apiClient.get(`/social/content/${contentId}`);
  return response.data;
};

export const saveContent = async (contentId: string, collectionName?: string, notes?: string) => {
  const response = await apiClient.post(`/social/content/${contentId}/save`, {
    collection_name: collectionName,
    notes,
  });
  return response.data;
};

export const unsaveContent = async (contentId: string) => {
  const response = await apiClient.post(`/social/content/${contentId}/unsave`);
  return response.data;
};

export const getRelatedContent = async (contentId: string, limit: number = 10) => {
  const response = await apiClient.get(`/social/content/${contentId}/related?limit=${limit}`);
  return response.data;
};

export const getSimilarDestinationsFromContent = async (contentId: string, limit: number = 5) => {
  const response = await apiClient.get(`/social/content/${contentId}/similar-destinations?limit=${limit}`);
  return response.data;
};

// Trending API
export const getTrendingDestinations = async (params: {
  period?: "today" | "week" | "month";
  region?: string;
  limit?: number;
}) => {
  const response = await apiClient.get("/social/trending/destinations", { params });
  return response.data;
};

export const getTrendingHashtags = async (
  period: "today" | "week" | "month" = "week",
  limit: number = 20
) => {
  const response = await apiClient.get(`/social/trending/hashtags?period=${period}&limit=${limit}`);
  return response.data;
};

export const getTrendingExperiences = async (params?: { destination?: string; limit?: number }) => {
  const response = await apiClient.get("/social/trending/experiences", { params });
  return response.data;
};

// Collections API
export const getCollections = async (params: {
  collection_type?: "guide" | "itinerary" | "bucket_list" | "hidden_gems" | "seasonal";
  featured_only?: boolean;
  influencer_id?: string;
  destination?: string;
  limit?: number;
  offset?: number;
}) => {
  const response = await apiClient.get("/social/collections", { params });
  return response.data;
};

export const getCollectionDetails = async (collectionId: string) => {
  const response = await apiClient.get(`/social/collections/${collectionId}`);
  return response.data;
};

export const saveCollection = async (collectionId: string) => {
  const response = await apiClient.post(`/social/collections/${collectionId}/save`);
  return response.data;
};

// Discover API
export const discoverContent = async (params: {
  category?: string;
  destination?: string;
  hashtag?: string;
  content_type?: string;
  min_engagement?: number;
  date_range?: "today" | "week" | "month" | "year";
  limit?: number;
  offset?: number;
}) => {
  const response = await apiClient.post("/social/discover", params);
  return response.data;
};

export const searchSocial = async (
  query: string,
  type: "all" | "influencers" | "content" | "destinations" | "hashtags" = "all",
  limit: number = 20
) => {
  const response = await apiClient.get(`/social/search?q=${encodeURIComponent(query)}&type=${type}&limit=${limit}`);
  return response.data;
};

// User Social API
export const getUserSavedContent = async (collection?: string) => {
  const params = collection ? { collection } : {};
  const response = await apiClient.get("/social/user/saved", { params });
  return response.data;
};

export const getUserFollowing = async () => {
  const response = await apiClient.get("/social/user/following");
  return response.data;
};

export const updateSocialPreferences = async (preferences: {
  followed_influencers?: string[];
  followed_hashtags?: string[];
  followed_destinations?: string[];
  preferred_content_types?: string[];
  preferred_categories?: string[];
  hide_sponsored?: boolean;
  discover_new_influencers?: boolean;
  show_friend_activity?: boolean;
}) => {
  const response = await apiClient.post("/social/user/preferences", preferences);
  return response.data;
};

// Instagram Integration API
export const connectInstagramAccount = async (accessToken: string, instagramUserId?: string) => {
  const response = await apiClient.post("/social/instagram/connect", {
    access_token: accessToken,
    instagram_user_id: instagramUserId,
  });
  return response.data;
};

export const disconnectInstagramAccount = async () => {
  const response = await apiClient.post("/social/instagram/disconnect");
  return response.data;
};

export const importInstagramPosts = async (maxPosts: number = 50) => {
  const response = await apiClient.get(`/social/instagram/import?max_posts=${maxPosts}`);
  return response.data;
};

export const shareToInstagram = async (params: {
  content_type: "story" | "post" | "reel";
  media_url: string;
  caption?: string;
  hashtags?: string[];
  location_name?: string;
}) => {
  const response = await apiClient.post("/social/share/instagram", params);
  return response.data;
};

// Analytics API
export const getInfluencerAnalytics = async (
  influencerId: string,
  period: "week" | "month" | "year" = "month"
) => {
  const response = await apiClient.get(`/social/analytics/influencer/${influencerId}?period=${period}`);
  return response.data;
};

export const getSocialStatsOverview = async () => {
  const response = await apiClient.get("/social/stats/overview");
  return response.data;
};

// React Query Hooks helpers
export const socialQueryKeys = {
  feed: (params: any) => ["social", "feed", params],
  trending: (period: string) => ["social", "trending", period],
  influencers: (params: any) => ["social", "influencers", params],
  influencer: (id: string) => ["social", "influencer", id],
  influencerContent: (id: string, params: any) => ["social", "influencer", id, "content", params],
  content: (id: string) => ["social", "content", id],
  collections: (params: any) => ["social", "collections", params],
  collection: (id: string) => ["social", "collection", id],
  trendingDestinations: (params: any) => ["social", "trending", "destinations", params],
  trendingHashtags: (period: string) => ["social", "trending", "hashtags", period],
  saved: (collection?: string) => ["social", "user", "saved", collection],
  following: () => ["social", "user", "following"],
  search: (query: string, type: string) => ["social", "search", query, type],
};
