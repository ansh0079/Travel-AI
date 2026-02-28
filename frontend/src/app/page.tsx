'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ConversationalSearch from '@/components/ConversationalSearch';
import AIAgentChat from '@/components/AIAgentChat';
import DestinationCards from '@/components/DestinationCards';
import SmartSuggestions from '@/components/SmartSuggestions';
import SmartQuestionnaire from '@/components/SmartQuestionnaire';
import { useRecommendations } from '@/hooks/useRecommendations';
import { useAutoResearch } from '@/hooks/useAutoResearch';
import { TravelRequest } from '@/types/travel';
import { TravelPreferences } from '@/services/api';
import { Bot, Sparkles, Loader2, ClipboardList } from 'lucide-react';

type TabType = 'assistant' | 'agent' | 'questionnaire';

export default function Home() {
  const [searchParams, setSearchParams] = useState<TravelRequest | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('assistant');
  const { data, isLoading, error, fetchRecommendations } = useRecommendations();
  const { isPolling, startResearch, clearResults: clearResearch } = useAutoResearch();

  const handleSearch = async (params: TravelRequest) => {
    setSearchParams(params);
    setShowResults(true);
    // Fire recommendations and background web research in parallel
    fetchRecommendations(params);
    startResearch({
      origin: params.origin,
      travel_start: params.travel_start,
      travel_end: params.travel_end,
      budget_level: params.user_preferences.travel_style.toLowerCase() as any,
      interests: params.user_preferences.interests as string[],
      traveling_with: params.user_preferences.traveling_with as any,
      passport_country: params.user_preferences.passport_country,
      visa_preference: params.user_preferences.visa_preference as any,
    });
  };

  // Handler for SmartQuestionnaire — preferences map directly to agents
  const handleQuestionnaireComplete = (prefs: TravelPreferences) => {
    const BUDGET_MAP: Record<string, { daily: number; total: number }> = {
      low: { daily: 75, total: 1500 },
      moderate: { daily: 175, total: 3500 },
      high: { daily: 375, total: 7500 },
      luxury: { daily: 600, total: 12000 },
    };
    const budget = BUDGET_MAP[prefs.budget_level || 'moderate'];

    const travelRequest: TravelRequest = {
      origin: prefs.origin || '',
      travel_start: prefs.travel_start || '',
      travel_end: prefs.travel_end || '',
      num_travelers: prefs.has_kids ? (prefs.kids_count || 2) + 1 : 1,
      num_recommendations: 5,
      user_preferences: {
        budget_daily: budget.daily,
        budget_total: budget.total,
        travel_style: (prefs.budget_level as any) || 'moderate',
        interests: (prefs.interests || []) as any[],
        passport_country: prefs.passport_country || 'US',
        visa_preference: prefs.visa_preference || 'visa_free',
        traveling_with: (prefs.traveling_with || 'solo') as any,
        preferred_weather: prefs.weather_preference,
        accessibility_needs: prefs.accessibility_needs || [],
        dietary_restrictions: prefs.dietary_restrictions || [],
        max_flight_duration: prefs.max_flight_duration,
      },
    };

    setSearchParams(travelRequest);
    setShowResults(true);
    // Fire both: structured recommendations + deep agent online research
    fetchRecommendations(travelRequest);
    startResearch(prefs);
  };

  const handleStartOver = () => {
    setShowResults(false);
    setSearchParams(null);
    clearResearch();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-1/2 -left-1/4 w-96 h-96 bg-primary-300/20 rounded-full blur-3xl animate-pulse-slow" />
          <div className="absolute -bottom-1/2 -right-1/4 w-96 h-96 bg-purple-300/20 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-radial from-primary-200/30 to-transparent rounded-full" />

          {/* Floating destination photo cards — left side */}
          <div className="hidden lg:block absolute left-4 top-1/2 -translate-y-1/2 space-y-4 opacity-70 pointer-events-none select-none">
            {[
              { id: '1502602898657-3e91760cbb34', label: 'Paris', rotate: '-rotate-6' },
              { id: '1545569341-9eb8b30979d9', label: 'Kyoto', rotate: 'rotate-3' },
              { id: '1570077188670-e3a8d69ac5ff', label: 'Santorini', rotate: '-rotate-2' },
            ].map(({ id, label, rotate }) => (
              <div key={id} className={`relative w-36 h-24 rounded-2xl overflow-hidden shadow-2xl ${rotate} ring-4 ring-white/60`}>
                <img
                  src={`https://images.unsplash.com/photo-${id}?w=300&q=75&auto=format&fit=crop`}
                  alt={label}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
                <span className="absolute bottom-1.5 left-2 text-white text-xs font-semibold">{label}</span>
              </div>
            ))}
          </div>

          {/* Floating destination photo cards — right side */}
          <div className="hidden lg:block absolute right-4 top-1/2 -translate-y-1/2 space-y-4 opacity-70 pointer-events-none select-none">
            {[
              { id: '1537996194471-e657df975ab4', label: 'Bali', rotate: 'rotate-6' },
              { id: '1512453979798-5ea266f8880c', label: 'Dubai', rotate: '-rotate-3' },
              { id: '1573843981267-be1999ff37cd', label: 'Maldives', rotate: 'rotate-2' },
            ].map(({ id, label, rotate }) => (
              <div key={id} className={`relative w-36 h-24 rounded-2xl overflow-hidden shadow-2xl ${rotate} ring-4 ring-white/60`}>
                <img
                  src={`https://images.unsplash.com/photo-${id}?w=300&q=75&auto=format&fit=crop`}
                  alt={label}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
                <span className="absolute bottom-1.5 left-2 text-white text-xs font-semibold">{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 w-full max-w-4xl mx-auto px-4">
          <AnimatePresence mode="wait">
            {!showResults ? (
              <motion.div
                key="search"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, y: -50 }}
                className="text-center"
              >
                {/* Header */}
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8 }}
                >
                  <span className="inline-block px-4 py-2 rounded-full bg-primary-100 text-primary-700 text-sm font-medium mb-6">
                    ✨ AI-Powered Travel Planner
                  </span>
                </motion.div>

                <motion.h1
                  className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 leading-tight"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.1 }}
                >
                  Where to next?
                  <br />
                  <span className="gradient-text">Let's plan it together</span>
                </motion.h1>

                <motion.p
                  className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                >
                  Tell me what you're looking for, and I'll find the perfect destinations
                  tailored just for you.
                </motion.p>

                {/* Tab Selection */}
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  className="flex justify-center gap-2 mb-6 flex-wrap"
                >
                  <button
                    onClick={() => setActiveTab('assistant')}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium transition-all ${activeTab === 'assistant'
                        ? 'bg-primary-600 text-white shadow-lg'
                        : 'bg-white/80 text-gray-600 hover:bg-white'
                      }`}
                  >
                    <Sparkles className="w-4 h-4" />
                    Trip Planner
                  </button>
                  <button
                    onClick={() => setActiveTab('questionnaire')}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium transition-all ${activeTab === 'questionnaire'
                        ? 'bg-emerald-600 text-white shadow-lg'
                        : 'bg-white/80 text-gray-600 hover:bg-white'
                      }`}
                  >
                    <ClipboardList className="w-4 h-4" />
                    Smart Form
                  </button>
                  <button
                    onClick={() => setActiveTab('agent')}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium transition-all ${activeTab === 'agent'
                        ? 'bg-violet-600 text-white shadow-lg'
                        : 'bg-white/80 text-gray-600 hover:bg-white'
                      }`}
                  >
                    <Bot className="w-4 h-4" />
                    AI Research Agent
                  </button>
                </motion.div>

                {/* Chat Box */}
                <motion.div
                  initial={{ opacity: 0, y: 40 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                  className="max-w-3xl mx-auto"
                >
                  <AnimatePresence mode="wait">
                    {activeTab === 'assistant' ? (
                      <motion.div
                        key="assistant"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        className="bg-white rounded-3xl shadow-2xl overflow-hidden"
                      >
                        <div className="bg-gradient-to-r from-primary-600 to-purple-600 px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                              <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div className="text-left">
                              <h3 className="text-white font-semibold">TravelAI Trip Planner</h3>
                              <p className="text-white/70 text-sm">Answer a few questions • Get personalized recommendations</p>
                            </div>
                          </div>
                        </div>
                        <ConversationalSearch onSubmit={handleSearch} isLoading={isLoading} />
                      </motion.div>
                    ) : activeTab === 'questionnaire' ? (
                      <motion.div
                        key="questionnaire"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        className="bg-white rounded-3xl shadow-2xl p-4 md:p-6"
                      >
                        {/* Header */}
                        <div className="bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl px-6 py-4 mb-6">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                              <ClipboardList className="w-5 h-5 text-white" />
                            </div>
                            <div className="text-left">
                              <h3 className="text-white font-semibold">Smart Travel Form</h3>
                              <p className="text-white/70 text-sm">Step-by-step questions • Adapts to your answers</p>
                            </div>
                          </div>
                        </div>
                        <SmartQuestionnaire
                          onComplete={handleQuestionnaireComplete}
                          onCancel={() => setActiveTab('assistant')}
                        />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="agent"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                      >
                        <AIAgentChat />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>

                {/* Trust badges */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 }}
                  className="mt-12 flex flex-wrap justify-center gap-6 text-sm text-gray-500"
                >
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    Free to use
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    No sign-up required
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    Personalized results
                  </span>
                </motion.div>

                {/* Popular destinations photo strip */}
                <motion.div
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.1 }}
                  className="mt-8"
                >
                  <p className="text-xs text-gray-400 uppercase tracking-widest mb-3">Popular destinations</p>
                  <div className="flex gap-3 justify-center flex-wrap">
                    {[
                      { id: '1502602898657-3e91760cbb34', label: 'Paris' },
                      { id: '1540959733332-eab4deabeeaf', label: 'Tokyo' },
                      { id: '1537996194471-e657df975ab4', label: 'Bali' },
                      { id: '1570077188670-e3a8d69ac5ff', label: 'Santorini' },
                      { id: '1512453979798-5ea266f8880c', label: 'Dubai' },
                      { id: '1573843981267-be1999ff37cd', label: 'Maldives' },
                    ].map(({ id, label }) => (
                      <div
                        key={id}
                        className="relative w-16 h-16 md:w-20 md:h-20 rounded-2xl overflow-hidden shadow-lg ring-2 ring-white/80 cursor-default group"
                      >
                        <img
                          src={`https://images.unsplash.com/photo-${id}?w=200&q=80&auto=format&fit=crop`}
                          alt={label}
                          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                        <span className="absolute bottom-1 left-0 right-0 text-center text-white text-[9px] md:text-[10px] font-semibold leading-tight">{label}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              </motion.div>
            ) : (
              <motion.div
                key="results"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="w-full"
              >
                {/* Results Header */}
                <div className="text-center mb-8">
                  <motion.h2
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-4xl font-bold text-gray-900 mb-4"
                  >
                    {isLoading ? 'Finding your perfect trip...' : 'Your Personalized Destinations'}
                  </motion.h2>
                  <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="text-gray-600"
                  >
                    {searchParams && (
                      <span>
                        From <strong>{searchParams.origin}</strong> •{' '}
                        <strong>{searchParams.num_travelers}</strong> traveler{searchParams.num_travelers > 1 ? 's' : ''} •{' '}
                        <strong>{searchParams.user_preferences.travel_style}</strong> style
                      </span>
                    )}
                  </motion.p>
                  {isPolling && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="inline-flex items-center gap-2 mt-3 px-4 py-1.5 bg-violet-50 border border-violet-200 rounded-full text-sm text-violet-700"
                    >
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Agents researching destinations in the background…
                    </motion.div>
                  )}
                </div>

                {/* Loading State */}
                {isLoading && (
                  <div className="max-w-6xl mx-auto">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                      {[1, 2, 3].map((i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 20 }}
                          transition={{ delay: i * 0.1 }}
                          className="bg-white rounded-2xl shadow-lg p-6 animate-pulse"
                        >
                          <div className="h-48 bg-gray-200 rounded-xl mb-4" />
                          <div className="h-6 bg-gray-200 rounded w-3/4 mb-2" />
                          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
                          <div className="h-4 bg-gray-200 rounded w-full" />
                        </motion.div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Error State */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="max-w-xl mx-auto bg-red-50 border border-red-200 rounded-2xl p-8 text-center"
                  >
                    <div className="text-4xl mb-4">😕</div>
                    <h3 className="font-bold text-red-700 mb-2 text-lg">Something went wrong</h3>
                    <p className="text-red-600">{error.message}</p>
                    <button
                      onClick={handleStartOver}
                      className="mt-4 px-6 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                    >
                      Try Again
                    </button>
                  </motion.div>
                )}

                {/* Results */}
                {data && data.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="max-w-6xl mx-auto"
                  >
                    <DestinationCards
                      destinations={data}
                      origin={searchParams?.origin}
                      travelStart={searchParams?.travel_start}
                      travelEnd={searchParams?.travel_end}
                    />

                    {/* Smart Suggestions */}
                    <SmartSuggestions
                      cities={data.map((d) => d.city || d.name)}
                      origin={searchParams?.origin}
                      travelStart={searchParams?.travel_start}
                      travelEnd={searchParams?.travel_end}
                    />

                    {/* Start Over Button */}
                    <div className="text-center mt-12">
                      <button
                        onClick={handleStartOver}
                        className="px-8 py-3 bg-white text-gray-700 rounded-xl shadow-lg hover:shadow-xl transition-shadow"
                      >
                        🔄 Plan Another Trip
                      </button>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>

      {/* Features Section - Only show when not in results */}
      {!showResults && (
        <section className="max-w-6xl mx-auto px-4 py-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Our AI analyzes thousands of destinations to find your perfect match
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: '1',
                icon: '💬',
                title: 'Tell Us Your Preferences',
                description: 'Answer a few quick questions about your ideal trip - duration, budget, interests, and more.',
              },
              {
                step: '2',
                icon: '🤖',
                title: 'AI Analysis',
                description: 'Our AI analyzes weather, affordability, visa requirements, attractions, and events in real-time.',
              },
              {
                step: '3',
                icon: '✈️',
                title: 'Get Recommendations',
                description: 'Receive personalized destination recommendations with detailed insights for each location.',
              },
            ].map((feature, i) => (
              <motion.div
                key={i}
                className="bg-white rounded-2xl shadow-lg p-8 text-center relative"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                viewport={{ once: true }}
              >
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold text-sm">
                  {feature.step}
                </div>
                <div className="text-5xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-bold mb-3 text-gray-900">{feature.title}</h3>
                <p className="text-gray-600 leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-16">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-2xl font-bold mb-4">TravelAI</h3>
              <p className="text-gray-400">
                Your AI-powered travel companion for discovering the perfect destinations.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Features</h4>
              <ul className="space-y-2 text-gray-400">
                <li>AI Recommendations</li>
                <li>Weather Forecasts</li>
                <li>Visa Information</li>
                <li>Cost Analysis</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Destinations</h4>
              <ul className="space-y-2 text-gray-400">
                <li>Europe</li>
                <li>Asia</li>
                <li>Americas</li>
                <li>Africa & Middle East</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Connect</h4>
              <ul className="space-y-2 text-gray-400">
                <li>About Us</li>
                <li>Contact</li>
                <li>Privacy Policy</li>
                <li>Terms of Service</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-12 pt-8 text-center text-gray-500">
            © 2024 TravelAI. All rights reserved.
          </div>
        </div>
      </footer>
    </main>
  );
}
