"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/services/api";

interface ResearchState {
  jobId: string | null;
  status: "idle" | "researching" | "completed" | "error";
  progress: number;
  currentStep: string;
  results: any | null;
  error: string | null;
  messages: Array<{ type: string; message: string; timestamp: Date }>;
}

interface WebSocketMessage {
  type: "connected" | "started" | "progress" | "completed" | "error" | "pong";
  job_id?: string;
  step?: string;
  percentage?: number;
  message?: string;
  error?: string;
  results_summary?: any;
}

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1";

export function useResearch() {
  const [state, setState] = useState<ResearchState>({
    jobId: null,
    status: "idle",
    progress: 0,
    currentStep: "",
    results: null,
    error: null,
    messages: [],
  });

  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback((jobId: string) => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = `${WS_BASE_URL}/ws/research/${jobId}`;
    console.log("Connecting to WebSocket:", wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        setConnectionError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          console.log("WebSocket message:", data);

          switch (data.type) {
            case "started":
              setState((prev) => ({
                ...prev,
                status: "researching",
                messages: [
                  ...prev.messages,
                  {
                    type: "info",
                    message: "Research started...",
                    timestamp: new Date(),
                  },
                ],
              }));
              break;

            case "progress":
              setState((prev) => ({
                ...prev,
                progress: data.percentage || 0,
                currentStep: data.step || "",
                messages: [
                  ...prev.messages,
                  {
                    type: "step",
                    message: data.message || `Step: ${data.step} (${data.percentage}%)`,
                    timestamp: new Date(),
                  },
                ],
              }));
              break;

            case "completed":
              setState((prev) => ({
                ...prev,
                status: "completed",
                progress: 100,
                messages: [
                  ...prev.messages,
                  {
                    type: "success",
                    message: `Research complete! Found ${data.results_summary?.destinations_count || 0} destinations.`,
                    timestamp: new Date(),
                  },
                ],
              }));
              disconnect();
              // Fetch full results
              if (data.job_id) {
                fetchResults(data.job_id);
              }
              break;

            case "error":
              setState((prev) => ({
                ...prev,
                status: "error",
                error: data.error || "Unknown error",
                messages: [
                  ...prev.messages,
                  {
                    type: "error",
                    message: data.error || "An error occurred",
                    timestamp: new Date(),
                  },
                ],
              }));
              disconnect();
              break;
          }
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnectionError("WebSocket connection error");
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        console.log("WebSocket closed:", event.code, event.reason);
        setIsConnected(false);

        // Auto-reconnect if research is still ongoing
        if (state.status === "researching" && event.code !== 1000) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect(jobId);
          }, 3000);
        }
      };
    } catch (e) {
      console.error("Error creating WebSocket:", e);
      setConnectionError("Failed to create WebSocket connection");
    }
  }, [state.status]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, "User disconnected");
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  const startResearch = useCallback(
    async (preferences: any) => {
      try {
        setState({
          jobId: null,
          status: "researching",
          progress: 0,
          currentStep: "",
          results: null,
          error: null,
          messages: [],
        });

        // Start research job
        const response = await api.startAutoResearch(preferences);
        const job_id = response.job_id;

        setState((prev) => ({ ...prev, jobId: job_id }));
        jobIdRef.current = job_id;

        // Connect WebSocket for real-time updates
        connect(job_id);

        return job_id;
      } catch (error) {
        setState((prev) => ({
          ...prev,
          status: "error",
          error: error instanceof Error ? error.message : "Failed to start research",
        }));
        throw error;
      }
    },
    [connect]
  );

  const fetchResults = useCallback(async (jobId: string) => {
    try {
      const results = await api.getResearchResults(jobId);
      setState((prev) => ({ ...prev, results }));
      return results;
    } catch (error) {
      console.error("Failed to fetch results:", error);
      throw error;
    }
  }, []);

  const cancelResearch = useCallback(() => {
    disconnect();
    setState({
      jobId: null,
      status: "idle",
      progress: 0,
      currentStep: "",
      results: null,
      error: null,
      messages: [],
    });
  }, [disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    ...state,
    isConnected,
    connectionError,
    startResearch,
    cancelResearch,
    fetchResults,
    disconnect,
    connect,
  };
}
