'use client';

import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { api, CityDetails } from '@/services/api';
import CurrencyConverter from '@/components/CurrencyConverter';
import PackingList from '@/components/PackingList';
import TravelAdvisory from '@/components/TravelAdvisory';
import ExpenseTracker from '@/components/ExpenseTracker';
import TripAdvisorPanel from '@/components/TripAdvisorPanel';
import RedditInsights from '@/components/RedditInsights';
import AttractionDetailModal from '@/components/AttractionDetailModal';

export default function CityDetailsClient() {
  const params = useParams();
  const searchParams = useSearchParams();
  const cityName = params.name ? decodeURIComponent(params.name as string) : '';
  
  const [cityData, setCityData] = useState<CityDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedAttraction, setSelectedAttraction] = useState<CityDetails['attractions']['top_attractions'][0] | null>(null);
  
  // Get query params for context (handle null during static generation)
  const origin = searchParams?.get('origin') || '';
  const travelStart = searchParams?.get('travel_start') || '';
  const travelEnd = searchParams?.get('travel_end') || '';
  const budgetLevel = searchParams?.get('budget_level') || 'moderate';
  const passportCountry = searchParams?.get('passport_country') || 'US';
  const hasKids = searchParams?.get('has_kids') === 'true';

  // Calculate trip duration in days
  const travelDays = (() => {
    if (!travelStart || !travelEnd) return 7;
    const diff =
      (new Date(travelEnd).getTime() - new Date(travelStart).getTime()) / 86_400_000;
    return Math.max(1, Math.round(diff));
  })();

  useEffect(() => {
    fetchCityDetails();
  }, [cityName]);

  const fetchCityDetails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await api.getCityDetails(cityName, {
        origin,
        travel_start: travelStart,
        travel_end: travelEnd,
        budget_level: budgetLevel,
        passport_country: passportCountry,
      });
      setCityData(data);
    } catch (err) {
      setError('Failed to load city details. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📍' },
    { id: 'flights', label: 'Flights', icon: '✈️' },
    { id: 'attractions', label: 'Attractions', icon: '🏛️' },
    { id: 'events', label: 'Events', icon: '🎉' },
    { id: 'hotels', label: 'Hotels', icon: '🏨' },
    { id: 'dining', label: 'Dining', icon: '🍽️' },
    { id: 'transport', label: 'Transport', icon: '🚇' },
    { id: 'costs', label: 'Costs & Visa', icon: '💰' },
    { id: 'packing', label: 'Packing', icon: '🎒' },
    { id: 'expenses', label: 'Expenses', icon: '💸' },
    { id: 'community', label: 'Community', icon: '💬' },
  ];

  if (!cityName || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">{cityName ? `Loading ${cityName} details...` : 'Loading...'}</p>
        </div>
      </div>
    );
  }

  if (error || !cityData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || 'City not found'}</p>
          <Link href="/auto-research" className="text-blue-600 hover:underline">
            ← Back to Research
          </Link>
        </div>
      </div>
    );
  }

  const { overview, weather, flights, attractions, events, hotels, restaurants, transport, costs, visa, tips, images } = cityData;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Image Header */}
      <div className="relative h-96">
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${images.hero})` }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/20" />
        </div>
        
        <div className="relative h-full max-w-7xl mx-auto px-4 flex flex-col justify-end pb-8">
          <Link 
            href="/auto-research" 
            className="text-white/80 hover:text-white mb-4 inline-block absolute top-4 left-4 bg-black/30 px-3 py-1 rounded-full backdrop-blur-sm"
          >
            ← Back to Research Results
          </Link>
          <h1 className="text-4xl font-bold mb-2 text-white">{overview.name}</h1>
          <p className="text-xl text-blue-100">{overview.country}</p>
          <p className="mt-4 max-w-2xl text-blue-50">{overview.description}</p>
          
          <div className="mt-6 flex flex-wrap gap-4 text-sm">
            <span className="bg-white/20 px-3 py-1 rounded-full text-white">
              🌡️ {weather.current_temp}°C {weather.condition}
            </span>
            <span className="bg-white/20 px-3 py-1 rounded-full text-white">
              💱 {overview.currency}
            </span>
            <span className="bg-white/20 px-3 py-1 rounded-full text-white">
              🗣️ {overview.language}
            </span>
            <span className="bg-white/20 px-3 py-1 rounded-full text-white">
              🕐 {overview.time_zone}
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="sticky top-0 bg-white shadow-md z-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex overflow-x-auto hide-scrollbar">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-4 border-b-2 whitespace-nowrap font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Weather Card */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">Weather & Climate</h2>
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <div className="flex items-center gap-4 mb-4">
                    <span className="text-5xl">{weather.condition === 'Sunny' ? '☀️' : weather.condition === 'Rainy' ? '🌧️' : '⛅'}</span>
                    <div>
                      <p className="text-3xl font-bold">{weather.current_temp}°C</p>
                      <p className="text-gray-600">{weather.condition}</p>
                    </div>
                  </div>
                  <p className="text-gray-700">{weather.climate_overview}</p>
                </div>
                <div>
                  <h3 className="font-semibold mb-2">3-Day Forecast</h3>
                  <div className="space-y-2">
                    {weather.forecast.map((day, idx) => (
                      <div key={idx} className="flex justify-between items-center bg-gray-50 p-2 rounded">
                        <span className="font-medium">{day.day}</span>
                        <span className="text-gray-600">{day.condition}</span>
                        <span className="font-semibold">{day.temp}°C</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-blue-800"><strong>Best time to visit:</strong> {overview.best_time_to_visit}</p>
              </div>
            </div>

            {/* Photo Gallery */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">📸 Photo Gallery</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {images.gallery.map((img, idx) => (
                  <div key={idx} className="aspect-square rounded-lg overflow-hidden">
                    <img 
                      src={img} 
                      alt={`${overview.name} gallery ${idx + 1}`}
                      className="w-full h-full object-cover hover:scale-110 transition-transform duration-300"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Travel Advisory */}
            <TravelAdvisory countryName={overview.country} />

            {/* Essential Info */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="text-lg font-bold mb-3">Essential Information</h3>
                <ul className="space-y-2 text-gray-700">
                  <li><strong>Language:</strong> {overview.language}</li>
                  <li><strong>Currency:</strong> {overview.currency}</li>
                  <li><strong>Time Zone:</strong> {overview.time_zone}</li>
                  <li><strong>Emergency:</strong> {overview.emergency_number}</li>
                </ul>
              </div>

              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="text-lg font-bold mb-3">Travel Tips</h3>
                <ul className="space-y-2">
                  {tips.slice(0, 4).map((tip, idx) => (
                    <li key={idx} className="flex gap-2 text-gray-700">
                      <span className="text-blue-500">💡</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Flights Tab */}
        {activeTab === 'flights' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">✈️ Flights to {overview.name}</h2>
              
              {flights.from_origin && (
                <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                  <p className="text-lg">
                    <span className="font-semibold">From {flights.from_origin}:</span>{' '}
                    {flights.cheapest_price && (
                      <span className="text-green-600 font-bold">From ${flights.cheapest_price}</span>
                    )}
                    {flights.duration_hours && (
                      <span className="text-gray-600"> • {flights.duration_hours}h flight</span>
                    )}
                  </p>
                </div>
              )}

              {flights.airlines.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold mb-2">Airlines</h3>
                  <div className="flex flex-wrap gap-2">
                    {flights.airlines.map((airline, idx) => (
                      <span key={idx} className="bg-gray-100 px-3 py-1 rounded-full text-sm">
                        {airline}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {flights.flight_options.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">Flight Options</h3>
                  <div className="space-y-3">
                    {flights.flight_options.map((option, idx) => (
                      <div key={idx} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-semibold">{option.airline}</p>
                            <p className="text-sm text-gray-600">
                              {option.departure_time} → {option.arrival_time}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-xl font-bold text-green-600">${option.price}</p>
                            <p className="text-sm text-gray-600">{option.duration_hours}h • {option.stops === 0 ? 'Direct' : `${option.stops} stop${option.stops > 1 ? 's' : ''}`}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Attractions Tab */}
        {activeTab === 'attractions' && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-bold mb-4">Top Attractions ({attractions.total_count})</h2>
            
            <div className="flex flex-wrap gap-2 mb-6">
              {attractions.categories.map((cat, idx) => (
                <span key={idx} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                  {cat}
                </span>
              ))}
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              {attractions.top_attractions.map((attraction, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedAttraction(attraction)}
                  className="border rounded-lg overflow-hidden hover:shadow-lg transition-all text-left group"
                >
                  {images.attractions[attraction.name] && (
                    <div className="h-48 overflow-hidden">
                      <img
                        src={images.attractions[attraction.name]}
                        alt={attraction.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    </div>
                  )}
                  <div className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-lg group-hover:text-blue-600 transition-colors">{attraction.name}</h3>
                      <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm">
                        ⭐ {attraction.rating}
                      </span>
                    </div>
                    <p className="text-gray-600 text-sm mb-2 line-clamp-2">{attraction.description}</p>
                    <div className="flex gap-2 text-sm">
                      <span className="bg-gray-100 px-2 py-1 rounded">{attraction.category}</span>
                      <span className="bg-gray-100 px-2 py-1 rounded">{attraction.price_level}</span>
                    </div>
                    <p className="text-blue-600 text-sm mt-2 font-medium">Click for details →</p>
                  </div>
                </button>
              ))}
            </div>

            {/* Real TripAdvisor attractions */}
            <TripAdvisorPanel cityName={overview.name} type="attractions" />
          </div>
        )}

        {/* Events Tab */}
        {activeTab === 'events' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">🎉 Events & Festivals ({events.total_count})</h2>
              
              {events.upcoming_events.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold mb-3">Upcoming Events</h3>
                  <div className="space-y-3">
                    {events.upcoming_events.map((event, idx) => (
                      <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                        <div className="flex justify-between items-start">
                          <h4 className="font-semibold">{event.name}</h4>
                          <span className="text-sm text-gray-500">{event.date}</span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{event.description}</p>
                        <span className="inline-block mt-2 bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                          {event.type}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {events.festivals.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">Festivals</h3>
                  <div className="space-y-3">
                    {events.festivals.map((festival, idx) => (
                      <div key={idx} className="border-l-4 border-purple-500 pl-4 py-2">
                        <div className="flex justify-between items-start">
                          <h4 className="font-semibold">{festival.name}</h4>
                          <span className="text-sm text-gray-500">{festival.date}</span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{festival.description}</p>
                        <span className="inline-block mt-2 bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded">
                          {festival.type}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Hotels Tab */}
        {activeTab === 'hotels' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">🏨 Hotels & Accommodation</h2>
              
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-700">
                  <strong>Price Range:</strong> ${hotels.price_range.min} - ${hotels.price_range.max} per night
                </p>
              </div>

              {hotels.luxury_options.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold mb-3 text-purple-700">💎 Luxury Options</h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {hotels.luxury_options.map((hotel, idx) => (
                      <div key={idx} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start">
                          <h4 className="font-semibold">{hotel.name}</h4>
                          <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm">
                            ⭐ {hotel.rating}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{hotel.location}</p>
                        <p className="text-lg font-bold text-green-600 mt-2">${hotel.price_per_night}/night</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {hotels.top_rated.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold mb-3 text-blue-700">⭐ Top Rated</h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {hotels.top_rated.map((hotel, idx) => (
                      <div key={idx} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start">
                          <h4 className="font-semibold">{hotel.name}</h4>
                          <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm">
                            ⭐ {hotel.rating}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{hotel.location}</p>
                        <p className="text-lg font-bold text-green-600 mt-2">${hotel.price_per_night}/night</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {hotels.budget_options.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3 text-green-700">💰 Budget Options</h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {hotels.budget_options.map((hotel, idx) => (
                      <div key={idx} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start">
                          <h4 className="font-semibold">{hotel.name}</h4>
                          <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm">
                            ⭐ {hotel.rating}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{hotel.location}</p>
                        <p className="text-lg font-bold text-green-600 mt-2">${hotel.price_per_night}/night</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Real TripAdvisor hotels */}
              <TripAdvisorPanel cityName={overview.name} type="hotels" />
            </div>
          </div>
        )}

        {/* Dining Tab */}
        {activeTab === 'dining' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">🍽️ Dining & Restaurants</h2>
              
              <div className="mb-6 p-4 bg-orange-50 rounded-lg">
                <p className="text-gray-700"><strong>Food Scene:</strong> {restaurants.food_scene}</p>
                <p className="text-gray-600 mt-1"><strong>Price Range:</strong> {restaurants.price_range}</p>
              </div>

              {restaurants.must_try_dishes.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold mb-3">🍜 Must Try Dishes</h3>
                  <div className="flex flex-wrap gap-2">
                    {restaurants.must_try_dishes.map((dish, idx) => (
                      <span key={idx} className="bg-orange-100 text-orange-800 px-3 py-1 rounded-full text-sm">
                        {dish}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {restaurants.top_restaurants.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">Top Restaurants</h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {restaurants.top_restaurants.map((restaurant, idx) => (
                      <div key={idx} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start">
                          <h4 className="font-semibold">{restaurant.name}</h4>
                          <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-sm">
                            ⭐ {restaurant.rating}
                          </span>
                        </div>
                        <p className="text-sm text-orange-600 mt-1">{restaurant.cuisine}</p>
                        <p className="text-sm text-gray-600 mt-1">{restaurant.description}</p>
                        <span className="inline-block mt-2 bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded">
                          {restaurant.price_range}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Real TripAdvisor restaurants */}
              <TripAdvisorPanel cityName={overview.name} type="restaurants" />
            </div>
          </div>
        )}

        {/* Transport Tab */}
        {activeTab === 'transport' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">🚇 Transportation</h2>
              
              {/* From Airport */}
              <div className="mb-6">
                <h3 className="font-semibold mb-3">✈️ From Airport</h3>
                <div className="p-4 bg-blue-50 rounded-lg">
                  <p className="text-gray-700 mb-2"><strong>Recommended:</strong> {transport.from_airport.recommended}</p>
                  <p className="text-gray-600 mb-2"><strong>Cost Range:</strong> {transport.from_airport.cost_range}</p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {transport.from_airport.options.map((option, idx) => (
                      <span key={idx} className="bg-white px-2 py-1 rounded text-sm">
                        {option}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Public Transport */}
              {transport.public_transport.available && (
                <div className="mb-6">
                  <h3 className="font-semibold mb-3">🚌 Public Transport</h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="p-4 bg-green-50 rounded-lg">
                      <p className="text-gray-700"><strong>Types:</strong> {transport.public_transport.types.join(', ')}</p>
                      <p className="text-gray-600 mt-1"><strong>Cost per ride:</strong> {transport.public_transport.cost_per_ride}</p>
                      <p className="text-gray-600"><strong>Day pass:</strong> {transport.public_transport.day_pass}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Taxi/Rideshare */}
              {transport.taxi_rideshare.available && (
                <div className="mb-6">
                  <h3 className="font-semibold mb-3">🚕 Taxi & Rideshare</h3>
                  <div className="p-4 bg-yellow-50 rounded-lg">
                    <p className="text-gray-700"><strong>Base fare:</strong> {transport.taxi_rideshare.base_fare}</p>
                    <p className="text-gray-600 mt-1"><strong>Apps:</strong> {transport.taxi_rideshare.apps.join(', ')}</p>
                  </div>
                </div>
              )}

              {/* Recommended Pass */}
              <div className="p-4 bg-purple-50 rounded-lg">
                <p className="text-purple-800">
                  <strong>💡 Recommended Pass:</strong> {transport.recommended_pass}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Costs & Visa Tab */}
        {activeTab === 'costs' && (
          <div className="space-y-6">
            {/* Daily Costs */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">💰 Daily Costs</h2>
              
              <div className="grid md:grid-cols-3 gap-4 mb-6">
                <div className="p-4 bg-green-50 rounded-lg text-center">
                  <p className="text-sm text-gray-600 mb-1">Budget</p>
                  <p className="text-2xl font-bold text-green-600">${costs.budget_daily}</p>
                  <p className="text-xs text-gray-500">per day</p>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg text-center">
                  <p className="text-sm text-gray-600 mb-1">Moderate</p>
                  <p className="text-2xl font-bold text-blue-600">${costs.moderate_daily}</p>
                  <p className="text-xs text-gray-500">per day</p>
                </div>
                <div className="p-4 bg-purple-50 rounded-lg text-center">
                  <p className="text-sm text-gray-600 mb-1">Luxury</p>
                  <p className="text-2xl font-bold text-purple-600">${costs.luxury_daily}</p>
                  <p className="text-xs text-gray-500">per day</p>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-gray-700"><strong>Average Meal:</strong> ${costs.meal_average}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-gray-700"><strong>Average Transport:</strong> ${costs.transport_average}</p>
                </div>
              </div>

              {/* Currency Converter */}
              <CurrencyConverter
                amountUSD={costs.moderate_daily}
                label="Moderate Daily Budget"
              />
            </div>

            {/* Visa Info */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-4">🛂 Visa Requirements</h2>
              
              <div className={`p-4 rounded-lg mb-4 ${visa.visa_required ? 'bg-yellow-50' : 'bg-green-50'}`}>
                <p className={`font-semibold ${visa.visa_required ? 'text-yellow-800' : 'text-green-800'}`}>
                  {visa.visa_required ? '⚠️ Visa Required' : '✅ Visa Not Required'}
                </p>
              </div>

              {visa.visa_required && (
                <div className="space-y-3">
                  {visa.visa_type && (
                    <div className="flex justify-between border-b pb-2">
                      <span className="text-gray-600">Visa Type</span>
                      <span className="font-medium">{visa.visa_type}</span>
                    </div>
                  )}
                  {visa.duration && (
                    <div className="flex justify-between border-b pb-2">
                      <span className="text-gray-600">Duration</span>
                      <span className="font-medium">{visa.duration}</span>
                    </div>
                  )}
                  {visa.cost && (
                    <div className="flex justify-between border-b pb-2">
                      <span className="text-gray-600">Cost</span>
                      <span className="font-medium">{visa.cost}</span>
                    </div>
                  )}
                  {visa.processing_time && (
                    <div className="flex justify-between border-b pb-2">
                      <span className="text-gray-600">Processing Time</span>
                      <span className="font-medium">{visa.processing_time}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Packing List Tab */}
        {activeTab === 'packing' && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-bold mb-2">🎒 Packing List</h2>
            <p className="text-gray-500 text-sm mb-6">
              Check items off as you pack — progress is saved automatically in your browser.
            </p>
            <PackingList
              tripType={
                weather.current_temp !== null && weather.current_temp > 25
                  ? 'beach'
                  : weather.current_temp !== null && weather.current_temp < 10
                  ? 'winter'
                  : 'city'
              }
              hasKids={hasKids}
              weather={
                weather.current_temp !== null && weather.current_temp < 10 ? 'cold' : 'warm'
              }
              cityName={overview.name}
            />
          </div>
        )}

        {/* Expense Tracker Tab */}
        {activeTab === 'expenses' && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-2xl font-bold mb-2">💸 Expense Tracker</h2>
            <p className="text-gray-500 text-sm mb-6">
              Log your spending and track it against your budget. Data is saved locally.
            </p>
            <ExpenseTracker
              cityName={overview.name}
              dailyBudgetUSD={costs.moderate_daily}
              travelDays={travelDays}
            />
          </div>
        )}

        {/* Community Tab */}
        {activeTab === 'community' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-2xl font-bold mb-1">💬 Traveller Community</h2>
              <p className="text-gray-500 text-sm mb-6">
                Real experiences and tips from fellow travellers on Reddit.
              </p>
              <RedditInsights cityName={overview.name} />
            </div>
          </div>
        )}

      </div>

      {/* Attraction Detail Modal */}
      <AttractionDetailModal
        attraction={selectedAttraction}
        cityName={overview.name}
        isOpen={!!selectedAttraction}
        onClose={() => setSelectedAttraction(null)}
      />
    </div>
  );
}
