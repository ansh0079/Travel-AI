"use client";

import { useState } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lightbulb,
  Bookmark,
  Share2,
  ChevronLeft,
  MapPin,
  Calendar,
  DollarSign,
  Plus,
} from "lucide-react";

// Types
interface InspirationItem {
  id: string;
  type: "photo" | "reel" | "guide" | "collection";
  title: string;
  description: string;
  image_url: string;
  destination: {
    name: string;
    country: string;
  };
  influencer?: {
    id: string;
    username: string;
    display_name: string;
    profile_image_url: string;
  };
  tags: string[];
  likes_count: number;
  is_saved: boolean;
  best_time_to_visit?: string;
  budget_estimate?: string;
  duration_days?: number;
}

interface TripInspirationProps {
  onAddToTrip?: (item: InspirationItem) => void;
  onSaveForLater?: (item: InspirationItem) => void;
}

// Mock Data
const MOCK_INSPIRATION: InspirationItem[] = [
  {
    id: "1",
    type: "guide",
    title: "48 Hours in Kyoto: A Complete Itinerary",
    description: "From Fushimi Inari at sunrise to Gion at dusk, experience the best of Japan's cultural capital in just two days.",
    image_url: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800",
    destination: { name: "Kyoto", country: "Japan" },
    influencer: {
      id: "1",
      username: "japan_journey",
      display_name: "Yuki Tanaka",
      profile_image_url: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200",
    },
    tags: ["culture", "food", "temples", "photography"],
    likes_count: 45200,
    is_saved: false,
    best_time_to_visit: "March-May, October-November",
    budget_estimate: "$150-200/day",
    duration_days: 2,
  },
  {
    id: "2",
    type: "photo",
    title: "Hidden Beach Paradise",
    description: "This secluded beach in the Philippines has the whitest sand I've ever seen. No crowds, just pure paradise.",
    image_url: "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800",
    destination: { name: "El Nido", country: "Philippines" },
    influencer: {
      id: "2",
      username: "island_hopper",
      display_name: "Maria Santos",
      profile_image_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200",
    },
    tags: ["beach", "island", "hidden gem", "relaxation"],
    likes_count: 89300,
    is_saved: true,
    best_time_to_visit: "November-May",
    budget_estimate: "$80-120/day",
  },
  {
    id: "3",
    type: "collection",
    title: "Best Street Food in Southeast Asia",
    description: "A curated collection of must-try street food experiences across Thailand, Vietnam, Malaysia, and Singapore.",
    image_url: "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
    destination: { name: "Multiple", country: "Southeast Asia" },
    influencer: {
      id: "3",
      username: "foodie_adventures",
      display_name: "David Lee",
      profile_image_url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200",
    },
    tags: ["food", "street food", "local experience", "budget"],
    likes_count: 67300,
    is_saved: false,
    budget_estimate: "$30-50/day for food",
    duration_days: 14,
  },
  {
    id: "4",
    type: "reel",
    title: "Northern Lights in Iceland",
    description: "The moment the aurora danced across the sky in Iceland. Bucket list checked! ✨",
    image_url: "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=800",
    destination: { name: "Reykjavik", country: "Iceland" },
    influencer: {
      id: "4",
      username: "nordic_adventures",
      display_name: "Emma Wilson",
      profile_image_url: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200",
    },
    tags: ["nature", "northern lights", "winter", "adventure"],
    likes_count: 124500,
    is_saved: false,
    best_time_to_visit: "September-March",
    budget_estimate: "$200-300/day",
  },
];

