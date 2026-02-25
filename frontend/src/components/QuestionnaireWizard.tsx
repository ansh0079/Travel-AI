'use client';

import { useState, useCallback } from 'react';
import { TravelPreferences } from '@/services/api';

interface QuestionnaireWizardProps {
  onComplete: (preferences: TravelPreferences) => void;
  onCancel?: () => void;
}

type Step = 
  | 'welcome'
  | 'origin-dates'
  | 'budget-style'
  | 'interests'
  | 'preferences'
  | 'review';

const STEPS: Step[] = ['welcome', 'origin-dates', 'budget-style', 'interests', 'preferences', 'review'];

const INTERESTS_OPTIONS = [
  { id: 'beach', icon: '🏖️', label: 'Beaches', description: 'Sun, sand, and ocean' },
  { id: 'mountain', icon: '🏔️', label: 'Mountains', description: 'Hiking, views, nature' },
  { id: 'city', icon: '🏙️', label: 'City Life', description: 'Urban exploration' },
  { id: 'history', icon: '🏛️', label: 'History', description: 'Ancient sites, museums' },
  { id: 'nature', icon: '🌿', label: 'Nature', description: 'Parks, wildlife, scenery' },
  { id: 'adventure', icon: '🎿', label: 'Adventure', description: 'Extreme sports, thrills' },
  { id: 'food', icon: '🍜', label: 'Food & Dining', description: 'Culinary experiences' },
  { id: 'culture', icon: '🎭', label: 'Culture', description: 'Local traditions, arts' },
  { id: 'relaxation', icon: '🧘', label: 'Relaxation', description: 'Spas, wellness, calm' },
  { id: 'nightlife', icon: '🌃', label: 'Nightlife', description: 'Bars, clubs, evening fun' },
  { id: 'shopping', icon: '🛍️', label: 'Shopping', description: 'Markets, boutiques' },
  { id: 'art', icon: '🎨', label: 'Art', description: 'Galleries, exhibitions' },
  { id: 'music', icon: '🎵', label: 'Music', description: 'Concerts, festivals' },
  { id: 'sports', icon: '⚽', label: 'Sports', description: 'Events, activities' },
  { id: 'photography', icon: '📸', label: 'Photography', description: 'Scenic spots' },
  { id: 'wine', icon: '🍷', label: 'Wine & Drinks', description: 'Tastings, vineyards' },
];

