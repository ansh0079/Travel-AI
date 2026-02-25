'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { MapPin, Calendar, Users, Wallet, Heart, Umbrella } from 'lucide-react';
import { TravelRequest, Interest, TravelStyle } from '@/types/travel';

interface TravelSearchFormProps {
  onSubmit: (data: TravelRequest) => void;
  isLoading?: boolean;
}

const INTERESTS: { value: Interest; label: string; icon: string }[] = [
  { value: 'nature', label: 'Nature', icon: '🌿' },
  { value: 'culture', label: 'Culture', icon: '🏛️' },
  { value: 'adventure', label: 'Adventure', icon: '🧗' },
  { value: 'relaxation', label: 'Relaxation', icon: '🧘' },
  { value: 'food', label: 'Food', icon: '🍜' },
  { value: 'beaches', label: 'Beaches', icon: '🏖️' },
  { value: 'mountains', label: 'Mountains', icon: '⛰️' },
  { value: 'history', label: 'History', icon: '📜' },
  { value: 'art', label: 'Art', icon: '🎨' },
  { value: 'wildlife', label: 'Wildlife', icon: '🦁' },
  { value: 'nightlife', label: 'Nightlife', icon: '🌃' },
  { value: 'shopping', label: 'Shopping', icon: '🛍️' },
];

const TRAVEL_STYLES: { value: TravelStyle; label: string; description: string }[] = [
  { value: 'budget', label: 'Budget', description: 'Backpacker style, hostels, street food' },
  { value: 'moderate', label: 'Moderate', description: 'Mid-range hotels, mix of dining' },
  { value: 'comfort', label: 'Comfort', description: 'Nice hotels, good restaurants' },
  { value: 'luxury', label: 'Luxury', description: '5-star hotels, fine dining' },
];

