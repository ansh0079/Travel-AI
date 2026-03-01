"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Heart,
  MessageCircle,
  Bookmark,
  Share2,
  MapPin,
  UserPlus,
  TrendingUp,
  Filter,
  Loader2,
  Play,
  ImageIcon,
  Film,
  Grid3X3,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

// Types
interface Influencer {
  id: string;
  username: string;
  display_name: string;
  profile_image_url?: string;
  followers_count: number;
  tier: "nano" | "micro" | "mid" | "macro" | "mega";
  categories: string[];
  is_verified: boolean;
}

interface SocialContent {
  id: string;
  platform: string;
  content_type: "photo" | "video" | "reel" | "carousel" | "story";
  media_urls: string[];
  thumbnail_url: string;
  caption?: string;
  hashtags: string[];
  location_name?: string;
  city?: string;
  country?: string;
  likes_count: number;
  comments_count: number;
  posted_at: string;
  influencer: Influencer;
  is_sponsored: boolean;
  sponsor_brand?: string;
}

interface SocialFeedProps {
  feedType?: "foryou" | "following" | "trending" | "destination" | "influencer";
  destinationId?: string;
  influencerId?: string;
}

// Mock data for demonstration
const MOCK_CONTENT: SocialContent[] = [
  {
    id: "1",
    platform: "instagram",
    content_type: "photo",
    media_urls: ["https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800"],
    thumbnail_url: "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800",
    caption: "Paris in the spring is absolutely magical! ✨ The cherry blossoms along the Seine are in full bloom. Can't wait to share my complete guide to hidden gems in Paris! 🌸",
    hashtags: ["paris", "france", "travel", "spring", "cherryblossoms", "wanderlust"],
    location_name: "Seine River, Paris",
    city: "Paris",
    country: "France",
    likes_count: 45231,
    comments_count: 892,
    posted_at: "2024-03-15T10:30:00Z",
    influencer: {
      id: "inf1",
      username: "wanderlust_sarah",
      display_name: "Sarah Mitchell",
      profile_image_url: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200",
      followers_count: 245000,
      tier: "micro",
      categories: ["luxury", "food", "culture"],
      is_verified: true,
    },
    is_sponsored: false,
  },
  {
    id: "2",
    platform: "instagram",
    content_type: "reel",
    media_urls: ["https://example.com/video.mp4"],
    thumbnail_url: "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800",
    caption: "POV: You finally made it to Bali's most Instagrammable waterfall 💦 Save this for your Bali trip!",
    hashtags: ["bali", "indonesia", "waterfall", "travelreels", "wanderlust"],
    location_name: "Tegenungan Waterfall",
    city: "Ubud",
    country: "Indonesia",
    likes_count: 128500,
    comments_count: 2341,
    posted_at: "2024-03-14T15:20:00Z",
    influencer: {
      id: "inf2",
      username: "adventure_mike",
      display_name: "Mike Chen",
      profile_image_url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200",
      followers_count: 890000,
      tier: "macro",
      categories: ["adventure", "photography"],
      is_verified: true,
    },
    is_sponsored: true,
    sponsor_brand: "GoPro",
  },
  {
    id: "3",
    platform: "instagram",
    content_type: "carousel",
    media_urls: [
      "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800",
      "https://images.unsplash.com/photo-1523906834658-6e24ef2386f9?w=800",
      "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?w=800",
    ],
    thumbnail_url: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800",
    caption: "Cinque Terre is even more beautiful in person than in photos 😍 Swipe for my favorite spots in each village! Which one would you visit first?",
    hashtags: ["cinqueterre", "italy", "mediterranean", "travelguide", "europe"],
    location_name: "Cinque Terre",
    city: "La Spezia",
    country: "Italy",
    likes_count: 67342,
    comments_count: 1567,
    posted_at: "2024-03-13T09:15:00Z",
    influencer: {
      id: "inf3",
      username: "italywithlisa",
      display_name: "Lisa Romano",
      profile_image_url: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200",
      followers_count: 156000,
      tier: "micro",
      categories: ["culture", "food", "photography"],
      is_verified: false,
    },
    is_sponsored: false,
  },
];

