"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Users,
  Award,
  MapPin,
  Camera,
  TrendingUp,
  Filter,
  Search,
  CheckCircle,
  ExternalLink,
  BookOpen,
  Grid3X3,
  Heart,
} from "lucide-react";

// Types
interface Influencer {
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
}

interface InfluencerHubProps {
  onInfluencerSelect?: (influencer: Influencer) => void;
}

// Mock data
const MOCK_INFLUENCERS: Influencer[] = [
  {
    id: "1",
    username: "wanderlust_sarah",
    display_name: "Sarah Mitchell",
    bio: "Travel photographer capturing the world's hidden gems | 50+ countries | Tips & guides",
    profile_image_url: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400",
    followers_count: 245000,
    following_count: 890,
    posts_count: 1243,
    tier: "micro",
    categories: ["luxury", "food", "culture", "photography"],
    top_destinations: ["France", "Italy", "Japan", "Greece"],
    specialties: ["hidden gems", "luxury hotels", "local cuisine", "photography spots"],
    engagement_rate: 4.2,
    avg_likes: 12500,
    is_verified: true,
    is_featured: true,
    platforms: ["instagram", "youtube", "tiktok"],
  },
  {
    id: "2",
    username: "adventure_mike",
    display_name: "Mike Chen",
    bio: "Adventure seeker | Mountain climber | Drone pilot | Living life on the edge",
    profile_image_url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400",
    followers_count: 890000,
    following_count: 450,
    posts_count: 892,
    tier: "macro",
    categories: ["adventure", "photography", "mountains"],
    top_destinations: ["Nepal", "New Zealand", "Iceland", "Peru"],
    specialties: ["hiking trails", "drone photography", "extreme sports", "gear reviews"],
    engagement_rate: 3.8,
    avg_likes: 32000,
    is_verified: true,
    is_featured: true,
    platforms: ["instagram", "youtube"],
  },
  {
    id: "3",
    username: "budget_backpacker",
    display_name: "Alex & Emma",
    bio: "Couple traveling the world on $50/day | Budget tips | Hostel life | Street food",
    profile_image_url: "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=400",
    followers_count: 156000,
    following_count: 1200,
    posts_count: 2100,
    tier: "micro",
    categories: ["budget", "backpacker", "food", "couple"],
    top_destinations: ["Thailand", "Vietnam", "Mexico", "Portugal"],
    specialties: ["budget tips", "hostel reviews", "street food guides", "overland travel"],
    engagement_rate: 5.1,
    avg_likes: 8900,
    is_verified: false,
    is_featured: false,
    platforms: ["instagram", "tiktok"],
  },
  {
    id: "4",
    username: "solo.female.traveler",
    display_name: "Jessica Park",
    bio: "Solo female traveler | Safety tips | Empowering women to explore | 30+ countries alone",
    profile_image_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400",
    followers_count: 523000,
    following_count: 670,
    posts_count: 1567,
    tier: "macro",
    categories: ["solo_female", "culture", "wellness"],
    top_destinations: ["India", "Morocco", "Turkey", "Colombia"],
    specialties: ["solo travel safety", "female-friendly stays", "cultural immersion", "yoga retreats"],
    engagement_rate: 4.8,
    avg_likes: 28500,
    is_verified: true,
    is_featured: true,
    platforms: ["instagram", "youtube", "blog"],
  },
  {
    id: "5",
    username: "familytravel_dad",
    display_name: "David Thompson",
    bio: "Dad of 3 | Family travel expert | Kid-friendly destinations | Making memories",
    profile_image_url: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400",
    followers_count: 89000,
    following_count: 560,
    posts_count: 678,
    tier: "nano",
    categories: ["family", "budget", "culture"],
    top_destinations: ["USA", "UK", "Spain", "Costa Rica"],
    specialties: ["kid-friendly activities", "family hotels", "road trips", "travel with toddlers"],
    engagement_rate: 6.2,
    avg_likes: 5600,
    is_verified: false,
    is_featured: false,
    platforms: ["instagram", "tiktok"],
  },
];

const CATEGORIES = [
  { id: "all", label: "All", icon: Users },
  { id: "luxury", label: "Luxury", icon: Award },
  { id: "budget", label: "Budget", icon: TrendingUp },
  { id: "adventure", label: "Adventure", icon: MapPin },
  { id: "food", label: "Food", icon: Camera },
  { id: "solo_female", label: "Solo Female", icon: Users },
  { id: "family", label: "Family", icon: Users },
  { id: "photography", label: "Photography", icon: Camera },
];

