'use client';

import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';

import HeroSection from './home/components/HeroSection';
import ResultsSection from './home/components/ResultsSection';
import FeaturesSection from './home/components/FeaturesSection';
import FooterSection from './home/components/FooterSection';

import { useRecommendations } from '@/hooks/useRecommendations';
import { useAutoResearch } from '@/hooks/useAutoResearch';
import { TravelRequest } from '@/types/travel';
import { TravelPreferences } from '@/services/api';

type TabType = 'assistant' | 'agent' | 'questionnaire' | 'natural' | 'planning-agent';

export default function Home() {
  const [searchParams, setSearchParams] = useState<TravelRequest | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('planning-agent');
  const { data, isLoading, error, fetchRecommendations } = useRecommendations();
  const { isPolling, startResearch, clearResults: clearResearch } = useAutoResearch();

  const handleSearch = async (params: TravelRequest) => {
    setSearchParams(params);
    setShowResults(true);
    fetchRecommendations(params);
    startResearch({
      origin: params.origin,
      travel_start: params.travel_start,
      travel_end: params.travel_end,
      budget_level: params.user_preferences.travel_style.toLowerCase() as 'low' | 'moderate' | 'high' | 'luxury',
      interests: params.user_preferences.interests as string[],
      traveling_with: params.user_preferences.traveling_with as 'solo' | 'couple' | 'family' | 'friends',
      passport_country: params.user_preferences.passport_country,
      visa_preference: params.user_preferences.visa_preference as 'visa_free' | 'visa_on_arrival' | 'evisa_ok',
    });
  };

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
        travel_style: (prefs.budget_level as 'budget' | 'moderate' | 'comfort' | 'luxury') || 'moderate',
        interests: (prefs.interests || []) as import('@/types/travel').Interest[],
        passport_country: prefs.passport_country || 'US',
        visa_preference: prefs.visa_preference || 'visa_free',
        traveling_with: (prefs.traveling_with as 'solo' | 'couple' | 'family' | 'friends') || 'solo',
        preferred_weather: prefs.weather_preference,
        accessibility_needs: prefs.accessibility_needs || [],
        dietary_restrictions: prefs.dietary_restrictions || [],
        max_flight_duration: prefs.max_flight_duration,
      },
    };

    setSearchParams(travelRequest);
    setShowResults(true);
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
      <AnimatePresence mode="wait">
        {!showResults ? (
          <HeroSection
            key="hero"
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            isLoading={isLoading}
            isPolling={isPolling}
            onSearch={handleSearch}
            onQuestionnaireComplete={handleQuestionnaireComplete}
          />
        ) : (
          <section className="relative min-h-screen flex items-center justify-center overflow-hidden py-12">
            <ResultsSection
              searchParams={searchParams}
              isLoading={isLoading}
              isPolling={isPolling}
              error={error}
              data={data}
              travelStart={searchParams?.travel_start}
              travelEnd={searchParams?.travel_end}
              onStartOver={handleStartOver}
            />
          </section>
        )}
      </AnimatePresence>

      {!showResults && (
        <>
          <FeaturesSection />
          <FooterSection />
        </>
      )}
    </main>
  );
}
