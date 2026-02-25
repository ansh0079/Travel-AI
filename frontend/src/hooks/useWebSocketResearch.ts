'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { api, TravelPreferences, ResearchJob, ResearchResults } from '@/services/api';

interface UseWebSocketResearchReturn {
  // Job state
  jobId: string | null;
  jobStatus: ResearchJob | null;
  results: ResearchResults | null;
  
  // Connection state
  isConnected: boolean;
  isStarting: boolean;
  isResearching: boolean;
  
  // Messages
  lastMessage: WebSocketMessage | null;
  messages: WebSocketMessage[];
  
  // Errors
  error: Error | null;
  connectionError: string | null;
  
  // Actions
  startResearch: (preferences: TravelPreferences) => Promise<void>;
  fetchResults: (jobId: string) => Promise<ResearchResults | null>;
  clearResults: () => void;
  reconnect: () => void;
  disconnect: () => void;
  sendMessage: (message: any) => void;
}

interface WebSocketMessage {
  type: 'connected' | 'started' | 'progress' | 'completed' | 'error' | 'pong' | 'ack';
  job_id?: string;
  step?: string;
  percentage?: number;
  message?: string;
  error?: string;
  results_summary?: any;
  preferences?: any;
  timestamp?: number;
  received?: any;
}

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1';

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

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };
  }, []);

  const connectWebSocket = useCallback((id: string) => {
    // Close existing connection
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
        
        // Start ping interval to keep connection alive
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              action: 'ping',
              timestamp: Date.now()
            }));
          }
        }, 30000); // Ping every 30 seconds
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          console.log('WebSocket message:', data);
          
          setLastMessage(data);
          setMessages(prev => [...prev, data]);

          // Handle different message types
          switch (data.type) {
            case 'connected':
              setIsConnected(true);
              break;
              
            case 'started':
              setIsResearching(true);
              setJobStatus(prev => prev ? {
                ...prev,
                status: 'in_progress',
                current_step: 'started'
              } : null);
              break;
              
            case 'progress':
              setIsResearching(true);
              setJobStatus(prev => prev ? {
                ...prev,
                status: 'in_progress',
                progress_percentage: data.percentage || 0,
                current_step: data.step || 'researching'
              } : null);
              break;
              
            case 'completed':
              setIsResearching(false);
              setJobStatus(prev => prev ? {
                ...prev,
                status: 'completed',
                progress_percentage: 100,
                results_available: true
              } : null);
              // Auto-fetch results
              fetchResults(id);
              break;
              
            case 'error':
              setIsResearching(false);
              setJobStatus(prev => prev ? {
                ...prev,
                status: 'failed'
              } : null);
              setError(new Error(data.error || 'Research failed'));
              break;
              
            case 'pong':
              // Connection is alive, do nothing
              break;
              
            default:
              break;
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('WebSocket connection error');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        // Auto-reconnect if research is still ongoing (unless it was a normal close)
        if (isResearching && event.code !== 1000) {
          console.log('Attempting to reconnect in 3 seconds...');
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket(id);
          }, 3000);
        }
      };
    } catch (e) {
      console.error('Error creating WebSocket:', e);
      setConnectionError('Failed to create WebSocket connection');
    }
  }, [isResearching]);

  const disconnect = useCallback(() => {
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
  }, []);

  const reconnect = useCallback(() => {
    if (jobId) {
      connectWebSocket(jobId);
    }
  }, [jobId, connectWebSocket]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);

  const startResearch = useCallback(async (preferences: TravelPreferences) => {
    setIsStarting(true);
    setError(null);
    setResults(null);
    setMessages([]);
    setLastMessage(null);
    setConnectionError(null);
    
    try {
      // First, start the research via HTTP API
      const job = await api.startAutoResearch(preferences);
      setJobId(job.job_id);
      setJobStatus(job);
      
      // Then, connect WebSocket for real-time updates
      connectWebSocket(job.job_id);
      
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to start research'));
    } finally {
      setIsStarting(false);
    }
  }, [connectWebSocket]);

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

// Hook for multiple job tracking (useful for admin dashboard)
export function useWebSocketMultiResearch(): {
  activeJobs: Map<string, ResearchJob>;
  messages: Map<string, WebSocketMessage[]>;
  connectToJob: (jobId: string) => void;
  disconnectFromJob: (jobId: string) => void;
  disconnectAll: () => void;
} {
  const [activeJobs, setActiveJobs] = useState<Map<string, ResearchJob>>(new Map());
  const [messages, setMessages] = useState<Map<string, WebSocketMessage[]>>(new Map());
  const wsRefs = useRef<Map<string, WebSocket>>(new Map());

  const connectToJob = useCallback((jobId: string) => {
    if (wsRefs.current.has(jobId)) {
      return; // Already connected
    }

    const wsUrl = `${WS_BASE_URL}/ws/research/${jobId}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log(`WebSocket connected for job ${jobId}`);
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        
        setMessages(prev => {
          const newMap = new Map(prev);
          const jobMessages = newMap.get(jobId) || [];
          newMap.set(jobId, [...jobMessages, data]);
          return newMap;
        });

        // Update job status based on message type
        if (data.type === 'progress' || data.type === 'completed' || data.type === 'error') {
          setActiveJobs(prev => {
            const newMap = new Map(prev);
            const existing = newMap.get(jobId);
            if (existing) {
              newMap.set(jobId, {
                ...existing,
                status: data.type === 'completed' ? 'completed' : 
                        data.type === 'error' ? 'failed' : 'in_progress',
                progress_percentage: data.percentage || existing.progress_percentage,
                current_step: data.step || existing.current_step
              });
            }
            return newMap;
          });
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      wsRefs.current.delete(jobId);
    };

    wsRefs.current.set(jobId, ws);
  }, []);

  const disconnectFromJob = useCallback((jobId: string) => {
    const ws = wsRefs.current.get(jobId);
    if (ws) {
      ws.close();
      wsRefs.current.delete(jobId);
    }
  }, []);

  const disconnectAll = useCallback(() => {
    wsRefs.current.forEach((ws) => ws.close());
    wsRefs.current.clear();
  }, []);

  useEffect(() => {
    return () => {
      disconnectAll();
    };
  }, [disconnectAll]);

  return {
    activeJobs,
    messages,
    connectToJob,
    disconnectFromJob,
    disconnectAll,
  };
}