export default function QuestionnaireWizard({ onComplete, onCancel }: QuestionnaireWizardProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [direction, setDirection] = useState<'next' | 'prev'>('next');
  const [preferences, setPreferences] = useState<TravelPreferences>({
    origin: '',
    destinations: [],
    travel_start: '',
    travel_end: '',
    budget_level: 'moderate',
    interests: [],
    traveling_with: 'solo',
    passport_country: 'US',
    visa_preference: 'visa_free',
    weather_preference: 'warm',
    max_flight_duration: 12,
    accessibility_needs: [],
    dietary_restrictions: [],
    notes: '',
  });

  const currentStep = STEPS[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === STEPS.length - 1;
  const progress = ((currentStepIndex + 1) / STEPS.length) * 100;

  const canProceed = useCallback(() => {
    switch (currentStep) {
      case 'origin-dates':
        return preferences.origin && preferences.travel_start && preferences.travel_end;
      case 'budget-style':
        return preferences.budget_level && preferences.traveling_with;
      case 'interests':
        return (preferences.interests?.length || 0) >= 1;
      case 'preferences':
        return preferences.weather_preference && preferences.visa_preference;
      default:
        return true;
    }
  }, [currentStep, preferences]);

  const nextStep = () => {
    if (!canProceed()) return;
    if (!isLastStep) {
      setDirection('next');
      setCurrentStepIndex(prev => prev + 1);
    }
  };

  const prevStep = () => {
    if (!isFirstStep) {
      setDirection('prev');
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const handleComplete = () => {
    onComplete(preferences);
  };

  const updatePreference = <K extends keyof TravelPreferences>(
    key: K,
    value: TravelPreferences[K]
  ) => {
    setPreferences(prev => ({ ...prev, [key]: value }));
  };

  const toggleInterest = (interestId: string) => {
    const current = preferences.interests || [];
    if (current.includes(interestId)) {
      updatePreference('interests', current.filter(i => i !== interestId));
    } else {
      updatePreference('interests', [...current, interestId]);
    }
  };

  // Step Components
  const WelcomeStep = () => (
    <div className="text-center space-y-6">
      <div className="text-6xl mb-4">✈️</div>
      <h2 className="text-3xl font-bold text-gray-900">Plan Your Perfect Trip</h2>
      <p className="text-lg text-gray-600 max-w-lg mx-auto">
        Answer a few questions about your travel preferences, and our AI will research 
        the best destinations for you in real-time.
      </p>
      <div className="grid grid-cols-3 gap-4 mt-8">
        <div className="p-4 bg-blue-50 rounded-lg">
          <div className="text-2xl mb-2">🤖</div>
          <p className="text-sm font-medium text-gray-700">AI Research</p>
        </div>
        <div className="p-4 bg-green-50 rounded-lg">
          <div className="text-2xl mb-2">⚡</div>
          <p className="text-sm font-medium text-gray-700">Real-time Updates</p>
        </div>
        <div className="p-4 bg-purple-50 rounded-lg">
          <div className="text-2xl mb-2">🎯</div>
          <p className="text-sm font-medium text-gray-700">Personalized</p>
        </div>
      </div>
    </div>
  );

  const OriginDatesStep = () => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Where and When?</h2>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Departure City <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={preferences.origin}
          onChange={(e) => updatePreference('origin', e.target.value)}
          placeholder="e.g., New York, London, Tokyo"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Specific Destinations (Optional)
        </label>
        <input
          type="text"
          value={preferences.destinations?.join(', ') || ''}
          onChange={(e) => updatePreference('destinations', 
            e.target.value ? e.target.value.split(',').map(s => s.trim()) : []
          )}
          placeholder="e.g., Paris, Bali, Japan (leave empty for AI suggestions)"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="text-xs text-gray-500 mt-1">
          Leave empty and we&apos;ll suggest destinations based on your preferences
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Start Date <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            value={preferences.travel_start}
            onChange={(e) => updatePreference('travel_start', e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            End Date <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            value={preferences.travel_end}
            onChange={(e) => updatePreference('travel_end', e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>
    </div>
  );

  const BudgetStyleStep = () => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Budget & Travel Style</h2>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Budget Level <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-2 gap-3">
          {[
            { value: 'low', icon: '💰', label: 'Budget', desc: 'Hostels, street food' },
            { value: 'moderate', icon: '💰💰', label: 'Moderate', desc: '3-star hotels' },
            { value: 'high', icon: '💰💰💰', label: 'High', desc: '4-star hotels' },
            { value: 'luxury', icon: '💎', label: 'Luxury', desc: '5-star resorts' },
          ].map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => updatePreference('budget_level', option.value as any)}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                preferences.budget_level === option.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="text-2xl mb-1">{option.icon}</div>
              <div className="font-medium">{option.label}</div>
              <div className="text-xs text-gray-500">{option.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Traveling With <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-4 gap-3">
          {[
            { value: 'solo', icon: '🧑', label: 'Solo' },
            { value: 'couple', icon: '💑', label: 'Couple' },
            { value: 'family', icon: '👨‍👩‍👧‍👦', label: 'Family' },
            { value: 'group', icon: '👥', label: 'Group' },
          ].map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => updatePreference('traveling_with', option.value as any)}
              className={`p-3 border-2 rounded-lg text-center transition-all ${
                preferences.traveling_with === option.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="text-2xl mb-1">{option.icon}</div>
              <div className="text-sm font-medium">{option.label}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const InterestsStep = () => (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">What Are You Interested In?</h2>
        <p className="text-gray-600">Select at least 1 interest (select as many as you like!)</p>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {INTERESTS_OPTIONS.map((interest) => (
          <button
            key={interest.id}
            type="button"
            onClick={() => toggleInterest(interest.id)}
            className={`p-3 border-2 rounded-lg text-left transition-all ${
              preferences.interests?.includes(interest.id)
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="text-2xl mb-1">{interest.icon}</div>
            <div className="font-medium text-sm">{interest.label}</div>
            <div className="text-xs text-gray-500">{interest.description}</div>
          </button>
        ))}
      </div>

      <div className="bg-blue-50 p-4 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>Selected:</strong> {preferences.interests?.length || 0} interests
          {preferences.interests && preferences.interests.length > 0 && (
            <span className="ml-2">
              ({preferences.interests.join(', ')})
            </span>
          )}
        </p>
      </div>
    </div>
  );

  const PreferencesStep = () => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Additional Preferences</h2>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Preferred Weather <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-5 gap-2">
          {[
            { value: 'hot', icon: '☀️', label: 'Hot', temp: '30°C+' },
            { value: 'warm', icon: '🌤️', label: 'Warm', temp: '20-30°C' },
            { value: 'mild', icon: '⛅', label: 'Mild', temp: '10-20°C' },
            { value: 'cold', icon: '❄️', label: 'Cold', temp: '0-10°C' },
            { value: 'snow', icon: '🌨️', label: 'Snow', temp: '-5 to 5°C' },
          ].map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => updatePreference('weather_preference', option.value as any)}
              className={`p-3 border-2 rounded-lg text-center transition-all ${
                preferences.weather_preference === option.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="text-2xl mb-1">{option.icon}</div>
              <div className="font-medium text-sm">{option.label}</div>
              <div className="text-xs text-gray-500">{option.temp}</div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Visa Preference <span className="text-red-500">*</span>
        </label>
        <div className="space-y-2">
          {[
            { value: 'visa_free', icon: '✅', label: 'Visa-free only', desc: 'No visa required' },
            { value: 'visa_on_arrival', icon: '🛂', label: 'Visa on arrival OK', desc: 'Get visa at airport' },
            { value: 'evisa_ok', icon: '📱', label: 'eVisa OK', desc: 'Apply online before travel' },
          ].map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => updatePreference('visa_preference', option.value as any)}
              className={`w-full p-4 border-2 rounded-lg text-left flex items-center gap-4 transition-all ${
                preferences.visa_preference === option.value
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <span className="text-2xl">{option.icon}</span>
              <div>
                <div className="font-medium">{option.label}</div>
                <div className="text-xs text-gray-500">{option.desc}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Passport Country
        </label>
        <select
          value={preferences.passport_country}
          onChange={(e) => updatePreference('passport_country', e.target.value)}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="US">🇺🇸 United States</option>
          <option value="UK">🇬🇧 United Kingdom</option>
          <option value="CA">🇨🇦 Canada</option>
          <option value="AU">🇦🇺 Australia</option>
          <option value="DE">🇩🇪 Germany</option>
          <option value="FR">🇫🇷 France</option>
          <option value="JP">🇯🇵 Japan</option>
          <option value="IN">🇮🇳 India</option>
          <option value="BR">🇧🇷 Brazil</option>
          <option value="Other">🌍 Other</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Max Flight Duration
        </label>
        <input
          type="range"
          min="3"
          max="24"
          step="1"
          value={preferences.max_flight_duration || 12}
          onChange={(e) => updatePreference('max_flight_duration', parseInt(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-sm text-gray-600 mt-1">
          <span>3h</span>
          <span className="font-medium">{preferences.max_flight_duration || 12} hours</span>
          <span>24h</span>
        </div>
      </div>
    </div>
  );

  const ReviewStep = () => (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Review Your Preferences</h2>
      
      <div className="bg-gray-50 rounded-lg p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">From</p>
            <p className="font-medium">{preferences.origin || 'Not specified'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Dates</p>
            <p className="font-medium">
              {preferences.travel_start} to {preferences.travel_end}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Budget</p>
            <p className="font-medium capitalize">{preferences.budget_level}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Traveling With</p>
            <p className="font-medium capitalize">{preferences.traveling_with}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Weather</p>
            <p className="font-medium capitalize">{preferences.weather_preference}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Visa Preference</p>
            <p className="font-medium capitalize">{preferences.visa_preference?.replace('_', ' ')}</p>
          </div>
        </div>

        <div>
          <p className="text-sm text-gray-500 mb-2">Interests</p>
          <div className="flex flex-wrap gap-2">
            {preferences.interests?.map((interest) => {
              const option = INTERESTS_OPTIONS.find(i => i.id === interest);
              return (
                <span key={interest} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                  {option?.icon} {option?.label}
                </span>
              );
            })}
          </div>
        </div>

        {preferences.destinations && preferences.destinations.length > 0 && (
          <div>
            <p className="text-sm text-gray-500 mb-2">Specific Destinations</p>
            <p className="font-medium">{preferences.destinations.join(', ')}</p>
          </div>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Ready?</strong> Click &quot;Start AI Research&quot; and watch in real-time as our AI 
          researches destinations, checks weather, flights, hotels, and more!
        </p>
      </div>
    </div>
  );

  // Render current step
  const renderStep = () => {
    switch (currentStep) {
      case 'welcome': return <WelcomeStep />;
      case 'origin-dates': return <OriginDatesStep />;
      case 'budget-style': return <BudgetStyleStep />;
      case 'interests': return <InterestsStep />;
      case 'preferences': return <PreferencesStep />;
      case 'review': return <ReviewStep />;
      default: return null;
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress Bar */}
      {!isFirstStep && (
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Step {currentStepIndex} of {STEPS.length - 1}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Step Content */}
      <div className={`bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8 ${
        direction === 'next' ? 'animate-fade-in-right' : 'animate-fade-in-left'
      }`}>
        {renderStep()}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-6">
        <button
          onClick={isFirstStep ? onCancel : prevStep}
          className="px-6 py-3 text-gray-600 font-medium hover:text-gray-800 transition-colors"
        >
          {isFirstStep ? 'Cancel' : '← Back'}
        </button>
        
        {!isLastStep ? (
          <button
            onClick={nextStep}
            disabled={!canProceed()}
            className="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        ) : (
          <button
            onClick={handleComplete}
            className="px-8 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
          >
            <span>🚀</span>
            Start AI Research
          </button>
        )}
      </div>
    </div>
  );
}