// Components
function InspirationCard({
  item,
  onAdd,
  onSave,
  onClick,
}: {
  item: InspirationItem;
  onAdd: () => void;
  onSave: () => void;
  onClick: () => void;
}) {
  const [isHovered, setIsHovered] = useState(false);

  const typeLabels = {
    photo: "Photo",
    reel: "Reel",
    guide: "Travel Guide",
    collection: "Collection",
  };

  const typeColors = {
    photo: "bg-pink-500",
    reel: "bg-purple-500",
    guide: "bg-blue-500",
    collection: "bg-green-500",
  };

  return (
    <motion.div
      layout
      whileHover={{ scale: 1.02 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      className="bg-white rounded-2xl shadow-lg overflow-hidden cursor-pointer group"
      onClick={onClick}
    >
      {/* Image */}
      <div className="relative h-56 overflow-hidden">
        <img
          src={item.image_url}
          alt={item.title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

        {/* Type Badge */}
        <div className={`absolute top-3 left-3 ${typeColors[item.type]} text-white text-xs font-bold px-2 py-1 rounded-full`}>
          {typeLabels[item.type]}
        </div>

        {/* Quick Actions */}
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="absolute top-3 right-3 flex gap-2"
            >
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSave();
                }}
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                  item.is_saved ? "bg-yellow-500 text-white" : "bg-white/90 text-gray-700 hover:bg-white"
                }`}
              >
                <Bookmark className={`w-4 h-4 ${item.is_saved ? "fill-current" : ""}`} />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAdd();
                }}
                className="w-9 h-9 bg-blue-600 text-white rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Destination Overlay */}
        <div className="absolute bottom-3 left-3 text-white">
          <div className="flex items-center gap-1 text-sm">
            <MapPin className="w-3 h-3" />
            {item.destination.name}, {item.destination.country}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-bold text-gray-900 mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
          {item.title}
        </h3>
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">{item.description}</p>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-3">
          {item.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
              {tag}
            </span>
          ))}
        </div>

        {/* Meta Info */}
        {(item.best_time_to_visit || item.budget_estimate || item.duration_days) && (
          <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-3">
            {item.duration_days && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {item.duration_days} days
              </span>
            )}
            {item.budget_estimate && (
              <span className="flex items-center gap-1">
                <DollarSign className="w-3 h-3" />
                {item.budget_estimate}
              </span>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <div className="flex items-center gap-2">
            <img
              src={item.influencer?.profile_image_url}
              alt={item.influencer?.display_name}
              className="w-6 h-6 rounded-full object-cover"
            />
            <span className="text-sm text-gray-600">{item.influencer?.display_name}</span>
          </div>
          <div className="flex items-center gap-1 text-sm text-gray-500">
            <Heart className="w-4 h-4" />
            {(item.likes_count / 1000).toFixed(1)}K
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function InspirationModal({
  item,
  onClose,
  onAdd,
  onSave,
}: {
  item: InspirationItem;
  onClose: () => void;
  onAdd: () => void;
  onSave: () => void;
}) {
  if (!item) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col md:flex-row"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Image Section */}
        <div className="relative w-full md:w-1/2 h-64 md:h-auto">
          <Image
            src={item.image_url}
            alt={item.title}
            fill
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent md:hidden" />
          <button
            onClick={onClose}
            className="absolute top-4 left-4 w-10 h-10 bg-white/90 rounded-full flex items-center justify-center text-gray-700 hover:bg-white transition-colors"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
        </div>

        {/* Content Section */}
        <div className="flex-1 p-6 md:p-8 overflow-y-auto">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-full uppercase">
                  {item.type}
                </span>
                <span className="text-sm text-gray-500 flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {item.destination.name}, {item.destination.country}
                </span>
              </div>
              <h2 className="text-2xl font-bold text-gray-900">{item.title}</h2>
            </div>
          </div>

          {/* Influencer */}
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl mb-6">
            <Image
              src={item.influencer?.profile_image_url || ""}
              alt={item.influencer?.display_name || ""}
              width={48}
              height={48}
              className="w-12 h-12 rounded-full object-cover"
            />
            <div className="flex-1">
              <div className="font-semibold text-gray-900">{item.influencer?.display_name}</div>
              <div className="text-sm text-gray-500">@{item.influencer?.username}</div>
            </div>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-full text-sm font-medium hover:bg-blue-700 transition-colors">
              Follow
            </button>
          </div>

          {/* Description */}
          <p className="text-gray-700 mb-6 leading-relaxed">{item.description}</p>

          {/* Details */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {item.best_time_to_visit && (
              <div className="p-3 bg-gray-50 rounded-xl">
                <div className="text-sm text-gray-500 mb-1">Best Time to Visit</div>
                <div className="font-semibold text-gray-900">{item.best_time_to_visit}</div>
              </div>
            )}
            {item.budget_estimate && (
              <div className="p-3 bg-gray-50 rounded-xl">
                <div className="text-sm text-gray-500 mb-1">Budget Estimate</div>
                <div className="font-semibold text-gray-900">{item.budget_estimate}</div>
              </div>
            )}
            {item.duration_days && (
              <div className="p-3 bg-gray-50 rounded-xl">
                <div className="text-sm text-gray-500 mb-1">Recommended Duration</div>
                <div className="font-semibold text-gray-900">{item.duration_days} days</div>
              </div>
            )}
          </div>

          {/* Tags */}
          <div className="mb-6">
            <div className="text-sm font-semibold text-gray-900 mb-2">Tags</div>
            <div className="flex flex-wrap gap-2">
              {item.tags.map((tag) => (
                <span key={tag} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                  #{tag}
                </span>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onAdd}
              className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Add to My Trip
            </button>
            <button
              onClick={onSave}
              className={`px-4 py-3 rounded-xl font-medium transition-colors flex items-center gap-2 ${
                item.is_saved
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              <Bookmark className={`w-5 h-5 ${item.is_saved ? "fill-current" : ""}`} />
              {item.is_saved ? "Saved" : "Save"}
            </button>
            <button className="px-4 py-3 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors">
              <Share2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

// Main Component
export default function TripInspiration({ onAddToTrip, onSaveForLater }: TripInspirationProps) {
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedItem, setSelectedItem] = useState<InspirationItem | null>(null);
  const [items, setItems] = useState(MOCK_INSPIRATION);
  const [viewMode, setViewMode] = useState<"grid" | "masonry">("grid");

  const categories = [
    { id: "all", label: "All Inspiration" },
    { id: "guides", label: "Travel Guides" },
    { id: "photos", label: "Photos" },
    { id: "reels", label: "Reels" },
    { id: "collections", label: "Collections" },
    { id: "saved", label: "Saved" },
  ];

  const filteredItems = items.filter((item) => {
    if (selectedCategory === "all") return true;
    if (selectedCategory === "saved") return item.is_saved;
    if (selectedCategory === "guides") return item.type === "guide";
    if (selectedCategory === "photos") return item.type === "photo";
    if (selectedCategory === "reels") return item.type === "reel";
    if (selectedCategory === "collections") return item.type === "collection";
    return true;
  });

  const handleSave = (itemId: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === itemId ? { ...item, is_saved: !item.is_saved } : item
      )
    );
  };

  const handleAdd = (item: InspirationItem) => {
    onAddToTrip?.(item);
    setSelectedItem(null);
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Lightbulb className="w-6 h-6 text-yellow-500" />
          <h1 className="text-3xl font-bold text-gray-900">Trip Inspiration</h1>
        </div>
        <p className="text-gray-600">
          Discover ideas from top travel creators and build your dream trip
        </p>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        {/* Category Pills */}
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-full font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat.id
                  ? "bg-gray-900 text-white"
                  : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-50"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">View:</span>
          <button
            onClick={() => setViewMode("grid")}
            className={`p-2 rounded-lg transition-colors ${
              viewMode === "grid" ? "bg-gray-200 text-gray-900" : "text-gray-400 hover:text-gray-600"
            }`}
          >
            <div className="w-4 h-4 grid grid-cols-2 gap-0.5">
              <div className="bg-current rounded-sm" />
              <div className="bg-current rounded-sm" />
              <div className="bg-current rounded-sm" />
              <div className="bg-current rounded-sm" />
            </div>
          </button>
          <button
            onClick={() => setViewMode("masonry")}
            className={`p-2 rounded-lg transition-colors ${
              viewMode === "masonry" ? "bg-gray-200 text-gray-900" : "text-gray-400 hover:text-gray-600"
            }`}
          >
            <div className="w-4 h-4 flex flex-col gap-0.5">
              <div className="bg-current rounded-sm h-2" />
              <div className="bg-current rounded-sm h-1.5" />
              <div className="bg-current rounded-sm h-2" />
            </div>
          </button>
        </div>
      </div>

      {/* Inspiration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredItems.map((item) => (
          <InspirationCard
            key={item.id}
            item={item}
            onAdd={() => handleAdd(item)}
            onSave={() => handleSave(item.id)}
            onClick={() => setSelectedItem(item)}
          />
        ))}
      </div>

      {/* Empty State */}
      {filteredItems.length === 0 && (
        <div className="text-center py-16">
          <Lightbulb className="w-16 h-16 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No inspiration found</h3>
          <p className="text-gray-500">Try selecting a different category</p>
        </div>
      )}

      {/* Load More */}
      <div className="text-center mt-12">
        <button className="px-8 py-3 bg-white border border-gray-200 rounded-full font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          Load More Inspiration
        </button>
      </div>

      {/* Modal */}
      <AnimatePresence>
        {selectedItem && (
          <InspirationModal
            item={selectedItem}
            onClose={() => setSelectedItem(null)}
            onAdd={() => handleAdd(selectedItem)}
            onSave={() => handleSave(selectedItem.id)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
