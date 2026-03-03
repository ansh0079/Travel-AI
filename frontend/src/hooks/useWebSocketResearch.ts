'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { api, TravelPreferences, ResearchJob, ResearchResults } from '@/services/api';

interface UseWebSocketResearchReturn {
  jobId: string | null;
  jobStatus: ResearchJob | null;
  results: ResearchResults | null;
  isConnected: boolean;
  isStarting: boolean;
  isResearching: boolean;
  lastMessage: WebSocketMessage | null;
  messages: WebSocketMessage[];
  error: Error | null;
  connectionError: string | null;
  startResearch(_preferences: TravelPreferences): Promise<void>;
  fetchResults(_jobId: string): Promise<ResearchResults | null>;
  clearResults(): void;
  reconnect(): void;
  disconnect(): void;
  sendMessage(_message: any): void;
}

interface WebSocketMessage {
  type: 'connected' | 'started' | 'progress' | 'completed' | 'error' | 'pong' | 'ack';
  job_id?: string;
  step?: string;
  percentage?: number;
  message?: string;
  error?: string;
  results_summary?: any;
  timestamp?: number;
}

// WebSocket base — must NOT include /api/v1; the ws route is at /ws/research/{id}
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://travel-ai-backend-vwwk.onrender.com';

export function useWebSocketResearch(): UseWebSocketResearchReturn {
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<ResearchJob | null>(null);
  const [results, setResults] = useState<ResearchResults | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [isResearching, setIsResearching] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const wsFailedRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    stopPolling();
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    setIsConnected(false);
  }, [stopPolling]);

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

  const connectWebSocket = useCallback((id: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `${WS_BASE_URL}/ws/research/${id}`;
    console.log('Connecting to WebSocket:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(data);
          setMessages((prev) => [...prev, { ...data, timestamp: Date.now() }]);

          if (data.type === 'started') setIsResearching(true);
          if (data.type === 'started') {
            setJobStatus((prev) =>
              prev
                ? { ...prev, status: 'in_progress', current_step: data.step || 'initializing' }
                : prev
            );
          }
          if (data.type === 'progress') {
            setJobStatus((prev) =>
              prev
                ? {
                    ...prev,
                    status: 'in_progress',
                    current_step: data.step || prev.current_step,
                    progress_percentage: data.percentage ?? prev.progress_percentage,
                  }
                : prev
            );
          }
          if (data.type === 'completed') {
            setIsResearching(false);
            setJobStatus((prev) =>
              prev ? { ...prev, status: 'completed', current_step: 'completed', progress_percentage: 100 } : prev
            );
            if (data.job_id) fetchResults(data.job_id);
          }
          if (data.type === 'error') {
            setIsResearching(false);
            setJobStatus((prev) => (prev ? { ...prev, status: 'failed' } : prev));
            setError(new Error(data.error || 'Unknown error'));
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };

      ws.onerror = () => {
        setConnectionError('WebSocket unavailable — using polling');
        setIsConnected(false);
        wsFailedRef.current = true;
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        // If WS failed (not a clean user disconnect), fall back to HTTP polling
        if (wsFailedRef.current && !pollIntervalRef.current) {
          pollIntervalRef.current = setInterval(async () => {
            try {
              const status = await api.getResearchStatus(id);
              setJobStatus(status);
              if (status.status === 'completed') {
                stopPolling();
                setIsResearching(false);
                fetchResults(id);
              } else if (status.status === 'failed') {
                stopPolling();
                setIsResearching(false);
              } else {
                setIsResearching(true);
              }
            } catch (_err) {
              // silently swallow — job may not be started yet
            }
          }, 2500);
        } else if (isResearching && event.code !== 1000 && !wsFailedRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => connectWebSocket(id), 3000);
        }
      };
    } catch (e) {
      console.error('Error creating WebSocket:', e);
      setConnectionError('Failed to create WebSocket connection');
    }
  }, [fetchResults, isResearching]);

  const reconnect = useCallback(() => {
    if (jobId) connectWebSocket(jobId);
  }, [jobId, connectWebSocket]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const startResearch = useCallback(async (preferences: TravelPreferences) => {
    setIsStarting(true);
    setError(null);
    setResults(null);
    setMessages([]);
    setLastMessage(null);
    setConnectionError(null);
    wsFailedRef.current = false;
    stopPolling();

    try {
      const job = await api.startAutoResearch(preferences);
      setJobId(job.job_id);
      setJobStatus(job);
      connectWebSocket(job.job_id);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to start research'));
    } finally {
      setIsStarting(false);
    }
  }, [connectWebSocket, stopPolling]);

  const clearResults = useCallback(() => {
    disconnect();
    setJobId(null);
    setJobStatus(null);
    setResults(null);
    setError(null);
    setConnectionError(null);
    setMessages([]);
    setLastMessage(null);
    setIsResearching(false);
  }, [disconnect]);

  useEffect(() => {
    return () => {
      stopPolling();
      disconnect();
    };
  }, [disconnect, stopPolling]);

  return {
    jobId,
    jobStatus,
    results,
    isConnected,
    isStarting,
    isResearching,
    lastMessage,
    messages,
    error,
    connectionError,
    startResearch,
    fetchResults,
    clearResults,
    reconnect,
    disconnect,
    sendMessage,
  };
}
