'use client';

import { useState, useEffect } from 'react';
import { api, TripAdvisorAttraction, TripAdvisorHotel, TripAdvisorRestaurant } from '@/services/api';

interface TripAdvisorPanelProps {
  cityName: string;
  type: 'attractions' | 'hotels' | 'restaurants';
}

function StarRating({ rating }: { rating: number }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return (
    <span className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <svg
          key={i}
          className={`w-3.5 h-3.5 ${i < full ? 'text-yellow-400' : i === full && half ? 'text-yellow-300' : 'text-gray-200'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
      <span className="ml-1 text-xs text-gray-500">{rating.toFixed(1)}</span>
    </span>
  );
}

function AttractionCard({ item }: { item: TripAdvisorAttraction }) {
  return (
    <a
      href={item.web_url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow group"
    >
      {item.photo_url ? (
        <div className="h-40 overflow-hidden bg-gray-100">
          <img
            src={item.photo_url}
            alt={item.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        </div>
      ) : (
        <div className="h-40 bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
          <span className="text-4xl">🏛️</span>
        </div>
      )}
      <div className="p-3 flex flex-col gap-1 flex-1">
        <h4 className="font-semibold text-gray-900 text-sm leading-tight group-hover:text-blue-600 transition-colors line-clamp-2">
          {item.name}
        </h4>
        <StarRating rating={item.rating} />
        <p className="text-xs text-gray-400">{item.num_reviews.toLocaleString()} reviews</p>
        {item.ranking_string && (
          <p className="text-xs text-green-600 font-medium line-clamp-1">{item.ranking_string}</p>
        )}
        {item.address && (
          <p className="text-xs text-gray-400 mt-auto line-clamp-1">📍 {item.address}</p>
        )}
      </div>
    </a>
  );
}

function HotelCard({ item }: { item: TripAdvisorHotel }) {
  return (
    <a
      href={item.web_url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow group"
    >
      {item.photo_url ? (
        <div className="h-40 overflow-hidden bg-gray-100">
          <img
            src={item.photo_url}
            alt={item.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        </div>
      ) : (
        <div className="h-40 bg-gradient-to-br from-purple-50 to-pink-100 flex items-center justify-center">
          <span className="text-4xl">🏨</span>
        </div>
      )}
      <div className="p-3 flex flex-col gap-1 flex-1">
        <h4 className="font-semibold text-gray-900 text-sm leading-tight group-hover:text-purple-600 transition-colors line-clamp-2">
          {item.name}
        </h4>
        <div className="flex items-center gap-2">
          <StarRating rating={item.rating} />
          {item.hotel_class && (
            <span className="text-xs text-yellow-600">{'★'.repeat(Math.round(parseFloat(item.hotel_class) || 0))}</span>
          )}
        </div>
        <p className="text-xs text-gray-400">{item.num_reviews.toLocaleString()} reviews</p>
        {item.price_level && (
          <p className="text-xs text-gray-500">{item.price_level}</p>
        )}
        {item.amenities.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {item.amenities.slice(0, 3).map((a, i) => (
              <span key={i} className="text-xs bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded">
                {a}
              </span>
            ))}
          </div>
        )}
        {item.address && (
          <p className="text-xs text-gray-400 mt-auto line-clamp-1">📍 {item.address}</p>
        )}
      </div>
    </a>
  );
}

function RestaurantCard({ item }: { item: TripAdvisorRestaurant }) {
  return (
    <a
      href={item.web_url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow group"
    >
      {item.photo_url ? (
        <div className="h-40 overflow-hidden bg-gray-100">
          <img
            src={item.photo_url}
            alt={item.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        </div>
      ) : (
        <div className="h-40 bg-gradient-to-br from-orange-50 to-red-100 flex items-center justify-center">
          <span className="text-4xl">🍽️</span>
        </div>
      )}
      <div className="p-3 flex flex-col gap-1 flex-1">
        <h4 className="font-semibold text-gray-900 text-sm leading-tight group-hover:text-orange-600 transition-colors line-clamp-2">
          {item.name}
        </h4>
        <StarRating rating={item.rating} />
        <p className="text-xs text-gray-400">{item.num_reviews.toLocaleString()} reviews</p>
        {item.cuisine.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {item.cuisine.map((c, i) => (
              <span key={i} className="text-xs bg-orange-50 text-orange-700 px-1.5 py-0.5 rounded">
                {c}
              </span>
            ))}
          </div>
        )}
        {item.price_level && (
          <p className="text-xs text-gray-500">{item.price_level}</p>
        )}
        {item.address && (
          <p className="text-xs text-gray-400 mt-auto line-clamp-1">📍 {item.address}</p>
        )}
      </div>
    </a>
  );
}

export default function TripAdvisorPanel({ cityName, type }: TripAdvisorPanelProps) {
  const [attractions, setAttractions] = useState<TripAdvisorAttraction[]>([]);
  const [hotels, setHotels] = useState<TripAdvisorHotel[]>([]);
  const [restaurants, setRestaurants] = useState<TripAdvisorRestaurant[]>([]);
  const [loading, setLoading] = useState(true);
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    if (!cityName) return;
    setLoading(true);

    const fetchData = async () => {
      try {
        if (type === 'attractions') {
          const result = await api.getTripAdvisorAttractions(cityName);
          setEnabled(result.enabled);
          setAttractions(result.attractions || []);
        } else if (type === 'hotels') {
          const result = await api.getTripAdvisorHotels(cityName);
          setEnabled(result.enabled);
          setHotels(result.hotels || []);
        } else {
          const result = await api.getTripAdvisorRestaurants(cityName);
          setEnabled(result.enabled);
          setRestaurants(result.restaurants || []);
        }
      } catch {
        // silently fail — backend will return gracefully if API key missing
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [cityName, type]);

  // If TripAdvisor API not configured, don't render anything
  if (!enabled) return null;

  const items =
    type === 'attractions' ? attractions : type === 'hotels' ? hotels : restaurants;

  if (!loading && items.length === 0) return null;

  const titles: Record<string, string> = {
    attractions: 'Top Attractions on TripAdvisor',
    hotels: 'Hotels on TripAdvisor',
    restaurants: 'Restaurants on TripAdvisor',
  };

  return (
    <div className="mt-8">
      <div className="flex items-center gap-2 mb-4">
        <img
          src="https://static.tacdn.com/img2/brand_refresh/Tripadvisor_lockup_horizontal_secondary_registered.svg"
          alt="TripAdvisor"
          className="h-5"
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
        <h3 className="font-bold text-gray-800">{titles[type]}</h3>
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Live data</span>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-64 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {type === 'attractions' &&
            attractions.map((item) => <AttractionCard key={item.location_id} item={item} />)}
          {type === 'hotels' &&
            hotels.map((item) => <HotelCard key={item.location_id} item={item} />)}
          {type === 'restaurants' &&
            restaurants.map((item) => <RestaurantCard key={item.location_id} item={item} />)}
        </div>
      )}
    </div>
  );
}
