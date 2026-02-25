'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useResearch } from '@/hooks/useResearch';

export function AutonomousResearchForm() {
  const {
    startResearch,
    cancelResearch,
    status,
    progress,
    currentStep,
    results,
    error,
    messages,
    isConnected,
    jobId
  } = useResearch();
  
  const [preferences, setPreferences] = useState({
    origin: '',
    destinations: [] as string[],
    travel_start: '',
    travel_end: '',
    budget_level: 'moderate',
    interests: [] as string[],
    traveling_with: 'solo',
    passport_country: 'US',
    special_requirements: '',
    // New fields
    has_kids: false,
    kids_count: 0,
    kids_ages: [] as string[],
    trip_type: 'leisure',
    pace_preference: 'moderate',
    flight_duration_max: 12,
    accessibility_needs: [] as string[],
    dietary_restrictions: [] as string[]
  });
  
  const logEndRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll activity log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await startResearch(preferences);
  };
  
  const interestOptions = [
    'beach', 'mountains', 'city', 'history', 'culture',
    'food', 'adventure', 'nature', 'shopping', 'nightlife',
    'art', 'photography', 'wildlife', 'sports', 'relaxation'
  ];

  const kidsAgeOptions = [
    '0-2 (Infant)', '3-5 (Toddler)', '6-12 (Child)', '13-17 (Teen)'
  ];

  const accessibilityOptions = [
    'Wheelchair accessible', 'Stroller friendly', 'Elevator access', 
    'Ground floor rooms', 'Quiet environment'
  ];

  const dietaryOptions = [
    'Vegetarian', 'Vegan', 'Halal', 'Kosher', 
    'Gluten-free', 'Nut allergies', 'Dairy-free'
  ];
  
  const toggleInterest = (interest: string) => {
    setPreferences(prev => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter(i => i !== interest)
        : [...prev.interests, interest]
    }));
  };

  const toggleKidsAge = (age: string) => {
    setPreferences(prev => ({
      ...prev,
      kids_ages: prev.kids_ages.includes(age)
        ? prev.kids_ages.filter(a => a !== age)
        : [...prev.kids_ages, age]
    }));
  };

  const toggleAccessibility = (need: string) => {
    setPreferences(prev => ({
      ...prev,
      accessibility_needs: prev.accessibility_needs.includes(need)
        ? prev.accessibility_needs.filter(n => n !== need)
        : [...prev.accessibility_needs, need]
    }));
  };

  const toggleDietary = (diet: string) => {
    setPreferences(prev => ({
      ...prev,
      dietary_restrictions: prev.dietary_restrictions.includes(diet)
        ? prev.dietary_restrictions.filter(d => d !== diet)
        : [...prev.dietary_restrictions, diet]
    }));
  };
  
  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left column - Form */}
        <div>
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <span className="text-3xl">🤖</span>
            Autonomous Travel Researcher
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Origin */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Departure City
              </label>
              <input
                type="text"
                value={preferences.origin}
                onChange={(e) => setPreferences({...preferences, origin: e.target.value})}
                placeholder="e.g., New York"
                className="w-full p-3 border rounded-lg"
                required
              />
            </div>
            
            {/* Travel Dates */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Start Date
                </label>
                <input
                  type="date"
                  value={preferences.travel_start}
                  onChange={(e) => setPreferences({...preferences, travel_start: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  End Date
                </label>
                <input
                  type="date"
                  value={preferences.travel_end}
                  onChange={(e) => setPreferences({...preferences, travel_end: e.target.value})}
                  className="w-full p-3 border rounded-lg"
                  required
                />
              </div>
            </div>
            
            {/* Budget Level */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Budget Level
              </label>
              <select
                value={preferences.budget_level}
                onChange={(e) => setPreferences({...preferences, budget_level: e.target.value})}
                className="w-full p-3 border rounded-lg"
              >
                <option value="low">💵 Low - Budget traveler</option>
                <option value="moderate">💰 Moderate - Comfortable</option>
                <option value="high">💎 High - Premium experiences</option>
                <option value="luxury">👑 Luxury - No budget limits</option>
              </select>
            </div>
            
            {/* Interests */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Your Interests (select multiple)
              </label>
              <div className="flex flex-wrap gap-2">
                {interestOptions.map(interest => (
                  <button
                    key={interest}
                    type="button"
                    onClick={() => toggleInterest(interest)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-colors
                      ${preferences.interests.includes(interest)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                  >
                    {interest}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Traveling With */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Traveling With
              </label>
              <select
                value={preferences.traveling_with}
                onChange={(e) => setPreferences({...preferences, traveling_with: e.target.value})}
                className="w-full p-3 border rounded-lg"
              >
                <option value="solo">🧑 Solo</option>
                <option value="couple">💑 Couple</option>
                <option value="family">👪 Family (with kids)</option>
                <option value="group">👥 Group of friends</option>
              </select>
            </div>

            {/* Kids Section - Only show for family */}
            {preferences.traveling_with === 'family' && (
              <div className="bg-blue-50 p-4 rounded-lg space-y-4">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="has_kids"
                    checked={preferences.has_kids}
                    onChange={(e) => setPreferences({...preferences, has_kids: e.target.checked})}
                    className="w-5 h-5"
                  />
                  <label htmlFor="has_kids" className="text-sm font-medium">
                    Traveling with children
                  </label>
                </div>

                {preferences.has_kids && (
                  <>
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Number of children
                      </label>
                      <select
                        value={preferences.kids_count}
                        onChange={(e) => setPreferences({...preferences, kids_count: parseInt(e.target.value)})}
                        className="w-full p-3 border rounded-lg"
                      >
                        <option value={1}>1 child</option>
                        <option value={2}>2 children</option>
                        <option value={3}>3 children</option>
                        <option value={4}>4+ children</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Children&apos;s age ranges
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {kidsAgeOptions.map(age => (
                          <button
                            key={age}
                            type="button"
                            onClick={() => toggleKidsAge(age)}
                            className={`px-3 py-1.5 rounded-full text-sm transition-colors
                              ${preferences.kids_ages.includes(age)
                                ? 'bg-blue-600 text-white'
                                : 'bg-white text-gray-700 hover:bg-gray-100'
                              }`}
                          >
                            {age}
                          </button>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Trip Type */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Trip Type
              </label>
              <select
                value={preferences.trip_type}
                onChange={(e) => setPreferences({...preferences, trip_type: e.target.value})}
                className="w-full p-3 border rounded-lg"
              >
                <option value="leisure">🏖️ Leisure & Relaxation</option>
                <option value="adventure">🏔️ Adventure & Exploration</option>
                <option value="cultural">🏛️ Cultural & Historical</option>
                <option value="romantic">💕 Romantic Getaway</option>
                <option value="family">👨‍👩‍👧‍👦 Family Vacation</option>
                <option value="business">💼 Business Trip</option>
                <option value="food">🍽️ Food & Culinary</option>
                <option value="wellness">🧘 Wellness & Spa</option>
              </select>
            </div>

            {/* Pace Preference */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Trip Pace
              </label>
              <select
                value={preferences.pace_preference}
                onChange={(e) => setPreferences({...preferences, pace_preference: e.target.value})}
                className="w-full p-3 border rounded-lg"
              >
                <option value="relaxed">😌 Relaxed - Sleep in, few activities</option>
                <option value="moderate">⚖️ Moderate - Balance of activities & rest</option>
                <option value="busy">🏃 Busy - Pack in as much as possible</option>
              </select>
            </div>

            {/* Max Flight Duration */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Maximum Flight Duration
              </label>
              <select
                value={preferences.flight_duration_max}
                onChange={(e) => setPreferences({...preferences, flight_duration_max: parseInt(e.target.value)})}
                className="w-full p-3 border rounded-lg"
              >
                <option value={3}>✈️ Up to 3 hours (Short haul)</option>
                <option value={6}>✈️ Up to 6 hours (Medium haul)</option>
                <option value={12}>✈️ Up to 12 hours (Long haul)</option>
                <option value={20}>✈️ Any duration (Worldwide)</option>
              </select>
            </div>
            
            {/* Passport Country */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Passport Country
              </label>
              <select
                value={preferences.passport_country}
                onChange={(e) => setPreferences({...preferences, passport_country: e.target.value})}
                className="w-full p-3 border rounded-lg"
              >
                <option value="US">🇺🇸 United States</option>
                <option value="UK">🇬🇧 United Kingdom</option>
                <option value="CA">🇨🇦 Canada</option>
                <option value="AU">🇦🇺 Australia</option>
                <option value="IN">🇮🇳 India</option>
                <option value="SG">🇸🇬 Singapore</option>
                <option value="DE">🇩🇪 Germany</option>
                <option value="FR">🇫🇷 France</option>
              </select>
            </div>

            {/* Accessibility Needs */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Accessibility Needs (Optional)
              </label>
              <div className="flex flex-wrap gap-2">
                {accessibilityOptions.map(need => (
                  <button
                    key={need}
                    type="button"
                    onClick={() => toggleAccessibility(need)}
                    className={`px-3 py-1.5 rounded-full text-sm transition-colors
                      ${preferences.accessibility_needs.includes(need)
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                  >
                    {need}
                  </button>
                ))}
              </div>
            </div>

            {/* Dietary Restrictions */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Dietary Requirements (Optional)
              </label>
              <div className="flex flex-wrap gap-2">
                {dietaryOptions.map(diet => (
                  <button
                    key={diet}
                    type="button"
                    onClick={() => toggleDietary(diet)}
                    className={`px-3 py-1.5 rounded-full text-sm transition-colors
                      ${preferences.dietary_restrictions.includes(diet)
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                  >
                    {diet}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Special Requirements */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Special Requirements (optional)
              </label>
              <textarea
                value={preferences.special_requirements}
                onChange={(e) => setPreferences({...preferences, special_requirements: e.target.value})}
                placeholder="e.g., Pet friendly, celebrating anniversary, specific activities..."
                className="w-full p-3 border rounded-lg"
                rows={3}
              />
            </div>
            
            {/* Submit Button */}
            <button
              type="submit"
              disabled={status === 'researching' || preferences.interests.length === 0}
              className="w-full bg-blue-600 text-white py-4 rounded-lg font-semibold text-lg
                       hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
            >
              {status === 'researching' && (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Researching...
                </>
              )}
              {status === 'idle' && '🔍 Start Autonomous Research'}
              {(status === 'completed' || status === 'error') && '✨ Research Again'}
            </button>
          </form>
        </div>
        
        {/* Right column - Live Research Feed */}
        <div className="lg:border-l lg:pl-8">
          <div className="sticky top-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold flex items-center gap-2">
                <span>📡 Live Research Feed</span>
                {isConnected && (
                  <span className="flex items-center gap-1 text-sm text-green-600">
                    <span className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></span>
                    Connected
                  </span>
                )}
              </h3>
              
              {jobId && status === 'researching' && (
                <button
                  onClick={cancelResearch}
                  className="text-sm text-red-600 hover:text-red-800"
                >
                  Stop
                </button>
              )}
            </div>
            
            {/* Progress Bar */}
            {status === 'researching' && (
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{currentStep || 'Researching...'}</span>
                  <span className="text-gray-600">{progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
              </div>
            )}
            
            {/* Activity Log */}
            <div className="bg-gray-50 rounded-lg p-4 h-[500px] overflow-y-auto font-mono text-sm">
              {messages.length === 0 && (
                <div className="text-gray-400 text-center mt-20">
                  <div className="text-4xl mb-2">🤖</div>
                  <p>Ready to research...</p>
                  <p className="text-xs mt-2">Fill the form and start to see live research</p>
                </div>
              )}
              
              {messages.map((entry, index) => (
                <div key={index} className={`mb-2 border-l-2 pl-3 py-1
                  ${entry.type === 'error' ? 'border-red-400' : 
                    entry.type === 'success' ? 'border-green-400' : 
                    entry.type === 'step' ? 'border-blue-400' : 
                    'border-gray-300'}`}
                >
                  <span className="text-gray-400 text-xs">
                    {entry.timestamp.toLocaleTimeString()}
                  </span>
                  <span className="ml-2 text-gray-800">{entry.message}</span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
            
            {/* Results */}
            {results && status === 'completed' && (
              <div className="mt-6">
                <h4 className="font-semibold mb-2 flex items-center gap-2">
                  <span>🎉 Research Complete!</span>
                </h4>
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-sm font-medium mb-2">
                    Top Recommendations:
                  </div>
                  <div className="space-y-2">
                    {results.recommendations?.map((rec: any, i: number) => (
                      <div key={i} className="bg-white p-3 rounded-lg shadow-sm">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold">
                            {i+1}. {rec.destination}
                          </span>
                          <span className="text-green-600 font-bold">
                            {Math.round(rec.score)}%
                          </span>
                        </div>
                        <ul className="mt-1 text-xs text-gray-600 list-disc list-inside">
                          {rec.reasons?.map((reason: string, j: number) => (
                            <li key={j}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
            
            {error && (
              <div className="mt-6 bg-red-50 text-red-700 p-4 rounded-lg">
                {error}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