export default function TravelSearchForm({ onSubmit, isLoading }: TravelSearchFormProps) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<Partial<TravelRequest>>({
    origin: '',
    travel_start: '',
    travel_end: '',
    num_travelers: 1,
    num_recommendations: 5,
    user_preferences: {
      budget_daily: 150,
      budget_total: 3000,
      travel_style: 'moderate',
      interests: [],
      passport_country: 'US',
      visa_preference: 'visa_free',
      traveling_with: 'solo',
      accessibility_needs: [],
      dietary_restrictions: [],
    },
  });

  const handleInterestToggle = (interest: Interest) => {
    const current = formData.user_preferences?.interests || [];
    const updated = current.includes(interest)
      ? current.filter((i) => i !== interest)
      : [...current, interest];
    
    setFormData({
      ...formData,
      user_preferences: {
        ...formData.user_preferences!,
        interests: updated,
      },
    });
  };

  const handleSubmit = () => {
    if (formData.origin && formData.travel_start && formData.travel_end) {
      onSubmit(formData as TravelRequest);
    }
  };

  const totalSteps = 4;

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="flex items-center gap-2 mb-8">
        {Array.from({ length: totalSteps }).map((_, i) => (
          <div key={i} className="flex-1 flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                step > i + 1
                  ? 'bg-green-500 text-white'
                  : step === i + 1
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-500'
              }`}
            >
              {step > i + 1 ? '✓' : i + 1}
            </div>
            {i < totalSteps - 1 && (
              <div
                className={`flex-1 h-1 rounded transition-colors ${
                  step > i + 1 ? 'bg-green-500' : 'bg-gray-200'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Basic Info */}
      {step === 1 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="space-y-6"
        >
          <h3 className="text-2xl font-bold text-gray-900">Where are you traveling from?</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <MapPin className="w-4 h-4 inline mr-1" />
                Origin City
              </label>
              <input
                type="text"
                value={formData.origin}
                onChange={(e) => setFormData({ ...formData, origin: e.target.value })}
                placeholder="e.g., New York, London, Tokyo"
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Users className="w-4 h-4 inline mr-1" />
                Travelers
              </label>
              <select
                value={formData.num_travelers}
                onChange={(e) => setFormData({ ...formData, num_travelers: parseInt(e.target.value) })}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              >
                {[1, 2, 3, 4, 5, 6].map((n) => (
                  <option key={n} value={n}>
                    {n} {n === 1 ? 'person' : 'people'}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Calendar className="w-4 h-4 inline mr-1" />
                Start Date
              </label>
              <input
                type="date"
                value={formData.travel_start}
                onChange={(e) => setFormData({ ...formData, travel_start: e.target.value })}
                min={new Date().toISOString().split('T')[0]}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Calendar className="w-4 h-4 inline mr-1" />
                End Date
              </label>
              <input
                type="date"
                value={formData.travel_end}
                onChange={(e) => setFormData({ ...formData, travel_end: e.target.value })}
                min={formData.travel_start || new Date().toISOString().split('T')[0]}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Step 2: Budget */}
      {step === 2 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="space-y-6"
        >
          <h3 className="text-2xl font-bold text-gray-900">What's your budget?</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {TRAVEL_STYLES.map((style) => (
              <button
                key={style.value}
                onClick={() =>
                  setFormData({
                    ...formData,
                    user_preferences: {
                      ...formData.user_preferences!,
                      travel_style: style.value,
                    },
                  })
                }
                className={`p-4 rounded-xl border-2 text-left transition-all ${
                  formData.user_preferences?.travel_style === style.value
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-primary-200'
                }`}
              >
                <div className="font-semibold text-gray-900">{style.label}</div>
                <div className="text-xs text-gray-500 mt-1">{style.description}</div>
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Wallet className="w-4 h-4 inline mr-1" />
                Daily Budget (USD)
              </label>
              <input
                type="number"
                value={formData.user_preferences?.budget_daily}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    user_preferences: {
                      ...formData.user_preferences!,
                      budget_daily: parseInt(e.target.value) || 0,
                    },
                  })
                }
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Total Budget (USD)
              </label>
              <input
                type="number"
                value={formData.user_preferences?.budget_total}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    user_preferences: {
                      ...formData.user_preferences!,
                      budget_total: parseInt(e.target.value) || 0,
                    },
                  })
                }
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Step 3: Interests */}
      {step === 3 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="space-y-6"
        >
          <h3 className="text-2xl font-bold text-gray-900">What are you interested in?</h3>
          <p className="text-gray-600">Select all that apply</p>
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {INTERESTS.map((interest) => (
              <button
                key={interest.value}
                onClick={() => handleInterestToggle(interest.value)}
                className={`p-3 rounded-xl border-2 text-left transition-all flex items-center gap-3 ${
                  formData.user_preferences?.interests?.includes(interest.value)
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-primary-200'
                }`}
              >
                <span className="text-2xl">{interest.icon}</span>
                <span className="font-medium text-gray-700">{interest.label}</span>
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Step 4: Preferences */}
      {step === 4 && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="space-y-6"
        >
          <h3 className="text-2xl font-bold text-gray-900">Final details</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Heart className="w-4 h-4 inline mr-1" />
                Preferred Weather
              </label>
              <select
                value={formData.user_preferences?.preferred_weather || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    user_preferences: {
                      ...formData.user_preferences!,
                      preferred_weather: e.target.value || undefined,
                    },
                  })
                }
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              >
                <option value="">No preference</option>
                <option value="hot">Hot (30°C+)</option>
                <option value="warm">Warm (20-30°C)</option>
                <option value="mild">Mild (10-20°C)</option>
                <option value="cold">Cold (0-10°C)</option>
                <option value="snowy">Snowy (Below 0°C)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Umbrella className="w-4 h-4 inline mr-1" />
                Passport Country
              </label>
              <select
                value={formData.user_preferences?.passport_country}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    user_preferences: {
                      ...formData.user_preferences!,
                      passport_country: e.target.value,
                    },
                  })
                }
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              >
                <option value="US">United States</option>
                <option value="GB">United Kingdom</option>
                <option value="CA">Canada</option>
                <option value="AU">Australia</option>
                <option value="DE">Germany</option>
                <option value="FR">France</option>
                <option value="JP">Japan</option>
                <option value="CN">China</option>
                <option value="IN">India</option>
                <option value="BR">Brazil</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Recommendations
            </label>
            <input
              type="range"
              min="3"
              max="10"
              value={formData.num_recommendations}
              onChange={(e) =>
                setFormData({ ...formData, num_recommendations: parseInt(e.target.value) })
              }
              className="w-full"
            />
            <div className="text-center text-sm text-gray-600 mt-2">
              {formData.num_recommendations} destinations
            </div>
          </div>
        </motion.div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-6 border-t">
        <button
          onClick={() => setStep(Math.max(1, step - 1))}
          disabled={step === 1}
          className="px-6 py-3 rounded-xl border border-gray-200 text-gray-600 font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Previous
        </button>
        
        {step < totalSteps ? (
          <button
            onClick={() => setStep(step + 1)}
            className="px-6 py-3 rounded-xl bg-primary-600 text-white font-medium hover:bg-primary-700 transition-colors"
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="px-8 py-3 rounded-xl bg-gradient-to-r from-primary-600 to-purple-600 text-white font-medium hover:from-primary-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                />
                Finding Destinations...
              </>
            ) : (
              <>Find My Perfect Trip ✨</>
            )}
          </button>
        )}
      </div>
    </div>
  );
}