// Content Card Component
function ContentCard({ content }: { content: SocialContent }) {
  const [isLiked, setIsLiked] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [showFullCaption, setShowFullCaption] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    if (days === 0) return "Today";
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days} days ago`;
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
    return `${Math.floor(days / 30)} months ago`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl shadow-lg overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <img
              src={content.influencer.profile_image_url}
              alt={content.influencer.display_name}
              className="w-10 h-10 rounded-full object-cover ring-2 ring-gray-100"
            />
            {content.influencer.is_verified && (
              <div className="absolute -bottom-1 -right-1 bg-blue-500 text-white rounded-full p-0.5">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{content.influencer.display_name}</h3>
            <p className="text-sm text-gray-500">@{content.influencer.username}</p>
          </div>
        </div>
        <button className="text-blue-600 font-medium text-sm hover:bg-blue-50 px-3 py-1.5 rounded-full transition-colors">
          Follow
        </button>
      </div>

      {/* Media */}
      <div className="relative aspect-square bg-gray-100">
        <img
          src={content.thumbnail_url}
          alt="Travel content"
          className="w-full h-full object-cover"
        />
        
        {/* Content Type Badge */}
        <div className="absolute top-3 left-3 bg-black/50 backdrop-blur-sm text-white text-xs font-medium px-2 py-1 rounded-full flex items-center gap-1">
          {content.content_type === "reel" && <Film className="w-3 h-3" />}
          {content.content_type === "photo" && <ImageIcon className="w-3 h-3" />}
          {content.content_type === "carousel" && <Grid3X3 className="w-3 h-3" />}
          {content.content_type === "video" && <Play className="w-3 h-3" />}
          <span className="capitalize">{content.content_type}</span>
        </div>

        {/* Sponsored Badge */}
        {content.is_sponsored && (
          <div className="absolute top-3 right-3 bg-yellow-500/90 text-white text-xs font-medium px-2 py-1 rounded-full">
            Sponsored by {content.sponsor_brand}
          </div>
        )}

        {/* Carousel Navigation */}
        {content.content_type === "carousel" && content.media_urls.length > 1 && (
          <>
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1">
              {content.media_urls.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentImageIndex(idx)}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    idx === currentImageIndex ? "bg-white" : "bg-white/50"
                  }`}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Actions */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsLiked(!isLiked)}
              className={`transition-colors ${isLiked ? "text-red-500" : "text-gray-700 hover:text-red-500"}`}
            >
              <Heart className={`w-6 h-6 ${isLiked ? "fill-current" : ""}`} />
            </button>
            <button className="text-gray-700 hover:text-blue-500 transition-colors">
              <MessageCircle className="w-6 h-6" />
            </button>
            <button className="text-gray-700 hover:text-green-500 transition-colors">
              <Share2 className="w-6 h-6" />
            </button>
          </div>
          <button
            onClick={() => setIsSaved(!isSaved)}
            className={`transition-colors ${isSaved ? "text-yellow-500" : "text-gray-700 hover:text-yellow-500"}`}
          >
            <Bookmark className={`w-6 h-6 ${isSaved ? "fill-current" : ""}`} />
          </button>
        </div>

        {/* Stats */}
        <div className="text-sm font-semibold text-gray-900 mb-2">
          {formatNumber(content.likes_count)} likes
        </div>

        {/* Caption */}
        <div className="mb-3">
          <span className="font-semibold text-gray-900 mr-2">{content.influencer.username}</span>
          <span className="text-gray-700">
            {showFullCaption ? content.caption : `${content.caption?.slice(0, 100)}${content.caption && content.caption.length > 100 ? "..." : ""}`}
          </span>
          {content.caption && content.caption.length > 100 && (
            <button
              onClick={() => setShowFullCaption(!showFullCaption)}
              className="text-gray-500 text-sm ml-1 hover:text-gray-700"
            >
              {showFullCaption ? "less" : "more"}
            </button>
          )}
        </div>

        {/* Hashtags */}
        <div className="flex flex-wrap gap-1 mb-3">
          {content.hashtags.slice(0, 5).map((tag) => (
            <span key={tag} className="text-blue-600 text-sm hover:underline cursor-pointer">
              #{tag}
            </span>
          ))}
          {content.hashtags.length > 5 && (
            <span className="text-gray-500 text-sm">+{content.hashtags.length - 5} more</span>
          )}
        </div>

        {/* Location & Time */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          {content.location_name && (
            <div className="flex items-center gap-1 hover:text-gray-700 cursor-pointer">
              <MapPin className="w-4 h-4" />
              <span>{content.location_name}</span>
            </div>
          )}
          <span>{formatTime(content.posted_at)}</span>
        </div>
      </div>
    </motion.div>
  );
}

// Main Feed Component
export default function SocialFeed({
  feedType = "foryou",
  destinationId,
  influencerId,
}: SocialFeedProps) {
  const [activeTab, setActiveTab] = useState<"foryou" | "following" | "trending">("foryou");
  const [content, setContent] = useState<SocialContent[]>(MOCK_CONTENT);
  const [isLoading, setIsLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const tabs = [
    { id: "foryou", label: "For You", icon: null },
    { id: "following", label: "Following", icon: UserPlus },
    { id: "trending", label: "Trending", icon: TrendingUp },
  ];

  const loadMore = () => {
    // TODO: Implement pagination
    console.log("Load more content");
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-white/80 backdrop-blur-md border-b border-gray-200">
        <div className="flex items-center justify-between p-4">
          <h1 className="text-xl font-bold text-gray-900">Discover</h1>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <Filter className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors relative ${
                activeTab === tab.id
                  ? "text-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab.icon && <tab.icon className="w-4 h-4" />}
              {tab.label}
              {activeTab === tab.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600"
                />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-gray-50 border-b border-gray-200 overflow-hidden"
          >
            <div className="p-4 space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Content Type</label>
                <div className="flex gap-2 flex-wrap">
                  {["All", "Photos", "Videos", "Reels", "Guides"].map((type) => (
                    <button
                      key={type}
                      className="px-3 py-1.5 bg-white border border-gray-300 rounded-full text-sm hover:border-blue-500 hover:text-blue-600 transition-colors"
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Categories</label>
                <div className="flex gap-2 flex-wrap">
                  {["Luxury", "Budget", "Adventure", "Food", "Culture"].map((cat) => (
                    <button
                      key={cat}
                      className="px-3 py-1.5 bg-white border border-gray-300 rounded-full text-sm hover:border-blue-500 hover:text-blue-600 transition-colors"
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content Feed */}
      <div className="p-4 space-y-6">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : (
          <>
            {content.map((item) => (
              <ContentCard key={item.id} content={item} />
            ))}

            {/* Load More */}
            <button
              onClick={loadMore}
              className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700 font-medium transition-colors"
            >
              Load More
            </button>
          </>
        )}
      </div>
    </div>
  );
}
