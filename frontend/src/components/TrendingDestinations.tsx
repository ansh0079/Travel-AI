"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Flame,
  ArrowUpRight,
  MapPin,
  Camera,
  Users,
  Heart,
  MessageCircle,
  ArrowRight,
  Filter,
  ChevronRight,
  Sparkles,
} from "lucide-react";

// Types
interface TrendingDestination {
  id: string;
  destination_id: string;
  destination_name: string;
  country: string;
  image_url: string;
  trending_score: number;
  growth_percentage: number;
  posts_count_7d: number;
  total_engagement_7d: number;
  top_influencers: {
    id: string;
    username: string;
    profile_image_url: string;
  }[];
  featured_content: {
    id: string;
    thumbnail_url: string;
    likes_count: number;
  }[];
  trending_reason: "viral_reel" | "influencer_feature" | "event" | "seasonal" | "hidden_gem";
  related_hashtags: string[];
  why_trending: string;
}

// Mock data
const MOCK_TRENDING: TrendingDestination[] = [
  {
    id: "1",
    destination_id: "dest1",
    destination_name: "AlUla",
    country: "Saudi Arabia",
    image_url: "https://images.unsplash.com/photo-1540324155974-7523202daa3f?w=800",
    trending_score: 98.5,
    growth_percentage: 340,
    posts_count_7d: 12500,
    total_engagement_7d: 890000,
    top_influencers: [
      { id: "1", username: "wanderlust_sarah", profile_image_url: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100" },
      { id: "2", username: "adventure_mike", profile_image_url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100" },
    ],
    featured_content: [
      { id: "c1", thumbnail_url: "https://images.unsplash.com/photo-1540324155974-7523202daa3f?w=200", likes_count: 45000 },
      { id: "c2", thumbnail_url: "https://images.unsplash.com/photo-1579606038888-f33e0df3bd3a?w=200", likes_count: 32000 },
      { id: "c3", thumbnail_url: "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?w=200", likes_count: 28000 },
    ],
    trending_reason: "viral_reel",
    related_hashtags: ["#alula", "#saudiarabia", "#desert", "#heritage"],
    why_trending: "A viral drone video showcased the stunning rock formations, garnering 5M+ views",
  },
  {
    id: "2",
    destination_id: "dest2",
    destination_name: "Madeira",
    country: "Portugal",
    image_url: "https://images.unsplash.com/photo-1569949381669-ecf31ae8e613?w=800",
    trending_score: 94.2,
    growth_percentage: 180,
    posts_count_7d: 8900,
    total_engagement_7d: 520000,
    top_influencers: [
      { id: "3", username: "europewithlisa", profile_image_url: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100" },
    ],
    featured_content: [
      { id: "c4", thumbnail_url: "https://images.unsplash.com/photo-1569949381669-ecf31ae8e613?w=200", likes_count: 28000 },
      { id: "c5", thumbnail_url: "https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=200", likes_count: 21000 },
    ],
    trending_reason: "influencer_feature",
    related_hashtags: ["#madeira", "#portugal", "#islandlife", "#nature"],
    why_trending: "Multiple macro influencers featured Madeira's levada walks this month",
  },
  {
    id: "3",
    destination_id: "dest3",
    destination_name: "Hokkaido",
    country: "Japan",
    image_url: "https://images.unsplash.com/photo-1554797589-7241bb691973?w=800",
    trending_score: 91.8,
    growth_percentage: 125,
    posts_count_7d: 15600,
    total_engagement_7d: 780000,
    top_influencers: [
      { id: "4", username: "japan_journey", profile_image_url: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100" },
    ],
    featured_content: [
      { id: "c6", thumbnail_url: "https://images.unsplash.com/photo-1554797589-7241bb691973?w=200", likes_count: 52000 },
      { id: "c7", thumbnail_url: "https://images.unsplash.com/photo-1490806843957-31f4c9a91c65?w=200", likes_count: 38000 },
    ],
    trending_reason: "seasonal",
    related_hashtags: ["#hokkaido", "#japan", "#snow", "#winter"],
    why_trending: "Cherry blossom season approaching - travelers planning spring trips",
  },
  {
    id: "4",
    destination_id: "dest4",
    destination_name: "Oaxaca",
    country: "Mexico",
    image_url: "https://images.unsplash.com/photo-1518105779142-d975f22f1b0a?w=800",
    trending_score: 88.5,
    growth_percentage: 95,
    posts_count_7d: 6700,
    total_engagement_7d: 340000,
    top_influencers: [],
    featured_content: [
      { id: "c8", thumbnail_url: "https://images.unsplash.com/photo-1518105779142-d975f22f1b0a?w=200", likes_count: 18000 },
    ],
    trending_reason: "hidden_gem",
    related_hashtags: ["#oaxaca", "#mexico", ""],
    why_trending: "Food bloggers discovering Oaxaca's incredible culinary scene",
  },
  {
    id: "5",
    destination_id: "dest5",
    destination_name: "Dolomites",
    country: "Italy",
    image_url: "https://images.unsplash.com/photo-1516426122078-c23e76319801?w=800",
    trending_score: 86.2,
    growth_percentage: 78,
    posts_count_7d: 11200,
    total_engagement_7d: 620000,
    top_influencers: [],
    featured_content: [
      { id: "c9", thumbnail_url: "https://images.unsplash.com/photo-1516426122078-c23e76319801?w=200", likes_count: 42000 },
    ],
    trending_reason: "seasonal",
    related_hashtags: ["#dolomites", "#italy", "#mountains", "#hiking"],
    why_trending: "Summer hiking season - adventure travelers flocking to the trails",
  },
];

// Components
function TrendingBadge({ reason }: { reason: TrendingDestination["trending_reason"] }) {
  const configs = {
    viral_reel: { icon: Flame, color: "bg-orange-500", label: "Viral" },
    influencer_feature: { icon: Users, color: "bg-purple-500", label: "Featured" },
    event: { icon: Sparkles, color: "bg-blue-500", label: "Event" },
    seasonal: { icon: TrendingUp, color: "bg-green-500", label: "Seasonal" },
    hidden_gem: { icon: MapPin, color: "bg-pink-500", label: "Hidden Gem" },
  };

  const config = configs[reason];
  const Icon = config.icon;

  return (
    <div className={`${config.color} text-white text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </div>
  );
}

function DestinationCard({ destination, rank }: { destination: TrendingDestination; rank: number }) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="bg-white rounded-2xl shadow-lg overflow-hidden group cursor-pointer"
    >
      {/* Image */}
      <div className="relative h-48 overflow-hidden">
        <img
          src={destination.image_url}
          alt={destination.destination_name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
        
        {/* Rank */}
        <div className="absolute top-3 left-3 w-8 h-8 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center font-bold text-gray-900">
          #{rank}
        </div>

        {/* Trending Badge */}
        <div className="absolute top-3 right-3">
          <TrendingBadge reason={destination.trending_reason} />
        </div>

        {/* Destination Info */}
        <div className="absolute bottom-3 left-3 right-3 text-white">
          <h3 className="text-xl font-bold">{destination.destination_name}</h3>
          <p className="text-white/80 text-sm flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {destination.country}
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Trending Score */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="text-2xl font-bold text-gray-900">
              {destination.trending_score}
            </div>
            <div className="text-xs text-gray-500">
              <span className="text-green-500 font-semibold">+{destination.growth_percentage}%</span>
              <br />this week
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-semibold text-gray-900">
              {destination.posts_count_7d.toLocaleString()}
            </div>
            <div className="text-xs text-gray-500">posts this week</div>
          </div>
        </div>

        {/* Why Trending */}
        <p className="text-sm text-gray-600 mb-4 line-clamp-2">
          {destination.why_trending}
        </p>

        {/* Featured Content Preview */}
        <div className="flex gap-2 mb-4">
          {destination.featured_content.slice(0, 3).map((content, idx) => (
            <div key={content.id} className="relative flex-1 aspect-square rounded-lg overflow-hidden">
              <img
                src={content.thumbnail_url}
                alt=""
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                <Heart className="w-4 h-4 text-white" />
                <span className="text-white text-xs ml-1">
                  {(content.likes_count / 1000).toFixed(1)}K
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Top Influencers */}
        {destination.top_influencers.length > 0 && (
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-gray-500">Featured by:</span>
            <div className="flex -space-x-2">
              {destination.top_influencers.map((inf) => (
                <img
                  key={inf.id}
                  src={inf.profile_image_url}
                  alt={inf.username}
                  className="w-6 h-6 rounded-full border-2 border-white"
                  title={inf.username}
                />
              ))}
            </div>
          </div>
        )}

        {/* Hashtags */}
        <div className="flex flex-wrap gap-1">
          {destination.related_hashtags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function TrendingHero({ destination }: { destination: TrendingDestination }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative bg-gray-900 rounded-3xl overflow-hidden mb-8"
    >
      <div className="absolute inset-0">
        <img
          src={destination.image_url}
          alt={destination.destination_name}
          className="w-full h-full object-cover opacity-60"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent" />
      </div>

      <div className="relative p-8 md:p-12 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="max-w-xl">
          <div className="flex items-center gap-2 mb-4">
            <div className="bg-yellow-500 text-yellow-900 text-sm font-bold px-3 py-1 rounded-full flex items-center gap-1">
              <Flame className="w-4 h-4" />
              #1 Trending Now
            </div>
            <TrendingBadge reason={destination.trending_reason} />
          </div>

          <h2 className="text-4xl md:text-5xl font-bold text-white mb-2">
            {destination.destination_name}
          </h2>
          <p className="text-xl text-white/80 mb-4 flex items-center gap-2">
            <MapPin className="w-5 h-5" />
            {destination.country}
          </p>

          <p className="text-white/70 mb-6 max-w-lg">
            {destination.why_trending}
          </p>

          <div className="flex items-center gap-6 mb-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                +{destination.growth_percentage}%
              </div>
              <div className="text-white/60 text-sm">Growth</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {destination.posts_count_7d.toLocaleString()}
              </div>
              <div className="text-white/60 text-sm">Posts (7d)</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {(destination.total_engagement_7d / 1000000).toFixed(1)}M
              </div>
              <div className="text-white/60 text-sm">Engagement</div>
            </div>
          </div>

          <div className="flex gap-3">
            <button className="px-6 py-3 bg-white text-gray-900 rounded-full font-semibold hover:bg-gray-100 transition-colors flex items-center gap-2">
              Explore Destination
              <ArrowRight className="w-4 h-4" />
            </button>
            <button className="px-6 py-3 bg-white/10 text-white rounded-full font-semibold hover:bg-white/20 transition-colors backdrop-blur-sm">
              View Content
            </button>
          </div>
        </div>

        {/* Featured Content Grid */}
        <div className="hidden md:grid grid-cols-2 gap-3">
          {destination.featured_content.slice(0, 4).map((content) => (
            <div key={content.id} className="relative w-32 h-32 rounded-xl overflow-hidden group">
              <img
                src={content.thumbnail_url}
                alt=""
                className="w-full h-full object-cover transition-transform group-hover:scale-110"
              />
              <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <Heart className="w-5 h-5 text-white" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// Main Component
export default function TrendingDestinations() {
  const [selectedRegion, setSelectedRegion] = useState("all");
  const [timeRange, setTimeRange] = useState<"today" | "week" | "month">("week");

  const regions = [
    { id: "all", label: "Worldwide" },
    { id: "europe", label: "Europe" },
    { id: "asia", label: "Asia" },
    { id: "americas", label: "Americas" },
    { id: "africa", label: "Africa & Middle East" },
    { id: "oceania", label: "Oceania" },
  ];

  const timeRanges = [
    { id: "today", label: "Today" },
    { id: "week", label: "This Week" },
    { id: "month", label: "This Month" },
  ];

  const [heroDestination, ...gridDestinations] = MOCK_TRENDING;

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-6 h-6 text-blue-600" />
            <h1 className="text-3xl font-bold text-gray-900">Trending Destinations</h1>
          </div>
          <p className="text-gray-600">
            Discover what's hot right now based on social media buzz
          </p>
        </div>

        {/* Time Range Selector */}
        <div className="flex bg-white rounded-full p-1 shadow-sm border border-gray-200">
          {timeRanges.map((range) => (
            <button
              key={range.id}
              onClick={() => setTimeRange(range.id as any)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                timeRange === range.id
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Region Filter */}
      <div className="flex gap-2 overflow-x-auto pb-4 mb-6 scrollbar-hide">
        {regions.map((region) => (
          <button
            key={region.id}
            onClick={() => setSelectedRegion(region.id)}
            className={`px-4 py-2 rounded-full font-medium whitespace-nowrap transition-colors ${
              selectedRegion === region.id
                ? "bg-gray-900 text-white"
                : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50"
            }`}
          >
            {region.label}
          </button>
        ))}
      </div>

      {/* Hero Section - #1 Trending */}
      <TrendingHero destination={heroDestination} />

      {/* Grid Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {gridDestinations.map((destination, idx) => (
          <DestinationCard
            key={destination.id}
            destination={destination}
            rank={idx + 2}
          />
        ))}
      </div>

      {/* Load More */}
      <div className="text-center mt-12">
        <button className="px-8 py-3 bg-white border border-gray-200 rounded-full font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          Load More Destinations
        </button>
      </div>

      {/* How It Works */}
      <div className="mt-16 bg-gray-50 rounded-2xl p-8">
        <h3 className="text-xl font-bold text-gray-900 mb-4">How We Calculate Trends</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            { icon: Camera, label: "Post Volume", desc: "Number of posts about the destination" },
            { icon: Heart, label: "Engagement", desc: "Likes, comments, and shares" },
            { icon: ArrowUpRight, label: "Growth Rate", desc: "Week-over-week increase in mentions" },
            { icon: Users, label: "Influencer Activity", desc: "Content from verified travel creators" },
          ].map((item) => (
            <div key={item.label} className="flex items-start gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <item.icon className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">{item.label}</h4>
                <p className="text-sm text-gray-600">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