// Influencer Card Component
function InfluencerCard({
  influencer,
  onClick,
}: {
  influencer: Influencer;
  onClick?: (influencer: Influencer) => void;
}) {
  const [isFollowing, setIsFollowing] = useState(false);

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case "nano":
        return "bg-gray-100 text-gray-700";
      case "micro":
        return "bg-blue-100 text-blue-700";
      case "mid":
        return "bg-purple-100 text-purple-700";
      case "macro":
        return "bg-pink-100 text-pink-700";
      case "mega":
        return "bg-yellow-100 text-yellow-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="bg-white rounded-2xl shadow-lg overflow-hidden cursor-pointer group"
      onClick={() => onClick?.(influencer)}
    >
      {/* Cover Image Area */}
      <div className="h-24 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 relative">
        {influencer.is_featured && (
          <div className="absolute top-3 right-3 bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1">
            <Award className="w-3 h-3" />
            Featured
          </div>
        )}
      </div>

      {/* Profile Info */}
      <div className="px-5 pb-5">
        {/* Avatar */}
        <div className="relative -mt-12 mb-3">
          <img
            src={influencer.profile_image_url}
            alt={influencer.display_name}
            className="w-24 h-24 rounded-full object-cover border-4 border-white shadow-lg"
          />
          {influencer.is_verified && (
            <div className="absolute bottom-0 right-0 bg-blue-500 text-white rounded-full p-1">
              <CheckCircle className="w-4 h-4" />
            </div>
          )}
        </div>

        {/* Name & Tier */}
        <div className="mb-2">
          <h3 className="font-bold text-gray-900 text-lg">{influencer.display_name}</h3>
          <p className="text-gray-500 text-sm">@{influencer.username}</p>
        </div>

        {/* Tier Badge */}
        <span
          className={`inline-block text-xs font-semibold px-2 py-1 rounded-full mb-3 ${getTierColor(
            influencer.tier
          )}`}
        >
          {influencer.tier.charAt(0).toUpperCase() + influencer.tier.slice(1)} Influencer
        </span>

        {/* Bio */}
        <p className="text-gray-600 text-sm mb-4 line-clamp-2">{influencer.bio}</p>

        {/* Stats */}
        <div className="flex items-center justify-between mb-4 py-3 border-y border-gray-100">
          <div className="text-center">
            <div className="font-bold text-gray-900">{formatNumber(influencer.followers_count)}</div>
            <div className="text-xs text-gray-500">Followers</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-gray-900">{influencer.engagement_rate}%</div>
            <div className="text-xs text-gray-500">Engagement</div>
          </div>
          <div className="text-center">
            <div className="font-bold text-gray-900">{influencer.posts_count}</div>
            <div className="text-xs text-gray-500">Posts</div>
          </div>
        </div>

        {/* Categories */}
        <div className="flex flex-wrap gap-1 mb-4">
          {influencer.categories.slice(0, 3).map((cat) => (
            <span
              key={cat}
              className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full"
            >
              {cat.replace("_", " ")}
            </span>
          ))}
          {influencer.categories.length > 3 && (
            <span className="text-xs text-gray-400 px-1">
              +{influencer.categories.length - 3}
            </span>
          )}
        </div>

        {/* Top Destinations */}
        <div className="flex items-center gap-1 text-sm text-gray-600 mb-4">
          <MapPin className="w-4 h-4 text-gray-400" />
          <span className="truncate">
            {influencer.top_destinations.slice(0, 3).join(" • ")}
          </span>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsFollowing(!isFollowing);
            }}
            className={`flex-1 py-2 rounded-xl font-medium transition-colors ${
              isFollowing
                ? "bg-gray-100 text-gray-700 hover:bg-gray-200"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {isFollowing ? "Following" : "Follow"}
          </button>
          <button className="p-2 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
            <ExternalLink className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// Influencer Detail Modal
function InfluencerDetail({
  influencer,
  onClose,
}: {
  influencer: Influencer;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"overview" | "content" | "guides">("overview");

  const tabs = [
    { id: "overview", label: "Overview", icon: Users },
    { id: "content", label: "Content", icon: Grid3X3 },
    { id: "guides", label: "Guides", icon: BookOpen },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="h-32 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 bg-white/20 hover:bg-white/30 rounded-full flex items-center justify-center text-white transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="px-8 pb-8">
          {/* Profile Header */}
          <div className="flex items-end -mt-16 mb-6">
            <img
              src={influencer.profile_image_url}
              alt={influencer.display_name}
              className="w-32 h-32 rounded-full object-cover border-4 border-white shadow-xl"
            />
            <div className="ml-6 mb-2 flex-1">
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-gray-900">{influencer.display_name}</h2>
                {influencer.is_verified && (
                  <CheckCircle className="w-6 h-6 text-blue-500" />
                )}
              </div>
              <p className="text-gray-500">@{influencer.username}</p>
            </div>
            <div className="flex gap-3 mb-2">
              <button className="px-6 py-2 bg-blue-600 text-white rounded-full font-medium hover:bg-blue-700 transition-colors">
                Follow
              </button>
              <button className="px-6 py-2 border border-gray-300 rounded-full font-medium hover:bg-gray-50 transition-colors">
                View Profile
              </button>
            </div>
          </div>

          {/* Bio */}
          <p className="text-gray-700 mb-6 max-w-2xl">{influencer.bio}</p>

          {/* Stats Row */}
          <div className="flex gap-8 mb-6">
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {(influencer.followers_count / 1000).toFixed(1)}K
              </div>
              <div className="text-gray-500">Followers</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {influencer.engagement_rate}%
              </div>
              <div className="text-gray-500">Engagement</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{influencer.posts_count}</div>
              <div className="text-gray-500">Posts</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {(influencer.avg_likes / 1000).toFixed(1)}K
              </div>
              <div className="text-gray-500">Avg. Likes</div>
            </div>
          </div>

          {/* Specialties */}
          <div className="mb-6">
            <h3 className="font-semibold text-gray-900 mb-2">Specialties</h3>
            <div className="flex flex-wrap gap-2">
              {influencer.specialties.map((specialty) => (
                <span
                  key={specialty}
                  className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-sm"
                >
                  {specialty}
                </span>
              ))}
            </div>
          </div>

          {/* Top Destinations */}
          <div className="mb-6">
            <h3 className="font-semibold text-gray-900 mb-2">Top Destinations</h3>
            <div className="flex flex-wrap gap-2">
              {influencer.top_destinations.map((dest) => (
                <span
                  key={dest}
                  className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm flex items-center gap-1"
                >
                  <MapPin className="w-3 h-3" />
                  {dest}
                </span>
              ))}
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <div className="flex gap-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 py-3 border-b-2 font-medium transition-colors ${
                    activeTab === tab.id
                      ? "border-blue-600 text-blue-600"
                      : "border-transparent text-gray-600 hover:text-gray-900"
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <div className="min-h-[200px]">
            {activeTab === "overview" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-xl p-4">
                  <h4 className="font-semibold text-gray-900 mb-2">Content Performance</h4>
                  <p className="text-gray-600">Average engagement rate is {influencer.engagement_rate}%, which is excellent for their follower tier.</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <h4 className="font-semibold text-gray-900 mb-2">Audience Insights</h4>
                  <p className="text-gray-600">Primary audience: 25-34 year olds interested in {influencer.categories.join(", ")}.</p>
                </div>
              </div>
            )}
            {activeTab === "content" && (
              <div className="text-center py-12 text-gray-500">
                <Grid3X3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Content grid would load here</p>
              </div>
            )}
            {activeTab === "guides" && (
              <div className="text-center py-12 text-gray-500">
                <BookOpen className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Travel guides would load here</p>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// Main Component
export default function InfluencerHub({ onInfluencerSelect }: InfluencerHubProps) {
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedInfluencer, setSelectedInfluencer] = useState<Influencer | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const filteredInfluencers = MOCK_INFLUENCERS.filter((inf) => {
    const matchesCategory =
      selectedCategory === "all" || inf.categories.includes(selectedCategory);
    const matchesSearch =
      inf.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inf.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inf.specialties.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Travel Influencers</h1>
        <p className="text-gray-600">
          Discover top travel creators and get inspired by their journeys
        </p>
      </div>

      {/* Search & Filters */}
      <div className="mb-6 space-y-4">
        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search influencers, specialties, destinations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Category Pills */}
        <div className="flex gap-2 flex-wrap">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full font-medium transition-colors ${
                selectedCategory === cat.id
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50"
              }`}
            >
              <cat.icon className="w-4 h-4" />
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results Count */}
      <div className="flex items-center justify-between mb-6">
        <p className="text-gray-600">
          Showing <span className="font-semibold text-gray-900">{filteredInfluencers.length}</span> influencers
        </p>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select className="bg-transparent text-sm text-gray-600 focus:outline-none">
            <option>Sort by: Followers</option>
            <option>Sort by: Engagement</option>
            <option>Sort by: Recent</option>
          </select>
        </div>
      </div>

      {/* Influencer Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredInfluencers.map((influencer) => (
          <InfluencerCard
            key={influencer.id}
            influencer={influencer}
            onClick={setSelectedInfluencer}
          />
        ))}
      </div>

      {/* Empty State */}
      {filteredInfluencers.length === 0 && (
        <div className="text-center py-16">
          <Users className="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No influencers found</h3>
          <p className="text-gray-500">Try adjusting your filters or search query</p>
        </div>
      )}

      {/* Detail Modal */}
      {selectedInfluencer && (
        <InfluencerDetail
          influencer={selectedInfluencer}
          onClose={() => setSelectedInfluencer(null)}
        />
      )}
    </div>
  );
}
