'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MapPin, 
  Thermometer, 
  DollarSign, 
  FileText, 
  Star, 
  Calendar,
  Mountain,
  Info,
  X,
  ExternalLink,
  Heart,
  Share2
} from 'lucide-react';
import { Destination } from '@/types/travel';

interface DestinationCardsProps {
  destinations: Destination[];
}

export default function DestinationCards({ destinations }: DestinationCardsProps) {
  const [selectedDestination, setSelectedDestination] = useState<Destination | null>(null);

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {destinations.map((dest, index) => (
          <motion.div
            key={dest.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="bg-white rounded-2xl shadow-lg overflow-hidden card-hover cursor-pointer group"
            onClick={() => setSelectedDestination(dest)}
          >
            {/* Image */}
            <div className="relative h-48 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-primary-400 to-purple-500 group-hover:scale-110 transition-transform duration-500" />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-6xl">🌍</span>
              </div>
              
              {/* Score Badge */}
              <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm rounded-full px-3 py-1 flex items-center gap-1 shadow-lg">
                <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                <span className="font-bold text-gray-900">{dest.overall_score.toFixed(0)}%</span>
              </div>
              
              {/* Rank Badge */}
              {index < 3 && (
                <div className={`absolute top-4 left-4 rounded-full w-8 h-8 flex items-center justify-center font-bold text-white shadow-lg ${
                  index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : 'bg-amber-600'
                }`}>
                  #{index + 1}
                </div>
              )}
            </div>

            {/* Content */}
            <div className="p-6">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">{dest.name}</h3>
                  <p className="text-gray-500 flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {dest.country}
                  </p>
                </div>
              </div>

              {/* AI Recommendation */}
              {dest.recommendation_reason && (
                <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                  {dest.recommendation_reason}
                </p>
              )}

              {/* Quick Stats */}
              <div className="grid grid-cols-3 gap-2 text-sm">
                {dest.weather && (
                  <div className="bg-blue-50 rounded-lg p-2 text-center">
                    <Thermometer className="w-4 h-4 mx-auto mb-1 text-blue-600" />
                    <span className="font-medium text-blue-900">{dest.weather.temperature}°C</span>
                  </div>
                )}
                {dest.affordability && (
                  <div className="bg-green-50 rounded-lg p-2 text-center">
                    <DollarSign className="w-4 h-4 mx-auto mb-1 text-green-600" />
                    <span className="font-medium text-green-900 capitalize">{dest.affordability.cost_level}</span>
                  </div>
                )}
                {dest.visa && (
                  <div className={`rounded-lg p-2 text-center ${dest.visa.required ? 'bg-orange-50' : 'bg-green-50'}`}>
                    <FileText className={`w-4 h-4 mx-auto mb-1 ${dest.visa.required ? 'text-orange-600' : 'text-green-600'}`} />
                    <span className={`font-medium ${dest.visa.required ? 'text-orange-900' : 'text-green-900'}`}>
                      {dest.visa.required ? 'Visa Req' : 'Visa Free'}
                    </span>
                  </div>
                )}
              </div>

              {/* Score Breakdown */}
              <div className="mt-4 pt-4 border-t">
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Match Scores:</span>
                </div>
                <div className="grid grid-cols-5 gap-1 mt-2">
                  <ScoreBar label="Weather" score={dest.weather_score} color="bg-blue-500" />
                  <ScoreBar label="Cost" score={dest.affordability_score} color="bg-green-500" />
                  <ScoreBar label="Visa" score={dest.visa_score} color="bg-purple-500" />
                  <ScoreBar label="Sights" score={dest.attractions_score} color="bg-orange-500" />
                  <ScoreBar label="Events" score={dest.events_score} color="bg-pink-500" />
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedDestination && (
          <DestinationModal 
            destination={selectedDestination} 
            onClose={() => setSelectedDestination(null)} 
          />
        )}
      </AnimatePresence>
    </>
  );
}

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div className="text-center">
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-[10px] text-gray-500 mt-1 block">{label}</span>
    </div>
  );
}

interface DestinationModalProps {
  destination: Destination;
  onClose: () => void;
}

