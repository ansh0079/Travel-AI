'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useResearch } from '@/hooks/useResearch';
import { api } from '@/services/api';
import Link from 'next/link';

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
    notes: '',
    // New fields
    has_kids: false,
    kids_count: 0,
    kids_ages: [] as string[],
    trip_type: 'leisure',
    pace_preference: 'moderate',
    max_flight_duration: 12,
    accessibility_needs: [] as string[],
    dietary_restrictions: [] as string[],
    // Research depth
    research_depth: 'standard' as 'quick' | 'standard' | 'deep'
  });
  const [destinationsInput, setDestinationsInput] = useState('');
  const [isExportingDestination, setIsExportingDestination] = useState<string | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  
  const logEndRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll activity log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanedDestinations = destinationsInput
      .split(',')
      .map((part) => part.trim())
      .filter(Boolean);
    
    // Auto-suggest depth if not explicitly selected
    let finalPreferences = { ...preferences, destinations: cleanedDestinations };
    if (!preferences.research_depth) {
      // Simple client-side depth suggestion
      const suggestedDepth = suggestResearchDepth(preferences);
      finalPreferences = { ...finalPreferences, research_depth: suggestedDepth };
    }
    
    await startResearch(finalPreferences);
  };

  const suggestResearchDepth = (prefs: typeof preferences): 'quick' | 'standard' | 'deep' => {
    // Luxury/high budget → deep
    if (prefs.budget_level === 'luxury' || prefs.budget_level === 'high') return 'deep';
    
    // Romantic trips → deep
    if (prefs.trip_type === 'romantic') return 'deep';
    
    // Family with kids → standard
    if (prefs.has_kids || prefs.traveling_with === 'family') return 'standard';
    
    // Adventure/cultural → standard
    if (['adventure', 'cultural'].includes(prefs.trip_type)) return 'standard';
    
    // Default to standard
    return 'standard';
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

  const getDestinationResearch = (destination: string) =>
    results?.destinations?.find((d: any) => d.name?.toLowerCase() === destination.toLowerCase());

  const getEvidenceChips = (destination: string): string[] => {
    const detail = getDestinationResearch(destination);
    if (!detail?.data) return [];
    const chips: string[] = [];
    if (detail.data.weather?.condition) chips.push(`Weather: ${detail.data.weather.condition}`);
    if (typeof detail.data.visa?.visa_required === 'boolean') {
      chips.push(detail.data.visa.visa_required ? 'Visa required' : 'Visa-friendly');
    }
    if (Array.isArray(detail.data.attractions)) chips.push(`${detail.data.attractions.length} attractions`);
    if (Array.isArray(detail.data.events) && detail.data.events.length > 0) chips.push(`${detail.data.events.length} events`);
    if (Array.isArray(detail.data.flights) && detail.data.flights.length > 0) chips.push('Flight data included');
    if (Array.isArray(detail.data.hotels) && detail.data.hotels.length > 0) chips.push('Hotel data included');
    if (detail.data.web_research) chips.push('Web evidence included');
    return chips;
  };

  const getWebSources = (destination: string): string[] => {
    const detail = getDestinationResearch(destination);
    const webResearch = detail?.data?.web_research;
    if (!webResearch) return [];

    const toUrl = (entry: any): string | null => {
      if (!entry) return null;
      if (typeof entry === 'string') return entry;
      if (typeof entry === 'object') {
        const candidate = entry.href || entry.url || entry.source;
        return typeof candidate === 'string' ? candidate : null;
      }
      return null;
    };

    const rawSources = [
      ...(Array.isArray(webResearch.sources) ? webResearch.sources : []),
      ...(Array.isArray(webResearch.research_sources) ? webResearch.research_sources : []),
      ...(Array.isArray(webResearch.general_info?.sources) ? webResearch.general_info.sources : []),
      ...(Array.isArray(webResearch.travel_tips?.sources) ? webResearch.travel_tips.sources : []),
    ];

    return Array.from(
      new Set(
        rawSources
          .map(toUrl)
          .filter((source): source is string => Boolean(source && /^https?:\/\//i.test(source)))
      )
    );
  };

  const handleUsePlan = async (destination: string) => {
    setSelectedPlan(destination);
    try {
      await api.trackAnalyticsEvent('recommendation_accepted', jobId || undefined, {
        destination,
        source: 'research_use_plan',
      });
    } catch (err) {
      console.warn('Failed to track recommendation acceptance', err);
    }
  };

  const getDataSourceBadge = (source?: string) => {
    if (!source) return null;
    
    const isReal = source !== 'Mock Data';
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${
        isReal 
          ? 'bg-green-100 text-green-700' 
          : 'bg-gray-100 text-gray-500'
      }`}>
        {isReal ? '🔗 Live' : '📦 Mock'} • {source}
      </span>
    );
  };

  const handleExport = async (rec: any) => {
    setIsExportingDestination(rec.destination);
    try {
      await api.trackAnalyticsEvent('recommendation_accepted', jobId || undefined, {
        destination: rec.destination,
        source: 'research_export',
      });
      const exported = await api.exportTripBrief({
        destination: rec.destination,
        score: rec.score,
        reasons: rec.reasons || [],
        highlights: {
          ...(rec.highlights || {}),
          evidence: getEvidenceChips(rec.destination),
          web_sources: getWebSources(rec.destination).length,
        },
      });

      const fileName = `${rec.destination.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-trip-brief.md`;
      const blob = new Blob([exported.markdown], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = fileName;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export trip brief', err);
    } finally {
      setIsExportingDestination(null);
    }
  };
  
  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left column - Form */}
        <div>
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <span className="text-3xl">AI</span>
            Autonomous Travel Researcher
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Origin */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Where are you starting from?
              </label>
              <input
                type="text"
                value={preferences.origin}
                onChange={(e) => setPreferences(prev => ({...prev, origin: e.target.value}))}
                placeholder="e.g., New York"
                className="w-full p-3 border rounded-lg"
                required
              />
            </div>

            {/* Destinations (optional) */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Preferred destinations (optional)
              </label>
              <input
                type="text"
                value={destinationsInput}
                onChange={(e) => setDestinationsInput(e.target.value)}
                onBlur={() =>
                  setPreferences((prev) => ({
                    ...prev,
                    destinations: destinationsInput
                      .split(',')
                      .map((part) => part.trim())
                      .filter(Boolean),
                  }))
                }
                placeholder="e.g., Tokyo, Bali, Rome"
                className="w-full p-3 border rounded-lg"
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave blank to let the agent suggest destinations.
              </p>
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
                  onChange={(e) => setPreferences(prev => ({...prev, travel_start: e.target.value}))}
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
                  onChange={(e) => setPreferences(prev => ({...prev, travel_end: e.target.value}))}
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
                onChange={(e) => setPreferences(prev => ({...prev, budget_level: e.target.value}))}
                className="w-full p-3 border rounded-lg"
              >
                <option value="low">Low - Budget traveler</option>
                <option value="moderate">Moderate - Comfortable</option>
                <option value="high">High - Premium experiences</option>
                <option value="luxury">Luxury - No budget limits</option>
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
                onChange={(e) => setPreferences(prev => ({...prev, traveling_with: e.target.value}))}
                className="w-full p-3 border rounded-lg"
              >
                <option value="solo">Solo</option>
                <option value="couple">Couple</option>
                <option value="family">Family (with kids)</option>
                <option value="group">Group of friends</option>
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
                    onChange={(e) => setPreferences(prev => ({...prev, has_kids: e.target.checked}))}
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
                        onChange={(e) => setPreferences(prev => ({...prev, kids_count: parseInt(e.target.value)}))}
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
                onChange={(e) => setPreferences(prev => ({...prev, trip_type: e.target.value}))}
                className="w-full p-3 border rounded-lg"
              >
                <option value="leisure">Leisure and Relaxation</option>
                <option value="adventure">Adventure and Exploration</option>
                <option value="cultural">Cultural and Historical</option>
                <option value="romantic">Romantic Getaway</option>
                <option value="family">Family Vacation</option>
                <option value="business">Business Trip</option>
                <option value="food">Food and Culinary</option>
                <option value="wellness">Wellness and Spa</option>
              </select>
            </div>

            {/* Pace Preference */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Trip Pace
              </label>
              <select
                value={preferences.pace_preference}
                onChange={(e) => setPreferences(prev => ({...prev, pace_preference: e.target.value}))}
                className="w-full p-3 border rounded-lg"
              >
                <option value="relaxed">Relaxed - Sleep in, few activities</option>
                <option value="moderate">Moderate - Balance of activities and rest</option>
                <option value="busy">Busy - Pack in as much as possible</option>
              </select>
            </div>

            {/* Max Flight Duration */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Maximum Flight Duration
              </label>
              <select
                value={preferences.max_flight_duration}
                onChange={(e) => setPreferences(prev => ({...prev, max_flight_duration: parseInt(e.target.value)}))}
                className="w-full p-3 border rounded-lg"
              >
                <option value={3}>Up to 3 hours (Short haul)</option>
                <option value={6}>Up to 6 hours (Medium haul)</option>
                <option value={12}>Up to 12 hours (Long haul)</option>
                <option value={20}>Any duration (Worldwide)</option>
              </select>
            </div>

            {/* Passport Country */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Passport Country
              </label>
              <select
                value={preferences.passport_country}
                onChange={(e) => setPreferences(prev => ({...prev, passport_country: e.target.value}))}
                className="w-full p-3 border rounded-lg"
              >
                <option value="US">United States</option>
                <option value="UK">United Kingdom</option>
                <option value="CA">Canada</option>
                <option value="AU">Australia</option>
                <option value="IN">India</option>
                <option value="SG">Singapore</option>
                <option value="DE">Germany</option>
                <option value="FR">France</option>
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

            {/* Research Depth */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium">
                  Research Depth
                </label>
                <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
                  ✨ Recommended: {suggestResearchDepth(preferences).charAt(0).toUpperCase() + suggestResearchDepth(preferences).slice(1)}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setPreferences(prev => ({...prev, research_depth: 'quick'}))}
                  className={`p-3 rounded-lg border-2 transition-all text-left
                    ${preferences.research_depth === 'quick'
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                    }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">⚡</span>
                    <span className="font-semibold text-sm">Quick</span>
                  </div>
                  <div className="text-xs text-gray-600">~30 seconds</div>
                  <div className="text-xs text-gray-500 mt-1">Basic info only</div>
                </button>

                <button
                  type="button"
                  onClick={() => setPreferences(prev => ({...prev, research_depth: 'standard'}))}
                  className={`p-3 rounded-lg border-2 transition-all text-left
                    ${preferences.research_depth === 'standard'
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                    }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">📊</span>
                    <span className="font-semibold text-sm">Standard</span>
                  </div>
                  <div className="text-xs text-gray-600">~2 minutes</div>
                  <div className="text-xs text-gray-500 mt-1">Full research + deals</div>
                </button>

                <button
                  type="button"
                  onClick={() => setPreferences(prev => ({...prev, research_depth: 'deep'}))}
                  className={`p-3 rounded-lg border-2 transition-all text-left
                    ${preferences.research_depth === 'deep'
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                    }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">🔬</span>
                    <span className="font-semibold text-sm">Deep</span>
                  </div>
                  <div className="text-xs text-gray-600">~5 minutes</div>
                  <div className="text-xs text-gray-500 mt-1">Everything + safety</div>
                </button>
              </div>
            </div>

            {/* Special Requirements */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Special Requirements (optional)
              </label>
              <textarea
                value={preferences.notes}
                onChange={(e) => setPreferences(prev => ({...prev, notes: e.target.value}))}
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
              {status === 'idle' && 'Start Autonomous Research'}
              {(status === 'completed' || status === 'error') && 'Research Again'}
            </button>
          </form>
        </div>
        
        {/* Right column - Live Research Feed */}
        <div className="lg:border-l lg:pl-8">
          <div className="sticky top-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold flex items-center gap-2">
                <span>Live Research Feed</span>
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
                  <div className="text-4xl mb-2">AI</div>
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
                  <span>Research Complete</span>
                </h4>
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-sm font-medium mb-2">
                    Top Recommendations:
                  </div>
                  <div className="space-y-2">
                    {results.recommendations?.map((rec: any, i: number) => (
                      <div key={i} className="bg-white p-3 rounded-lg shadow-sm">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold">
                                {i + 1}. {rec.destination}
                              </span>
                              <span className="text-green-600 font-bold">
                                {Math.round(rec.score)}%
                              </span>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              <Link
                                href={`/city/${encodeURIComponent(rec.destination)}?origin=${encodeURIComponent(preferences.origin || '')}&travel_start=${preferences.travel_start || ''}&travel_end=${preferences.travel_end || ''}&budget_level=${preferences.budget_level || 'moderate'}&passport_country=${preferences.passport_country || 'US'}`}
                                className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700 transition-colors"
                              >
                                View details &rarr;
                              </Link>
                              <button
                                onClick={() => handleUsePlan(rec.destination)}
                                className={`text-xs px-2 py-1 rounded transition-colors ${
                                  selectedPlan === rec.destination
                                    ? 'bg-emerald-100 text-emerald-700'
                                    : 'bg-emerald-600 text-white hover:bg-emerald-700'
                                }`}
                              >
                                {selectedPlan === rec.destination ? 'Selected' : 'Use this plan'}
                              </button>
                              <button
                                onClick={() => handleExport(rec)}
                                disabled={isExportingDestination === rec.destination}
                                className="text-xs bg-gray-800 text-white px-2 py-1 rounded hover:bg-gray-900 disabled:opacity-60"
                              >
                                {isExportingDestination === rec.destination ? 'Exporting...' : 'Export trip'}
                              </button>
                            </div>
                          </div>
                        </div>
                        {rec.reasons?.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs font-medium text-gray-700 mb-1">Why this?</p>
                            <ul className="text-xs text-gray-600 list-disc list-inside">
                              {rec.reasons.map((reason: string, j: number) => (
                                <li key={j}>{reason}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {getEvidenceChips(rec.destination).length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs font-medium text-gray-700 mb-1">Evidence</p>
                            <div className="flex flex-wrap gap-1.5">
                              {getEvidenceChips(rec.destination).map((chip, chipIdx) => (
                                <span key={chipIdx} className="text-[11px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                                  {chip}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {getDestinationResearch(rec.destination)?.data?.web_research && (
                          <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded">
                            <p className="text-xs font-medium text-amber-800">From the web</p>
                            {getWebSources(rec.destination).length > 0 ? (
                              <div className="mt-1 space-y-1">
                                {getWebSources(rec.destination).slice(0, 3).map((source, sourceIdx) => (
                                  <a
                                    key={`${source}-${sourceIdx}`}
                                    href={source}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block text-[11px] text-amber-700 underline break-all"
                                  >
                                    {source}
                                  </a>
                                ))}
                              </div>
                            ) : (
                              <p className="text-[11px] text-amber-700 mt-1">
                                External web research evidence was included for this destination.
                              </p>
                            )}
                          </div>
                        )}
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
