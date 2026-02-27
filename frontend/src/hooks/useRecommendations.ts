'use client';

import { useState, useCallback } from 'react';
import { api } from '@/services/api';
import { TravelRequest, Destination } from '@/types/travel';

interface UseRecommendationsReturn {
  data: Destination[] | null;
  isLoading: boolean;
  error: Error | null;
  fetchRecommendations: (request: TravelRequest) => Promise<void>;
  clearResults: () => void;
}

export function useRecommendations(): UseRecommendationsReturn {
  const [data, setData] = useState<Destination[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchRecommendations = useCallback(async (request: TravelRequest) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const results = await api.getRecommendations(request);
      setData(results);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to fetch recommendations';
      setError(new Error(detail));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return {
    data,
    isLoading,
    error,
    fetchRecommendations,
    clearResults,
  };
}