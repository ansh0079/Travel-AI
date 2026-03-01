'use client';

import { motion } from 'framer-motion';
import { Bot, Sparkles, ClipboardList } from 'lucide-react';

import ConversationalSearch from '@/components/ConversationalSearch';
import AIAgentChat from '@/components/AIAgentChat';
import SmartQuestionnaire from '@/components/SmartQuestionnaire';
import { TravelRequest } from '@/types/travel';
import { TravelPreferences } from '@/services/api';

type TabType = 'assistant' | 'agent' | 'questionnaire';

interface HeroSectionProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  isLoading: boolean;
  isPolling: boolean;
  onSearch: (params: TravelRequest) => void;
  onQuestionnaireComplete: (prefs: TravelPreferences) => void;
}

const tabs = [
  {
    id: 'assistant' as TabType,
    label: 'Trip Planner',
    icon: Sparkles,
    activeColor: 'bg-primary-600',
  },
  {
    id: 'questionnaire' as TabType,
    label: 'Smart Form',
    icon: ClipboardList,
    activeColor: 'bg-emerald-600',
  },
  {
    id: 'agent' as TabType,
    label: 'AI Research Agent',
    icon: Bot,
    activeColor: 'bg-violet-600',
  },
];

export default function HeroSection({
  activeTab,
  setActiveTab,
  isLoading,
  isPolling,
  onSearch,
  onQuestionnaireComplete,
}: HeroSectionProps) {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 w-96 h-96 bg-primary-300/20 rounded-full blur-3xl animate-pulse-slow" />
        <div
          className="absolute -bottom-1/2 -right-1/4 w-96 h-96 bg-purple-300/20 rounded-full blur-3xl animate-pulse-slow"
          style={{ animationDelay: '1s' }}
        />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-radial from-primary-200/30 to-transparent rounded-full" />
      </div>

      <div className="relative z-10 w-full max-w-4xl mx-auto px-4">
        <motion.div
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
            <span className="gradient-text">Let&apos;s plan it together</span>
          </motion.h1>

          <motion.p
            className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            Tell me what you&apos;re looking for, and I&apos;ll find the perfect destinations
            tailored just for you.
          </motion.p>

          {/* Tab Selection */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex justify-center gap-2 mb-6 flex-wrap"
          >
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-medium transition-all ${
                  activeTab === tab.id
                    ? `${tab.activeColor} text-white shadow-lg`
                    : 'bg-white/80 text-gray-600 hover:bg-white'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </motion.div>

          {/* Chat Box */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="max-w-3xl mx-auto"
          >
            {activeTab === 'assistant' && (
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
                      <p className="text-white/70 text-sm">
                        Answer a few questions • Get personalized recommendations
                      </p>
                    </div>
                  </div>
                </div>
                <ConversationalSearch onSubmit={onSearch} isLoading={isLoading} />
              </motion.div>
            )}

            {activeTab === 'questionnaire' && (
              <motion.div
                key="questionnaire"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="bg-white rounded-3xl shadow-2xl p-4 md:p-6"
              >
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
                  onComplete={onQuestionnaireComplete}
                  onCancel={() => setActiveTab('assistant')}
                />
              </motion.div>
            )}

            {activeTab === 'agent' && (
              <motion.div key="agent" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                <AIAgentChat />
              </motion.div>
            )}
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
        </motion.div>
      </div>
    </section>
  );
}
