'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Sparkles, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { TravelPreferences } from '@/services/api';
import ErrorBoundary from '@/components/ErrorBoundary';

// Dynamically import chat component with loading fallback
const UltraModernChat = dynamic(() => import('@/components/UltraModernChat'), {
  loading: () => (
    <div className="flex items-center justify-center py-12">
      <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
      <span className="ml-3 text-gray-400">Loading chat...</span>
    </div>
  ),
  ssr: false,
});

export default function ChatPage() {
  const [currentStep, setCurrentStep] = useState<'chat' | 'results'>('chat');
  const [preferences, setPreferences] = useState<TravelPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate initial load check
    const timer = setTimeout(() => setIsLoading(false), 500);
    return () => clearTimeout(timer);
  }, []);

  const handleChatComplete = (prefs: TravelPreferences) => {
    setPreferences(prefs);
    setCurrentStep('results');
    console.log('Preferences:', prefs);
  };

  return (
    <main className="min-h-screen bg-[#0a0a19] relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        {/* Mesh Gradient */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500/30 rounded-full blur-3xl animate-float" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/30 rounded-full blur-3xl animate-float-delayed" />
          <div className="absolute top-1/2 left-1/2 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-float-slow" />
        </div>

        {/* Grid Pattern */}
        <div 
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                             linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
            backgroundSize: '50px 50px',
          }}
        />
      </div>

      {/* Navigation */}
      <motion.nav 
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="fixed top-0 left-0 right-0 z-50 px-4 py-4"
      >
        <div className="max-w-7xl mx-auto">
          <div className="glass rounded-full px-6 py-4 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 text-white hover:text-emerald-400 transition-colors">
              <ArrowLeft className="w-5 h-5" />
              <span className="font-medium">Back to Home</span>
            </Link>
            
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl gradient-aurora flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold hidden sm:inline">TravelAI</span>
            </div>

            <div className="w-24" /> {/* Spacer for centering */}
          </div>
        </div>
      </motion.nav>

      {/* Main Content */}
      <div className="pt-24 pb-12 px-4 min-h-screen flex items-center justify-center">
        <div className="w-full max-w-5xl">
          {isLoading ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-12"
            >
              <RefreshCw className="w-12 h-12 animate-spin text-emerald-400 mx-auto mb-4" />
              <p className="text-gray-400">Loading chat interface...</p>
            </motion.div>
          ) : currentStep === 'chat' ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
            >
              <div className="text-center mb-8">
                <h1 className="text-4xl sm:text-5xl font-bold mb-4">
                  Plan Your <span className="text-gradient">Perfect Trip</span>
                </h1>
                <p className="text-xl text-gray-400">
                  Chat with our AI to create your personalized itinerary
                </p>
              </div>

              <ErrorBoundary>
                <UltraModernChat onComplete={handleChatComplete} />
              </ErrorBoundary>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="text-center"
            >
              <div className="glass-panel max-w-2xl mx-auto">
                <div className="w-20 h-20 mx-auto mb-6 rounded-3xl gradient-aurora flex items-center justify-center">
                  <Sparkles className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-3xl font-bold mb-4">Ready to Explore!</h2>
                <p className="text-gray-400 mb-8">
                  Based on your preferences, we're generating personalized recommendations...
                </p>
                <div className="flex flex-wrap justify-center gap-3 mb-8">
                  {preferences?.destinations?.map((dest, i) => (
                    <span key={i} className="px-4 py-2 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      {dest}
                    </span>
                  ))}
                  {preferences?.budget_level && (
                    <span className="px-4 py-2 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      {preferences.budget_level}
                    </span>
                  )}
                  {preferences?.travel_start && (
                    <span className="px-4 py-2 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      {preferences.travel_start}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setCurrentStep('chat')}
                  className="btn-primary"
                >
                  Back to Chat
                </button>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </main>
  );
}
