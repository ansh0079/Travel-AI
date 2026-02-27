'use client';

import { useState, useCallback } from 'react';
import { api, TravelGenieResult } from '@/services/api';

interface UseTravelGenieReturn {
  data: TravelGenieResult | null;
  isLoading: boolean;
  error: Error | null;
  fetch: (origin: string, destination: string, travelDate: string, returnDate?: string) => Promise<void>;
  clear: () => void;
}

export function useTravelGenie(): UseTravelGenieReturn {
  const [data, setData] = useState<TravelGenieResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetch = useCallback(async (
    origin: string,
    destination: string,
    travelDate: string,
    returnDate?: string
  ) => {
    setIsLoading(true);
    setData(null);
    setError(null);
    try {
      const result = await api.travelGenieCompleteInfo(origin, destination, travelDate, returnDate);
      setData(result);
    } catch (err: any) {
      setError(new Error(err?.response?.data?.detail || err?.message || 'Agent research failed'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { data, isLoading, error, fetch, clear };
}
