'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { api, TravelPreferences, ResearchJob, ResearchResults } from '@/services/api';

interface UseAutoResearchReturn {
  // Job state
  jobId: string | null;
  jobStatus: ResearchJob | null;
  results: ResearchResults | null;
  
  // Loading states
  isStarting: boolean;
  isPolling: boolean;
  
  // Errors
  error: Error | null;
  
  // Actions
  startResearch: (preferences: TravelPreferences) => Promise<void>;
  checkStatus: (jobId: string) => Promise<ResearchJob | null>;
  fetchResults: (jobId: string) => Promise<ResearchResults | null>;
  clearResults: () => void;
  
  // Polling control
  stopPolling: () => void;
  startPolling: (jobId: string, interval?: number) => void;
}

export function useAutoResearch(): UseAutoResearchReturn {
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<ResearchJob | null>(null);
  const [results, setResults] = useState<ResearchResults | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const startResearch = useCallback(async (preferences: TravelPreferences) => {
    setIsStarting(true);
    setError(null);
    setResults(null);
    
    try {
      const job = await api.startAutoResearch(preferences);
      setJobId(job.job_id);
      setJobStatus(job);
      
      // Automatically start polling
      startPolling(job.job_id);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to start research'));
    } finally {
      setIsStarting(false);
    }
  }, []);

  const checkStatus = useCallback(async (id: string) => {
    try {
      const status = await api.getResearchStatus(id);
      setJobStatus(status);
      return status;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to check status'));
      return null;
    }
  }, []);

  const fetchResults = useCallback(async (id: string) => {
    try {
      const researchResults = await api.getResearchResults(id);
      setResults(researchResults);
      return researchResults;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch results'));
      return null;
    }
  }, []);

  const clearResults = useCallback(() => {
    setJobId(null);
    setJobStatus(null);
    setResults(null);
    setError(null);
    stopPolling();
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const startPolling = useCallback((id: string, interval: number = 2000) => {
    // Clear any existing polling
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    
    setIsPolling(true);
    
    pollingRef.current = setInterval(async () => {
      try {
        const status = await api.getResearchStatus(id);
        setJobStatus(status);
        
        // Stop polling if completed or failed
        if (status.status === 'completed' || status.status === 'failed') {
          stopPolling();
          
          // Auto-fetch results if completed
          if (status.status === 'completed' && status.results_available) {
            await fetchResults(id);
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
        // Don't stop polling on error, might be temporary
      }
    }, interval);
  }, [fetchResults, stopPolling]);

  return {
    jobId,
    jobStatus,
    results,
    isStarting,
    isPolling,
    error,
    startResearch,
    checkStatus,
    fetchResults,
    clearResults,
    stopPolling,
    startPolling,
  };
}
