'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Sparkles, ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';

interface Suggestion {
  city: string;
  country: string;
  reason: string;
}

interface SmartSuggestionsProps {
  cities: string[];       // The recommended city names to base suggestions on
  origin?: string;
  travelStart?: string;
  travelEnd?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

export default function SmartSuggestions({
  cities,
  origin,
  travelStart,
  travelEnd,
}: SmartSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!cities || cities.length === 0) return;
    setLoading(true);
    const query = cities.slice(0, 3).join(',');
    fetch(`${API_BASE}/suggestions/similar?cities=${encodeURIComponent(query)}&limit=4`)
      .then((r) => r.json())
      .then((data) => setSuggestions(data.suggestions || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [cities.join(',')]);

  if (loading) {
    return (
      <div className="mt-10 max-w-6xl mx-auto">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5 text-violet-500 animate-pulse" />
          <h3 className="text-lg font-semibold text-gray-700">Finding hidden gems for you…</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-white rounded-2xl shadow animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!suggestions.length) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mt-10 max-w-6xl mx-auto"
    >
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-violet-500" />
        <h3 className="text-lg font-semibold text-gray-800">
          You might also love…
        </h3>
        <span className="text-sm text-gray-400">Based on your top picks</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {suggestions.map((s, i) => (
          <motion.div
            key={s.city}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <Link
              href={`/city/${encodeURIComponent(s.city.toLowerCase())}?origin=${encodeURIComponent(origin || '')}&travel_start=${encodeURIComponent(travelStart || '')}&travel_end=${encodeURIComponent(travelEnd || '')}`}
              className="block h-full bg-white rounded-2xl shadow-md hover:shadow-lg transition-shadow p-4 border border-gray-100 hover:border-violet-200 group"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="font-semibold text-gray-900 group-hover:text-violet-700 transition-colors">
                    {s.city}
                  </p>
                  <p className="text-xs text-gray-400">{s.country}</p>
                </div>
                <ExternalLink className="w-3.5 h-3.5 text-gray-300 group-hover:text-violet-400 transition-colors flex-shrink-0 mt-0.5" />
              </div>
              <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{s.reason}</p>
            </Link>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