function DestinationModal({ destination, onClose }: DestinationModalProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'attractions' | 'events'>('overview');

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-3xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="relative h-64 bg-gradient-to-br from-primary-500 to-purple-600">
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-8xl">🌍</span>
          </div>
          
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center text-white hover:bg-white/30 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
          
          <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/60 to-transparent">
            <div className="flex items-end justify-between">
              <div>
                <h2 className="text-3xl font-bold text-white">{destination.name}</h2>
                <p className="text-white/80 flex items-center gap-2">
                  <MapPin className="w-5 h-5" />
                  {destination.city}, {destination.country}
                </p>
              </div>
              <div className="flex gap-2">
                <button className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center text-white hover:bg-white/30 transition-colors">
                  <Heart className="w-5 h-5" />
                </button>
                <button className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center text-white hover:bg-white/30 transition-colors">
                  <Share2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          {(['overview', 'attractions', 'events'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-4 text-sm font-medium capitalize transition-colors ${
                activeTab === tab
                  ? 'text-primary-600 border-b-2 border-primary-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-20rem)]">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* AI Reason */}
              {destination.recommendation_reason && (
                <div className="bg-primary-50 rounded-xl p-4">
                  <h4 className="font-semibold text-primary-900 mb-2">Why We Recommend This</h4>
                  <p className="text-primary-800">{destination.recommendation_reason}</p>
                </div>
              )}

              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {destination.weather && (
                  <div className="bg-gray-50 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-500 mb-2">
                      <Thermometer className="w-5 h-5" />
                      <span className="text-sm">Weather</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{destination.weather.temperature}°C</p>
                    <p className="text-sm text-gray-600">{destination.weather.condition}</p>
                    {destination.weather.recommendation && (
                      <p className="text-xs text-gray-500 mt-2">{destination.weather.recommendation}</p>
                    )}
                  </div>
                )}
                
                {destination.affordability && (
                  <div className="bg-gray-50 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-500 mb-2">
                      <DollarSign className="w-5 h-5" />
                      <span className="text-sm">Daily Cost</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">${destination.affordability.daily_cost_estimate}</p>
                    <p className="text-sm text-gray-600 capitalize">{destination.affordability.cost_level}</p>
                  </div>
                )}
                
                {destination.visa && (
                  <div className="bg-gray-50 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-gray-500 mb-2">
                      <FileText className="w-5 h-5" />
                      <span className="text-sm">Visa</span>
                    </div>
                    <p className="text-lg font-bold text-gray-900">
                      {destination.visa.required ? 'Required' : 'Not Required'}
                    </p>
                    {destination.visa.evisa_available && (
                      <p className="text-sm text-green-600">eVisa available</p>
                    )}
                    {destination.visa.visa_free_days && (
                      <p className="text-sm text-gray-600">{destination.visa.visa_free_days} days visa-free</p>
                    )}
                  </div>
                )}
                
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-gray-500 mb-2">
                    <Star className="w-5 h-5" />
                    <span className="text-sm">Match Score</span>
                  </div>
                  <p className="text-2xl font-bold text-primary-600">{destination.overall_score.toFixed(0)}%</p>
                  <p className="text-sm text-gray-600">Overall match</p>
                </div>
              </div>

              {/* Cost Breakdown */}
              {destination.affordability && (
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3">Cost Breakdown</h4>
                  <div className="space-y-2">
                    <CostBar label="Accommodation" amount={destination.affordability.accommodation_avg} total={destination.affordability.daily_cost_estimate} color="bg-blue-500" />
                    <CostBar label="Food & Dining" amount={destination.affordability.food_avg} total={destination.affordability.daily_cost_estimate} color="bg-green-500" />
                    <CostBar label="Transportation" amount={destination.affordability.transport_avg} total={destination.affordability.daily_cost_estimate} color="bg-purple-500" />
                    <CostBar label="Activities" amount={destination.affordability.activities_avg} total={destination.affordability.daily_cost_estimate} color="bg-orange-500" />
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'attractions' && (
            <div className="space-y-4">
              {destination.attractions.length > 0 ? (
                destination.attractions.map((attraction) => (
                  <div key={attraction.id} className="flex gap-4 p-4 bg-gray-50 rounded-xl">
                    <div className="w-16 h-16 bg-gradient-to-br from-gray-200 to-gray-300 rounded-lg flex items-center justify-center text-2xl flex-shrink-0">
                      {attraction.natural_feature ? '🏔️' : '🏛️'}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <h4 className="font-semibold text-gray-900">{attraction.name}</h4>
                        <div className="flex items-center gap-1 text-yellow-500">
                          <Star className="w-4 h-4 fill-current" />
                          <span className="text-sm font-medium">{attraction.rating}</span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{attraction.description}</p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                        <span className="capitalize">{attraction.type.replace(/_/g, ' ')}</span>
                        {attraction.entry_fee !== undefined && (
                          <span>{attraction.entry_fee === 0 ? 'Free' : `$${attraction.entry_fee}`}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Mountain className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No attractions data available</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'events' && (
            <div className="space-y-4">
              {destination.events.length > 0 ? (
                destination.events.map((event) => (
                  <div key={event.id} className="flex gap-4 p-4 bg-gray-50 rounded-xl">
                    <div className="w-16 h-16 bg-gradient-to-br from-purple-200 to-pink-200 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Calendar className="w-8 h-8 text-purple-600" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900">{event.name}</h4>
                      <p className="text-sm text-primary-600 mt-1">
                        {new Date(event.date).toLocaleDateString('en-US', {
                          weekday: 'long',
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">{event.venue}</p>
                      {event.price_range && (
                        <p className="text-xs text-gray-500 mt-1">{event.price_range}</p>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Calendar className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No events during your travel dates</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t bg-gray-50 flex gap-3">
          <button className="flex-1 py-3 px-6 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 transition-colors flex items-center justify-center gap-2">
            Plan This Trip
            <ExternalLink className="w-4 h-4" />
          </button>
          <button className="py-3 px-6 border border-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-100 transition-colors">
            Save for Later
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function CostBar({ label, amount, total, color }: { label: string; amount: number; total: number; color: string }) {
  const percentage = (amount / total) * 100;
  
  return (
    <div className="flex items-center gap-4">
      <span className="w-28 text-sm text-gray-600">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${percentage}%` }} />
      </div>
      <span className="w-16 text-sm font-medium text-gray-900 text-right">${amount.toFixed(0)}</span>
    </div>
  );
}