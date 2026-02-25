"use client";

import { useState } from "react";
import { useResearch } from "@/hooks/useResearch";
import { Wifi, WifiOff, AlertCircle, CheckCircle, Loader2, X } from "lucide-react";

interface ResearchFormData {
  origin: string;
  travel_start: string;
  travel_end: string;
  budget_level: string;
  interests: string[];
  traveling_with: string;
  weather_preference: string;
  // New fields
  has_kids: boolean;
  kids_count: number;
  kids_ages: string[];
  trip_type: string;
  accessibility_needs: string[];
  dietary_restrictions: string[];
  flight_duration_max: number;
  pace_preference: string;
}

const INTERESTS_OPTIONS = [
  "beach",
  "mountain",
  "city",
  "history",
  "nature",
  "adventure",
  "food",
  "culture",
  "relaxation",
  "nightlife",
];

export function ResearchDashboard() {
  const {
    status,
    progress,
    currentStep,
    results,
    error,
    messages,
    isConnected,
    connectionError,
    startResearch,
    cancelResearch,
  } = useResearch();

  const [formData, setFormData] = useState<ResearchFormData>({
    origin: "",
    travel_start: "",
    travel_end: "",
    budget_level: "moderate",
    interests: [],
    traveling_with: "solo",
    weather_preference: "warm",
    // New fields
    has_kids: false,
    kids_count: 0,
    kids_ages: [],
    trip_type: "leisure",
    accessibility_needs: [],
    dietary_restrictions: [],
    flight_duration_max: 12,
    pace_preference: "moderate",
  });

  const toggleInterest = (interest: string) => {
    setFormData((prev) => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter((i) => i !== interest)
        : [...prev.interests, interest],
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.interests.length === 0) {
      alert("Please select at least one interest");
      return;
    }
    await startResearch(formData);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header Card */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Travel Research</h2>
              <p className="text-gray-500 mt-1">
                Let our AI find the perfect destinations for you
              </p>
            </div>
            <div className="flex items-center gap-2">
              {isConnected ? (
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                  <Wifi className="w-4 h-4" />
                  Live
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                  <WifiOff className="w-4 h-4" />
                  Disconnected
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="p-6">
          {/* Idle State - Show Form */}
          {status === "idle" && (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Origin */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Where are you traveling from? <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.origin}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, origin: e.target.value }))
                  }
                  placeholder="e.g., London, New York, Tokyo"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
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
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        travel_start: e.target.value,
                      }))
                    }
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
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        travel_end: e.target.value,
                      }))
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>
              </div>

              {/* Budget Level */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Budget Level <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.budget_level}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      budget_level: e.target.value,
                    }))
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="low">💰 Budget - Hostels, street food</option>
                  <option value="moderate">💰💰 Moderate - 3-star hotels</option>
                  <option value="high">💰💰💰 High - 4-star hotels</option>
                  <option value="luxury">💎 Luxury - 5-star resorts</option>
                </select>
              </div>

              {/* Traveling With */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Traveling With <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.traveling_with}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      traveling_with: e.target.value,
                    }))
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="solo">Solo</option>
                  <option value="couple">Couple</option>
                  <option value="family">Family with kids</option>
                  <option value="group">Group of friends</option>
                </select>
              </div>

              {/* Kids Details - Only show if traveling with family */}
              {formData.traveling_with === "family" && (
                <>
                  {/* Has Kids */}
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="has_kids"
                      checked={formData.has_kids}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          has_kids: e.target.checked,
                          kids_count: e.target.checked ? 1 : 0,
                        }))
                      }
                      className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <label htmlFor="has_kids" className="text-sm font-medium text-gray-700">
                      Traveling with children
                    </label>
                  </div>

                  {/* Number of Kids */}
                  {formData.has_kids && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Number of children
                      </label>
                      <select
                        value={formData.kids_count}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            kids_count: parseInt(e.target.value),
                          }))
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value={1}>1 child</option>
                        <option value={2}>2 children</option>
                        <option value={3}>3 children</option>
                        <option value={4}>4+ children</option>
                      </select>
                    </div>
                  )}

                  {/* Kids Ages */}
                  {formData.has_kids && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Children&apos;s age ranges (Select all that apply)
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {["0-2 (Infant)", "3-5 (Toddler)", "6-12 (Child)", "13-17 (Teen)"].map((age) => (
                          <button
                            key={age}
                            type="button"
                            onClick={() => {
                              setFormData((prev) => ({
                                ...prev,
                                kids_ages: prev.kids_ages.includes(age)
                                  ? prev.kids_ages.filter((a) => a !== age)
                                  : [...prev.kids_ages, age],
                              }));
                            }}
                            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                              formData.kids_ages.includes(age)
                                ? "bg-blue-600 text-white"
                                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                            }`}
                          >
                            {age}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Trip Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Trip Type <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.trip_type}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      trip_type: e.target.value,
                    }))
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Trip Pace <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.pace_preference}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      pace_preference: e.target.value,
                    }))
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="relaxed">😌 Relaxed - Sleep in, few activities</option>
                  <option value="moderate">⚖️ Moderate - Balance of activities & rest</option>
                  <option value="busy">🏃 Busy - Pack in as much as possible</option>
                </select>
              </div>

              {/* Max Flight Duration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Maximum Flight Duration
                </label>
                <select
                  value={formData.flight_duration_max}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      flight_duration_max: parseInt(e.target.value),
                    }))
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value={3}>✈️ Up to 3 hours (Short haul)</option>
                  <option value={6}>✈️ Up to 6 hours (Medium haul)</option>
                  <option value={12}>✈️ Up to 12 hours (Long haul)</option>
                  <option value={20}>✈️ Any duration (Worldwide)</option>
                </select>
              </div>

              {/* Accessibility Needs */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Accessibility Needs (Optional)
                </label>
                <div className="flex flex-wrap gap-2">
                  {["Wheelchair accessible", "Stroller friendly", "Elevator access", "Ground floor rooms", "Quiet environment"].map((need) => (
                    <button
                      key={need}
                      type="button"
                      onClick={() => {
                        setFormData((prev) => ({
                          ...prev,
                          accessibility_needs: prev.accessibility_needs.includes(need)
                            ? prev.accessibility_needs.filter((n) => n !== need)
                            : [...prev.accessibility_needs, need],
                        }));
                      }}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                        formData.accessibility_needs.includes(need)
                          ? "bg-purple-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {need}
                    </button>
                  ))}
                </div>
              </div>

              {/* Dietary Restrictions */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dietary Requirements (Optional)
                </label>
                <div className="flex flex-wrap gap-2">
                  {["Vegetarian", "Vegan", "Halal", "Kosher", "Gluten-free", "Nut allergies", "Dairy-free"].map((diet) => (
                    <button
                      key={diet}
                      type="button"
                      onClick={() => {
                        setFormData((prev) => ({
                          ...prev,
                          dietary_restrictions: prev.dietary_restrictions.includes(diet)
                            ? prev.dietary_restrictions.filter((d) => d !== diet)
                            : [...prev.dietary_restrictions, diet],
                        }));
                      }}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                        formData.dietary_restrictions.includes(diet)
                          ? "bg-green-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {diet}
                    </button>
                  ))}
                </div>
              </div>

              {/* Weather Preference */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Preferred Weather <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.weather_preference}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      weather_preference: e.target.value,
                    }))
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="hot">☀️ Hot (30°C+) - Beach weather</option>
                  <option value="warm">🌤️ Warm (20-30°C) - Pleasant</option>
                  <option value="mild">⛅ Mild (10-20°C) - Comfortable</option>
                  <option value="cold">❄️ Cold (0-10°C) - Cozy</option>
                  <option value="snow">🌨️ Snow (-5 to 5°C) - Winter sports</option>
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
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                        formData.interests.includes(interest)
                          ? "bg-blue-600 text-white"
                          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      }`}
                    >
                      {interest.charAt(0).toUpperCase() + interest.slice(1)}
                    </button>
                  ))}
                </div>
                {formData.interests.length === 0 && (
                  <p className="text-sm text-red-500 mt-2">
                    Please select at least one interest
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={formData.interests.length === 0}
                className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                🚀 Start AI Research
              </button>
            </form>
          )}

          {/* Researching State - Show Progress */}
          {status === "researching" && (
            <div className="space-y-6">
              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">Research Progress</span>
                  <span className="text-blue-600 font-bold">{progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-sm text-gray-500">
                  {currentStep || "Initializing..."}
                </p>
              </div>

              {/* Activity Log */}
              <div className="border rounded-lg p-4 bg-gray-50 h-64 overflow-y-auto">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Activity Log</h4>
                <div className="space-y-2">
                  {messages.map((msg, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      {msg.type === "error" && (
                        <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                      )}
                      {msg.type === "success" && (
                        <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                      )}
                      {msg.type === "step" && (
                        <Loader2 className="w-4 h-4 text-blue-500 animate-spin mt-0.5 flex-shrink-0" />
                      )}
                      {msg.type === "info" && (
                        <div className="w-4 h-4 rounded-full bg-blue-200 mt-0.5 flex-shrink-0" />
                      )}
                      <div className="min-w-0">
                        <span className="text-xs text-gray-400">
                          {msg.timestamp.toLocaleTimeString()}
                        </span>
                        <p className="text-gray-700">{msg.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Connection Error */}
              {connectionError && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-sm text-yellow-800">
                    ⚠️ Connection lost. Auto-reconnecting...
                  </p>
                </div>
              )}

              {/* Cancel Button */}
              <div className="flex justify-end">
                <button
                  onClick={cancelResearch}
                  className="bg-red-50 text-red-600 px-4 py-2 rounded-lg font-medium hover:bg-red-100 transition-colors flex items-center gap-2"
                >
                  <X className="w-4 h-4" />
                  Cancel Research
                </button>
              </div>
            </div>
          )}

          {/* Completed State - Show Results */}
          {status === "completed" && results && (
            <div className="space-y-6">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <h3 className="text-lg font-semibold text-green-800">
                    Research Complete!
                  </h3>
                </div>
                <p className="text-green-700 mt-1">
                  Found {results.destinations?.length || 0} destinations with full analysis
                </p>
              </div>

              {/* Recommendations */}
              {results.recommendations?.length > 0 && (
                <div>
                  <h3 className="text-xl font-bold mb-4">Top Recommendations</h3>
                  <div className="space-y-4">
                    {results.recommendations.map((rec: any) => (
                      <div
                        key={rec.rank}
                        className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-3">
                            <span className="bg-blue-100 text-blue-800 text-sm font-bold px-2 py-1 rounded">
                              #{rec.rank}
                            </span>
                            <h4 className="text-lg font-semibold">{rec.destination}</h4>
                          </div>
                          <span className="text-green-600 font-bold">
                            Score: {rec.score}/100
                          </span>
                        </div>

                        {rec.reasons?.length > 0 && (
                          <div className="mt-3">
                            <p className="text-sm font-medium text-gray-700 mb-1">
                              Why we recommend it:
                            </p>
                            <ul className="text-sm text-gray-600 space-y-1">
                              {rec.reasons.map((reason: string, idx: number) => (
                                <li key={idx} className="flex items-center gap-2">
                                  <span className="text-green-500">✓</span> {reason}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="mt-3 flex gap-4 text-sm text-gray-500">
                          {rec.highlights?.flight_from && (
                            <span>✈️ Flights from ${rec.highlights.flight_from}</span>
                          )}
                          {rec.highlights?.hotel_from && (
                            <span>🏨 Hotels from ${rec.highlights.hotel_from}/night</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Start Over Button */}
              <button
                onClick={cancelResearch}
                className="w-full bg-gray-100 text-gray-700 py-3 px-6 rounded-lg font-semibold hover:bg-gray-200 transition-colors"
              >
                🔄 Start New Research
              </button>
            </div>
          )}

          {/* Error State */}
          {status === "error" && (
            <div className="space-y-4">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <h3 className="text-lg font-semibold text-red-800">Research Failed</h3>
                </div>
                <p className="text-red-700 mt-1">{error || "An unknown error occurred"}</p>
              </div>

              <button
                onClick={cancelResearch}
                className="w-full bg-gray-100 text-gray-700 py-3 px-6 rounded-lg font-semibold hover:bg-gray-200 transition-colors"
              >
                🔄 Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
