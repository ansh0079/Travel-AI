import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ResearchJob, ResearchResults, TravelPreferences } from '@/services/api';

export interface RankedDestination {
  destination: string;
  score: number;
  reasons: string[];
  constraints_applied: Record<string, any>;
}

export const PIPELINE_STEPS = ['discover', 'shortlist', 'compare', 'itinerary', 'booking_checklist'] as const;

export const STAGE_LABELS: Record<string, string> = {
  discover: 'Discover',
  shortlist: 'Shortlist',
  compare: 'Compare',
  itinerary: 'Itinerary',
  booking_checklist: 'Booking Checklist',
};

type BasePreferences = {
  destinations?: string[];
  budget_level?: string;
  visa_preference?: string;
  weather_preference?: string;
  preferred_weather?: string;
  [key: string]: any;
};

interface UseChatPipelineOptions<T extends BasePreferences> {
  sessionId: string;
  onHydrate?: (prefs: T | null) => void;
  defaultCandidates?: string[];
  autonomousResearch?: boolean;
}

export function useChatPipeline<T extends BasePreferences>({
  sessionId,
  onHydrate,
  defaultCandidates = ['Bangkok', 'Bali', 'Rome', 'Tokyo', 'Barcelona'],
  autonomousResearch = true,
}: UseChatPipelineOptions<T>) {
  const [planningStage, setPlanningStage] = useState<string>('discover');
  const [rankedDestinations, setRankedDestinations] = useState<RankedDestination[]>([]);
  const [isRanking, setIsRanking] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [researchJob, setResearchJob] = useState<ResearchJob | null>(null);
  const [researchResults, setResearchResults] = useState<ResearchResults | null>(null);
  const [isResearching, setIsResearching] = useState(false);
  const onHydrateRef = useRef(onHydrate);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autonomousStartedForSession = useRef<string | null>(null);
  const readyTrackedForSession = useRef<string | null>(null);
  const researchCompletedTrackedForJob = useRef<string | null>(null);

  useEffect(() => {
    onHydrateRef.current = onHydrate;
  }, [onHydrate]);

  useEffect(() => {
    autonomousStartedForSession.current = null;
    readyTrackedForSession.current = null;
    researchCompletedTrackedForJob.current = null;
    setResearchJob(null);
    setResearchResults(null);
    setIsResearching(false);
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, [sessionId]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const toResearchPreferences = useCallback((prefs: T | null): TravelPreferences => {
    const p = prefs || ({} as T);
    const maybeDates = (p as any).travel_dates as { start?: string; end?: string } | undefined;
    return {
      origin: p.origin || '',
      destinations: Array.isArray(p.destinations) ? p.destinations : [],
      travel_start: (p as any).travel_start || maybeDates?.start || '',
      travel_end: (p as any).travel_end || maybeDates?.end || '',
      budget_level: (p.budget_level as any) || 'moderate',
      interests: Array.isArray(p.interests) ? p.interests : [],
      traveling_with: (p.traveling_with as any) || 'solo',
      passport_country: p.passport_country || 'US',
      visa_preference: (p.visa_preference as any) || 'visa_free',
      weather_preference: (p.weather_preference as any) || (p.preferred_weather as any) || 'warm',
      num_travelers: Number((p as any).num_travelers || 1),
      has_kids: Boolean((p as any).has_kids),
      kids_ages: Array.isArray((p as any).kids_ages) ? (p as any).kids_ages : [],
      activity_pace: (p as any).activity_pace || 'moderate',
      accommodation_type: (p as any).accommodation_type,
      dietary_restrictions: Array.isArray((p as any).dietary_restrictions) ? (p as any).dietary_restrictions : [],
      accessibility_needs: Array.isArray((p as any).accessibility_needs) ? (p as any).accessibility_needs : [],
      special_occasion: (p as any).special_occasion,
      nightlife_priority: (p as any).nightlife_priority || 'medium',
      car_hire: (p as any).car_hire,
      flight_class: (p as any).flight_class || 'economy',
      past_destinations: Array.isArray((p as any).past_destinations) ? (p as any).past_destinations : [],
      special_requests: (p as any).special_requests || '',
    };
  }, []);

  const stopResearchPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const startResearchPolling = useCallback((jobId: string) => {
    stopResearchPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const status = await api.getResearchStatus(jobId);
        setResearchJob(status);
        const active = status.status === 'pending' || status.status === 'in_progress';
        setIsResearching(active);
        if (!active) {
          stopResearchPolling();
          if (status.status === 'completed' && status.results_available) {
            const results = await api.getResearchResults(jobId);
            setResearchResults(results);
            if (researchCompletedTrackedForJob.current !== jobId) {
              researchCompletedTrackedForJob.current = jobId;
              await api.trackAnalyticsEvent('autonomous_research_completed', sessionId, {
                recommendations: Array.isArray(results.recommendations) ? results.recommendations.length : 0,
              });
            }
          }
        }
      } catch (error) {
        console.error('Autonomous research polling failed:', error);
      }
    }, 2500);
  }, [sessionId, stopResearchPolling]);

  const startAutonomousResearch = useCallback(async (prefs: T | null) => {
    if (!autonomousResearch) return;
    if (autonomousStartedForSession.current === sessionId) return;
    autonomousStartedForSession.current = sessionId;

    try {
      const job = await api.startAutoResearch(toResearchPreferences(prefs));
      setResearchJob(job);
      setIsResearching(true);
      await api.trackAnalyticsEvent('autonomous_research_started', sessionId, { job_id: job.job_id });
      startResearchPolling(job.job_id);
    } catch (error) {
      console.error('Autonomous research start failed:', error);
      setIsResearching(false);
    }
  }, [autonomousResearch, sessionId, startResearchPolling, toResearchPreferences]);

  useEffect(() => {
    let mounted = true;
    const hydrateSession = async () => {
      try {
        const data = await api.getChatSession(sessionId);
        if (!mounted) return;
        const hydratedPrefs = (data.extracted_preferences || null) as T | null;
        setIsReady(Boolean(data.is_ready_for_recommendations));
        setPlanningStage(data.planning_stage || 'discover');
        const ranked = Array.isArray(data.planning_data?.ranked_destinations)
          ? data.planning_data.ranked_destinations
          : [];
        setRankedDestinations(ranked);
        onHydrateRef.current?.(hydratedPrefs);
      } catch {
        // Session may not exist yet.
      }
    };
    hydrateSession();
    return () => {
      mounted = false;
    };
  }, [sessionId]);

  const buildRankingCandidates = useCallback((prefs: T | null): string[] => {
    const fromExtracted = Array.isArray(prefs?.destinations) ? prefs.destinations : [];
    const merged = [...(fromExtracted || []), ...defaultCandidates];
    return Array.from(new Set(merged.map((x) => String(x).trim()).filter(Boolean))).slice(0, 8);
  }, [defaultCandidates]);

  const runRanking = useCallback(async (prefs: T | null) => {
    if (isRanking) return;
    const candidates = buildRankingCandidates(prefs);
    if (!candidates.length) return;

    setIsRanking(true);
    try {
      const result = await api.rankChatRecommendations(sessionId, candidates, {
        budget_level: prefs?.budget_level,
        visa_preference: prefs?.visa_preference,
        weather_preference: prefs?.weather_preference || prefs?.preferred_weather,
      });
      const ranked = result.ranked_destinations || [];
      setRankedDestinations(ranked);
      await api.updateChatPipelineData(sessionId, {
        shortlist: ranked.map((item) => item.destination),
      });
      const stageIndex = PIPELINE_STEPS.indexOf((planningStage as any) || 'discover');
      if (stageIndex < PIPELINE_STEPS.indexOf('shortlist')) {
        const stage = await api.advanceChatPipeline(sessionId, 'shortlist');
        setPlanningStage(stage.planning_stage);
      }
    } catch (error) {
      console.error('Ranking failed:', error);
    } finally {
      setIsRanking(false);
    }
  }, [buildRankingCandidates, isRanking, planningStage, sessionId]);

  const submitFeedback = useCallback(async (destination: string, feedback: number, prefs: T | null) => {
    try {
      await api.submitChatRecommendationFeedback(sessionId, destination, feedback);
      await runRanking(prefs);
    } catch (error) {
      console.error('Feedback submission failed:', error);
    }
  }, [runRanking, sessionId]);

  const syncMessageResult = useCallback(async (params: {
    extractedPreferences: T | null;
    ready: boolean;
    stage?: string;
  }) => {
    const { extractedPreferences, ready, stage } = params;
    setIsReady(Boolean(ready));
    if (stage) setPlanningStage(stage);
    onHydrateRef.current?.(extractedPreferences);
    await api.updateChatPipelineData(sessionId, {
      extracted_preferences: extractedPreferences || {},
    });
    if (ready) {
      if (readyTrackedForSession.current !== sessionId) {
        readyTrackedForSession.current = sessionId;
        await api.trackAnalyticsEvent('chat_ready_reached', sessionId, {});
      }
      await runRanking(extractedPreferences);
      await startAutonomousResearch(extractedPreferences);
    }
  }, [runRanking, sessionId, startAutonomousResearch]);

  const trackRecommendationAccepted = useCallback(async (destination: string) => {
    await api.trackAnalyticsEvent('recommendation_accepted', sessionId, { destination });
  }, [sessionId]);

  const advanceStage = useCallback(async () => {
    const next = await api.advanceChatPipeline(sessionId);
    setPlanningStage(next.planning_stage);
  }, [sessionId]);

  const clearSession = useCallback(async () => {
    try {
      await api.clearChatSession(sessionId);
    } catch {
      // Session might already be missing.
    }
  }, [sessionId]);

  return {
    planningStage,
    setPlanningStage,
    rankedDestinations,
    isRanking,
    isReady,
    setIsReady,
    runRanking,
    submitFeedback,
    syncMessageResult,
    advanceStage,
    clearSession,
    researchJob,
    researchResults,
    isResearching,
    startAutonomousResearch,
    trackRecommendationAccepted,
  };
}
