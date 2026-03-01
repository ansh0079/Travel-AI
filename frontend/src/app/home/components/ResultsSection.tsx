'use client';

import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

import DestinationCards from '@/components/DestinationCards';
import { Destination } from '@/types/travel';

interface ResultsSectionProps {
  searchParams: {
    origin: string;
    num_travelers: number;
    user_preferences: {
      travel_style: string;
    };
  } | null;
  isLoading: boolean;
  isPolling: boolean;
  error: Error | null;
  data: Destination[] | null;
  travelStart?: string;
  travelEnd?: string;
  onStartOver: () => void;
}

export default function ResultsSection({
  searchParams,
  isLoading,
  isPolling,
  error,
  data,
  travelStart,
  travelEnd,
  onStartOver,
}: ResultsSectionProps) {
  return (
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
              <strong>{searchParams.num_travelers}</strong> traveler
              {searchParams.num_travelers > 1 ? 's' : ''} •{' '}
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
            onClick={onStartOver}
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
            travelStart={travelStart}
            travelEnd={travelEnd}
          />

          {/* Start Over Button */}
          <div className="text-center mt-12">
            <button
              onClick={onStartOver}
              className="px-8 py-3 bg-white text-gray-700 rounded-xl shadow-lg hover:shadow-xl transition-shadow"
            >
              🔄 Plan Another Trip
            </button>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
