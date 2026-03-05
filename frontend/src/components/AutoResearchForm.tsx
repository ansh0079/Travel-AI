'use client';

import { useState, useEffect } from 'react';
import { useWebSocketResearch } from '@/hooks/useWebSocketResearch';
import { api, TravelPreferences } from '@/services/api';
import Link from 'next/link';

const INTERESTS_OPTIONS = [
  'beach', 'mountain', 'city', 'history', 'nature',
  'adventure', 'food', 'culture', 'relaxation', 'nightlife',
  'shopping', 'art', 'music', 'sports', 'photography'
];

export default function AutoResearchForm() {
  const {
    jobId,
    jobStatus,
    results,
    isConnected,
    isStarting,
    isResearching,
    messages,
    error,
    connectionError,
    startResearch,
    clearResults,
    reconnect
  } = useWebSocketResearch();

  const [formData, setFormData] = useState<TravelPreferences>({
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
  });
  const [isExporting, setIsExporting] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  // Auto-clear results after showing for 30 minutes
  useEffect(() => {
    if (results) {
      const timer = setTimeout(() => {
        // Optional: auto-clear or refresh
      }, 30 * 60 * 1000);
      return () => clearTimeout(timer);
    }
  }, [results]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await startResearch(formData);
  };

  const toggleInterest = (interest: string) => {
    setFormData(prev => ({
      ...prev,
      interests: prev.interests?.includes(interest)
        ? prev.interests.filter(i => i !== interest)
        : [...(prev.interests || []), interest]
    }));
  };

  const getDestinationResearch = (destination: string) =>
    results?.destinations?.find((d) => d.name?.toLowerCase() === destination.toLowerCase());

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

  const handleUsePlan = async (destination: string) => {
    setSelectedPlan(destination);
    try {
      await api.trackAnalyticsEvent('recommendation_accepted', jobId || undefined, {
        destination,
        source: 'auto_research_use_plan',
      });
    } catch (err) {
      console.warn('Failed to track recommendation acceptance', err);
    }
  };

  const handleExport = async (rec: any) => {
    setIsExporting(true);
    try {
      const detail = getDestinationResearch(rec.destination);
      await api.trackAnalyticsEvent('recommendation_accepted', jobId || undefined, {
        destination: rec.destination,
        source: 'auto_research_export',
      });
      const exported = await api.exportTripBrief({
        destination: rec.destination,
        score: rec.score,
        reasons: rec.reasons || [],
        highlights: {
          ...(rec.highlights || {}),
          evidence: getEvidenceChips(rec.destination),
          web_sources: Array.isArray(detail?.data?.web_research?.sources)
            ? detail?.data?.web_research?.sources.length
            : 0,
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
      setIsExporting(false);
    }
  };

  // Progress bar component
  const ProgressBar = () => {
    if (!jobStatus) return null;
    
    const percentage = jobStatus.progress_percentage;
    let statusColor = 'bg-blue-500';
    if (jobStatus.status === 'completed') statusColor = 'bg-green-500';
    if (jobStatus.status === 'failed') statusColor = 'bg-red-500';
    
    return (
      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-4">
        <div 
          className={`h-2.5 rounded-full ${statusColor} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    );
  };

  // Connection status indicator
  const ConnectionStatus = () => (
    <div className="flex items-center gap-2 text-sm">
      <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} ${isConnected ? '' : 'animate-pulse'}`} />
      <span className={isConnected ? 'text-green-600' : 'text-red-600'}>
        {isConnected ? 'Live updates' : connectionError ? 'Connection error' : 'Connecting...'}
      </span>
      {connectionError && (
        <button 
          onClick={reconnect}
          className="text-blue-600 hover:underline text-xs"
        >
          Retry
        </button>
      )}
    </div>
  );

  // Activity log component
  const ActivityLog = () => {
    if (!isResearching || messages.length === 0) return null;
    
    // Show last 5 relevant messages
    const relevantMessages = messages
      .filter(m => m.type === 'progress' || m.type === 'started' || m.type === 'completed')
      .slice(-5);
    
    if (relevantMessages.length === 0) return null;
    
    return (
      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-xs font-medium text-gray-500 mb-2">Activity Log:</p>
        <div className="space-y-1">
          {relevantMessages.map((msg, idx) => (
            <div key={idx} className="text-xs text-gray-600 flex items-center gap-2">
              {msg.type === 'started' && <span className="text-blue-500">▶</span>}
              {msg.type === 'progress' && <span className="text-blue-400">⟳</span>}
              {msg.type === 'completed' && <span className="text-green-500">✓</span>}
              <span className="capitalize">{msg.step?.replace(/_/g, ' ') || msg.message}</span>
              {msg.percentage !== undefined && (
                <span className="text-gray-400">({msg.percentage}%)</span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-2">AI Travel Research</h1>
      <p className="text-gray-600 mb-8">
        Answer a few questions and our AI agent will automatically research destinations for you in real-time.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          <strong>Error:</strong> {error.message}
        </div>
      )}

      {/* Research Form */}
      {!jobId && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Origin */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Where are you traveling from? <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.origin}
              onChange={(e) => setFormData(prev => ({ ...prev, origin: e.target.value }))}
              placeholder="e.g., New York, London, Tokyo"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          {/* Destinations (optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Any specific destinations in mind? (Optional)
            </label>
            <input
              type="text"
              value={formData.destinations?.join(', ') || ''}
              onChange={(e) => setFormData(prev => ({ 
                ...prev, 
                destinations: e.target.value ? e.target.value.split(',').map(s => s.trim()) : [] 
              }))}
              placeholder="Leave empty for AI suggestions, or enter: Paris, Tokyo, Bali"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Leave blank and we&apos;ll suggest destinations based on your preferences
            </p>
          </div>

          {/* Travel Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={formData.travel_start}
                onChange={(e) => setFormData(prev => ({ ...prev, travel_start: e.target.value }))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={formData.travel_end}
                onChange={(e) => setFormData(prev => ({ ...prev, travel_end: e.target.value }))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
          </div>

          {/* Budget */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Budget Level <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.budget_level}
              onChange={(e) => setFormData(prev => ({ ...prev, budget_level: e.target.value as any }))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            >
              <option value="low">💰 Budget - Hostels, street food, public transport</option>
              <option value="moderate">💰💰 Moderate - 3-star hotels, casual dining</option>
              <option value="high">💰💰💰 High - 4-star hotels, fine dining</option>
              <option value="luxury">💎 Luxury - 5-star resorts, premium experiences</option>
            </select>
          </div>

          {/* Travel Style */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Traveling With <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.traveling_with}
              onChange={(e) => setFormData(prev => ({ ...prev, traveling_with: e.target.value as any }))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            >
              <option value="solo">Solo</option>
              <option value="couple">Couple</option>
              <option value="family">Family with kids</option>
              <option value="group">Group of friends</option>
            </select>
          </div>

          {/* Interests */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Interests <span className="text-red-500">*</span> (Select all that apply)
            </label>
            <div className="flex flex-wrap gap-2">
              {INTERESTS_OPTIONS.map((interest) => (
                <button
                  key={interest}
                  type="button"
                  onClick={() => toggleInterest(interest)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    formData.interests?.includes(interest)
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {interest}
                </button>
              ))}
            </div>
            {formData.interests?.length === 0 && (
              <p className="text-xs text-red-500 mt-1">Please select at least one interest</p>
            )}
          </div>

          {/* Weather Preference */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Preferred Weather <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.weather_preference}
              onChange={(e) => setFormData(prev => ({ ...prev, weather_preference: e.target.value as any }))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            >
              <option value="hot">☀️ Hot (30°C+) - Beach weather</option>
              <option value="warm">🌤️ Warm (20-30°C) - Pleasant</option>
              <option value="mild">⛅ Mild (10-20°C) - Comfortable</option>
              <option value="cold">❄️ Cold (0-10°C) - Cozy</option>
              <option value="snow">🌨️ Snow (-5 to 5°C) - Winter sports</option>
            </select>
          </div>

          {/* Visa Preference */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Visa Preference <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.visa_preference}
              onChange={(e) => setFormData(prev => ({ ...prev, visa_preference: e.target.value as any }))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            >
              <option value="visa_free">✅ Visa-free only</option>
              <option value="visa_on_arrival">🛂 Visa on arrival OK</option>
              <option value="evisa_ok">📱 eVisa OK</option>
            </select>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isStarting || formData.interests?.length === 0}
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isStarting ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Starting Research...
              </span>
            ) : (
              '🚀 Start AI Research'
            )}
          </button>
        </form>
      )}

      {/* Progress Display */}
      {jobId && !results && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold">Research in Progress</h3>
              <p className="text-sm text-gray-600">Job ID: {jobId}</p>
            </div>
            <div className="text-right">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                jobStatus?.status === 'completed' ? 'bg-green-100 text-green-800' :
                jobStatus?.status === 'failed' ? 'bg-red-100 text-red-800' :
                jobStatus?.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {jobStatus?.status || 'pending'}
              </span>
            </div>
          </div>

          <ConnectionStatus />

          <div className="mt-4">
            <ProgressBar />
          </div>

          <div className="flex items-center justify-between text-sm text-gray-600 mt-2">
            <span>Current step: <strong className="capitalize">{jobStatus?.current_step?.replace(/_/g, ' ') || 'initializing'}</strong></span>
            <span>{jobStatus?.progress_percentage || 0}% complete</span>
          </div>

          {isResearching && (
            <div className="mt-4 flex items-center text-sm text-blue-600">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              AI is researching weather, visa requirements, attractions, flights, hotels...
            </div>
          )}

          <ActivityLog />

          <button
            onClick={clearResults}
            className="mt-6 text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Cancel and start over
          </button>
        </div>
      )}

      {/* Results Display */}
      {results && (
        <div className="space-y-6">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-green-800 mb-1">✅ Research Complete!</h3>
                <p className="text-green-700">
                  Found {results.destinations?.length || 0} destinations with full analysis
                </p>
              </div>
              <ConnectionStatus />
            </div>
          </div>

          {/* Top Recommendations */}
          <div>
            <h3 className="text-xl font-bold mb-4">Top Recommendations</h3>
            <div className="space-y-4">
              {results.recommendations?.map((rec) => (
                <div key={rec.rank} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded">
                          #{rec.rank}
                        </span>
                        <h4 className="text-lg font-semibold">{rec.destination}</h4>
                        <Link
                          href={`/city/${encodeURIComponent(rec.destination)}?origin=${encodeURIComponent(formData.origin || '')}&travel_start=${formData.travel_start || ''}&travel_end=${formData.travel_end || ''}&budget_level=${formData.budget_level || 'moderate'}&passport_country=${formData.passport_country || 'US'}`}
                          className="ml-auto text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 transition-colors"
                        >
                          View Details &rarr;
                        </Link>
                        <button
                          onClick={() => handleUsePlan(rec.destination)}
                          className={`text-sm px-3 py-1 rounded transition-colors ${
                            selectedPlan === rec.destination
                              ? 'bg-emerald-100 text-emerald-700'
                              : 'bg-emerald-600 text-white hover:bg-emerald-700'
                          }`}
                        >
                          {selectedPlan === rec.destination ? 'Selected' : 'Use this plan'}
                        </button>
                        <button
                          onClick={() => handleExport(rec)}
                          disabled={isExporting}
                          className="text-sm bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-900 disabled:opacity-60"
                        >
                          {isExporting ? 'Exporting...' : 'Export trip'}
                        </button>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-4 text-sm">
                        <span className="text-green-600 font-medium">
                          Score: {rec.score.toFixed(0)}/100
                        </span>
                        {rec.highlights?.flight_from && (
                          <span className="text-gray-600">
                            ✈️ Flights from ${rec.highlights.flight_from}
                          </span>
                        )}
                        {rec.highlights?.hotel_from && (
                          <span className="text-gray-600">
                            🏨 Hotels from ${rec.highlights.hotel_from}/night
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {rec.reasons && rec.reasons.length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">Why this?</p>
                      <ul className="text-sm text-gray-600 space-y-1">
                        {rec.reasons.map((reason, idx) => (
                          <li key={idx} className="flex items-center gap-2">
                            <span className="text-green-500">✓</span> {reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {getEvidenceChips(rec.destination).length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">Evidence</p>
                      <div className="flex flex-wrap gap-2">
                        {getEvidenceChips(rec.destination).map((chip, idx) => (
                          <span key={idx} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                            {chip}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {getDestinationResearch(rec.destination)?.data?.web_research && (
                    <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded">
                      <p className="text-sm font-medium text-amber-800">From the web</p>
                      <p className="text-xs text-amber-700 mt-1">
                        {Array.isArray(getDestinationResearch(rec.destination)?.data?.web_research?.sources)
                          ? `${getDestinationResearch(rec.destination)?.data?.web_research?.sources.length} sources were used during autonomous research.`
                          : 'External web research evidence was included for this destination.'}
                      </p>
                    </div>
                  )}

                  {rec.highlights?.top_attractions && (
                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">Top attractions:</p>
                      <div className="flex flex-wrap gap-2">
                        {rec.highlights.top_attractions.map((attraction, idx) => (
                          <span key={idx} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                            {attraction}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {rec.highlights?.top_events && rec.highlights.top_events.length > 0 && (
                    <div className="mt-2">
                      <p className="text-sm font-medium text-gray-700 mb-1">Events during your stay:</p>
                      <div className="flex flex-wrap gap-2">
                        {rec.highlights.top_events.map((event, idx) => (
                          <span key={idx} className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                            🎉 {event}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Comparison Table */}
          {results.comparison && results.comparison.destinations.length > 0 && (
            <div>
              <h3 className="text-xl font-bold mb-4">Comparison</h3>
              <div className="overflow-x-auto bg-white rounded-lg border border-gray-200">
                <table className="min-w-full">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Destination</th>
                      <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">Score</th>
                      <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">Visa</th>
                      <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">Attractions</th>
                      <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">Events</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {results.comparison.destinations.map((dest, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium">{dest.name}</td>
                        <td className="px-4 py-3 text-sm text-center">
                          <span className={`font-bold ${
                            dest.overall_score >= 80 ? 'text-green-600' :
                            dest.overall_score >= 60 ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {dest.overall_score.toFixed(0)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-center">
                          {dest.visa_required ? (
                            <span className="text-red-500 text-xs bg-red-50 px-2 py-1 rounded">Required</span>
                          ) : (
                            <span className="text-green-500 text-xs bg-green-50 px-2 py-1 rounded">Free</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-center">{dest.attractions_count}</td>
                        <td className="px-4 py-3 text-sm text-center">{dest.events_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Detailed Results */}
          <div>
            <h3 className="text-xl font-bold mb-4">Detailed Research</h3>
            <div className="space-y-4">
              {results.destinations?.map((dest, idx) => (
                <div key={idx} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold text-lg">{dest.name}</h4>
                    <div className="flex items-center gap-3">
                      {dest.overall_score && (
                        <span className="text-sm font-medium text-blue-600">
                          Score: {dest.overall_score.toFixed(0)}/100
                        </span>
                      )}
                      <Link
                        href={`/city/${encodeURIComponent(dest.name)}?origin=${encodeURIComponent(formData.origin || '')}&travel_start=${formData.travel_start || ''}&travel_end=${formData.travel_end || ''}&budget_level=${formData.budget_level || 'moderate'}&passport_country=${formData.passport_country || 'US'}`}
                        className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 transition-colors"
                      >
                        View Details →
                      </Link>
                    </div>
                  </div>
                  
                  {dest.error ? (
                    <p className="text-red-600 text-sm mt-2">Error: {dest.error}</p>
                  ) : (
                    <div className="mt-3 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 text-sm">
                      {dest.data?.weather && (
                        <div className="bg-white p-2 rounded">
                          <span className="text-gray-500 block text-xs">Weather</span>
                          <p className="font-medium">{dest.data.weather.temperature_c}°C, {dest.data.weather.condition}</p>
                        </div>
                      )}
                      {dest.data?.visa && (
                        <div className="bg-white p-2 rounded">
                          <span className="text-gray-500 block text-xs">Visa</span>
                          <p className="font-medium">
                            {dest.data.visa.visa_required ? 'Required' : 'Not Required'}
                          </p>
                        </div>
                      )}
                      {dest.data?.affordability && (
                        <div className="bg-white p-2 rounded">
                          <span className="text-gray-500 block text-xs">Budget Fit</span>
                          <p className="font-medium capitalize">{dest.data.affordability.budget_fit?.replace('_', ' ')}</p>
                        </div>
                      )}
                      {dest.data?.attractions && (
                        <div className="bg-white p-2 rounded">
                          <span className="text-gray-500 block text-xs">Attractions</span>
                          <p className="font-medium">{dest.data.attractions.length} found</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Start Over Button */}
          <button
            onClick={clearResults}
            className="w-full bg-gray-100 text-gray-700 py-3 px-6 rounded-lg font-semibold hover:bg-gray-200 transition-colors"
          >
            🔄 Start New Research
          </button>
        </div>
      )}
    </div>
  );
}

