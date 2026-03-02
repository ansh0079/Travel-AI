'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, User, Sparkles, Check, Edit2, MapPin, Calendar, Users, Wallet, Compass, X } from 'lucide-react';
import { api, TravelPreferences } from '@/services/api';
import { useChatPipeline } from '@/hooks/useChatPipeline';
import { buildAutonomousSuggestionPrompt, getAutonomousSuggestionAction } from '@/utils/autonomousSuggestionActions';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  suggestions?: string[];
  extracted?: Partial<TravelPreferences>;
}

interface TravelPlanningAgentProps {
  onComplete: (preferences: TravelPreferences) => void;
  isLoading?: boolean;
}

function normalizeBudgetLevel(level: unknown): TravelPreferences['budget_level'] {
  if (level === 'budget' || level === 'low') return 'low';
  if (level === 'high') return 'high';
  if (level === 'luxury' || level === 'ultra-luxury') return 'luxury';
  return 'moderate';
}

function normalizeWeatherPreference(value: unknown): TravelPreferences['weather_preference'] {
  if (value === 'hot' || value === 'warm' || value === 'mild' || value === 'cold' || value === 'snow') {
    return value;
  }
  return 'warm';
}

export default function TravelPlanningAgent({ onComplete, isLoading }: TravelPlanningAgentProps) {
  const [sessionId, setSessionId] = useState(
    () => (typeof window !== 'undefined' ? localStorage.getItem('travelai_agent_session') : null) || `session_${Date.now()}`
  );
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Hi there! 👋 I'm your AI Travel Planning Agent.

I'll help you plan your perfect trip through a friendly chat. Just tell me about your travel plans naturally - where you want to go, when, with who, your budget, interests... anything!

For example:
• *"I want a beach vacation in Thailand for 2 weeks in December with my partner"*
• *"Family trip to Japan with kids aged 5 and 8, interested in culture and food, about $300/day"*
• *"Solo backpacking Europe this summer, love hiking and meeting locals, tight budget"*

What kind of trip are you dreaming of? ✈️`,
      suggestions: ['Beach vacation', 'City break', 'Adventure trip', 'Family holiday']
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [extractedData, setExtractedData] = useState<Partial<TravelPreferences> | null>(null);
  const [showSummary, setShowSummary] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const announcedResearchJobRef = useRef<string | null>(null);
  const [activeAgentPanel, setActiveAgentPanel] = useState<'compare' | 'itinerary' | 'budget' | null>(null);

  const {
    planningStage,
    rankedDestinations,
    isRanking,
    isReady,
    researchJob,
    researchResults,
    isResearching,
    syncMessageResult,
    submitFeedback,
    advanceStage,
    clearSession,
    trackRecommendationAccepted,
  } = useChatPipeline<Partial<TravelPreferences>>({
    sessionId,
    onHydrate: (prefs) => setExtractedData(prefs),
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('travelai_agent_session', sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!researchResults || researchJob?.status !== 'completed') return;
    if (announcedResearchJobRef.current === researchJob.job_id) return;

    const top = (researchResults.recommendations || [])
      .slice(0, 3)
      .map((r: any, i: number) => `${i + 1}. ${r.destination || 'Destination'}${typeof r.score === 'number' ? ` (${r.score})` : ''}`)
      .join('\n');

    setMessages((prev) => [
      ...prev,
      {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: top
          ? `Autonomous research completed. Top matches for you:\n${top}\n\nI can now compare these or build your itinerary.`
          : 'Autonomous research completed. I can now suggest your best matches and build an itinerary.',
        suggestions: ['Compare top destinations', 'Build itinerary', 'Show budget breakdown'],
      },
    ]);

    announcedResearchJobRef.current = researchJob.job_id;
  }, [researchJob, researchResults]);

  useEffect(() => {
    announcedResearchJobRef.current = null;
  }, [sessionId]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isTyping) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const data = await api.chatMessage({
        message: text,
        session_id: sessionId,
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        suggestions: data.suggestions,
        extracted: data.extracted_preferences
      };

      setMessages(prev => [...prev, assistantMessage]);
      const extractedPrefs = (data.extracted_preferences || {}) as Partial<TravelPreferences>;
      await syncMessageResult({
        extractedPreferences: extractedPrefs,
        ready: Boolean(data.is_ready_for_recommendations),
        stage: data.planning_stage,
      });

      if (data.is_ready_for_recommendations) {
        setTimeout(() => setShowSummary(true), 1500);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I had trouble processing that. Could you try rephrasing?',
        suggestions: ['Try again']
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleSuggestionClick = (suggestion: string) => {
    const action = getAutonomousSuggestionAction(suggestion);
    if (action) setActiveAgentPanel(action);
    const autonomousPrompt = buildAutonomousSuggestionPrompt(suggestion, rankedDestinations, researchResults);
    sendMessage(autonomousPrompt || suggestion);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleComplete = () => {
    if (!extractedData) return;
    const maybeDates = (extractedData as any).travel_dates as { start?: string; end?: string } | undefined;

    const travelPrefs: TravelPreferences = {
      origin: extractedData.origin || '',
      destinations: extractedData.destinations || [],
      travel_start: extractedData.travel_start || maybeDates?.start || '',
      travel_end: extractedData.travel_end || maybeDates?.end || '',
      budget_level: normalizeBudgetLevel(extractedData.budget_level),
      budget_daily: extractedData.budget_daily,
      interests: extractedData.interests || [],
      traveling_with: extractedData.traveling_with || 'solo',
      passport_country: extractedData.passport_country || 'US',
      visa_preference: extractedData.visa_preference || 'visa_free',
      weather_preference: normalizeWeatherPreference(extractedData.weather_preference || extractedData.preferred_weather),
      num_travelers: extractedData.num_travelers || 1,
      has_kids: extractedData.has_kids || false,
      kids_ages: extractedData.kids_ages || [],
      activity_pace: extractedData.activity_pace,
      accommodation_type: extractedData.accommodation_type,
      dietary_restrictions: extractedData.dietary_restrictions || [],
      accessibility_needs: extractedData.accessibility_needs || [],
      special_occasion: extractedData.special_occasion,
      nightlife_priority: extractedData.nightlife_priority,
      car_hire: extractedData.car_hire,
      flight_class: extractedData.flight_class,
      past_destinations: extractedData.past_destinations || [],
      special_requests: extractedData.special_requests || '',
      preferred_continent: extractedData.preferred_continent,
      preferred_countries: extractedData.preferred_countries || [],
    };

    onComplete(travelPrefs);
  };

  const resetChat = async () => {
    await clearSession();
    const newSessionId = `session_${Date.now()}`;
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: `Hi there! 👋 I'm your AI Travel Planning Agent.\n\nTell me about your dream trip!`,
      suggestions: ['Beach vacation', 'City break', 'Adventure trip', 'Family holiday']
    }]);
    setExtractedData(null);
    setShowSummary(false);
    setSessionId(newSessionId);
  };

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
    }
  }, [input]);

  return (
    <div className="flex flex-col h-[650px] bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Travel Planning Agent</h3>
            <p className="text-blue-100 text-xs">I gather your preferences through natural conversation</p>
          </div>
        </div>
        {extractedData && (
          <div className="flex items-center gap-2">
            <ProgressBadge extracted={extractedData} isReady={isReady} />
            <span className="px-2 py-1 bg-white/20 text-white rounded-full text-xs font-medium capitalize">
              {planningStage.replace('_', ' ')}
            </span>
            <button
              onClick={resetChat}
              className="p-2 hover:bg-white/20 rounded-full text-white/80 hover:text-white transition-colors"
              title="Start over"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex gap-3 max-w-[85%] ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.role === 'user' ? 'bg-blue-600' : 'bg-gradient-to-br from-purple-500 to-blue-600'
                    }`}>
                      {message.role === 'user' ? (
                        <User className="w-4 h-4 text-white" />
                      ) : (
                        <Sparkles className="w-4 h-4 text-white" />
                      )}
                    </div>
                    <div className={`rounded-2xl px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
                      
                      {message.suggestions && message.suggestions.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          {message.suggestions.map((suggestion, i) => (
                            <button
                              key={i}
                              onClick={() => handleSuggestionClick(suggestion)}
                              className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
                                message.role === 'user'
                                  ? 'bg-blue-500 text-white hover:bg-blue-400'
                                  : 'bg-white text-blue-600 hover:bg-blue-50 border border-blue-200'
                              }`}
                            >
                              {suggestion}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {isTyping && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="p-4 border-t border-gray-100 bg-white">
            <div className="flex gap-3">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe your trip plans..."
                className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 resize-none min-h-[50px] max-h-[120px]"
                rows={1}
                disabled={isTyping || isLoading || showSummary}
              />
              <button
                type="submit"
                disabled={!input.trim() || isTyping || isLoading || showSummary}
                className="px-5 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-2 text-center">
              Press Enter to send, Shift+Enter for new line
            </p>
          </form>
        </div>

        {/* Live Info Panel */}
        {extractedData && (
          <div className="w-72 bg-gray-50 border-l border-gray-200 p-4 overflow-y-auto hidden lg:block">
            <h4 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Check className="w-4 h-4 text-green-500" />
              Information Gathered
            </h4>
            <InfoSection title="Trip Basics" icon={MapPin}>
              <InfoItem label="From" value={extractedData.origin} />
              <InfoItem label="Dates" value={
                (extractedData.travel_start && extractedData.travel_end)
                  ? `${extractedData.travel_start} to ${extractedData.travel_end}`
                  : ((extractedData as any).travel_dates?.start && (extractedData as any).travel_dates?.end
                    ? `${(extractedData as any).travel_dates.start} to ${(extractedData as any).travel_dates.end}`
                    : undefined)
              } />
              <InfoItem label="Travelers" value={extractedData.num_travelers ? 
                `${extractedData.num_travelers} people` : undefined} />
              <InfoItem label="Type" value={extractedData.traveling_with} />
            </InfoSection>

            <InfoSection title="Preferences" icon={Compass}>
              <InfoItem label="Budget" value={extractedData.budget_level} />
              <InfoItem label="Style" value={extractedData.activity_pace} />
              <InfoItem label="Weather" value={extractedData.preferred_weather} />
              <InfoItem label="Pace" value={extractedData.activity_pace} />
            </InfoSection>

            <InfoSection title="Interests" icon={Sparkles}>
              {extractedData.interests && extractedData.interests.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                  {extractedData.interests.map((interest, i) => (
                    <span key={i} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                      {interest}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-xs text-gray-400">Not specified yet</span>
              )}
            </InfoSection>

            <button
              onClick={async () => {
                await advanceStage();
              }}
              className="w-full mt-2 py-2.5 border border-gray-300 text-gray-700 rounded-xl text-sm hover:bg-gray-100 transition-colors"
            >
              Move to Next Stage
            </button>

            {(isRanking || rankedDestinations.length > 0) && (
              <div className="mt-4 rounded-xl border border-gray-200 bg-white p-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-gray-700">Ranked Destinations</p>
                  {isRanking && <span className="text-xs text-emerald-700">Ranking...</span>}
                </div>
                <div className="space-y-2">
                  {rankedDestinations.slice(0, 4).map((dest) => (
                    <div key={dest.destination} className="rounded-lg border border-gray-200 px-2.5 py-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-xs font-semibold text-gray-900">{dest.destination}</p>
                          <p className="text-[11px] text-gray-600">{dest.reasons?.join(' • ') || 'Matches your preferences'}</p>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <span className="text-[11px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">{dest.score}</span>
                          <div className="flex gap-1">
                            <button
                              onClick={() => submitFeedback(dest.destination, 1, extractedData)}
                              className="text-[11px] px-1.5 py-0.5 rounded border border-gray-300 hover:bg-gray-50"
                            >
                              Like
                            </button>
                            <button
                              onClick={() => submitFeedback(dest.destination, -1, extractedData)}
                              className="text-[11px] px-1.5 py-0.5 rounded border border-gray-300 hover:bg-gray-50"
                            >
                              Less
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeAgentPanel && (
              <div className="mt-3 rounded-xl border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-800">
                {activeAgentPanel === 'compare' && 'Compare panel is active: focusing on destination comparison.'}
                {activeAgentPanel === 'itinerary' && 'Itinerary panel is active: generating day-by-day plan.'}
                {activeAgentPanel === 'budget' && 'Budget panel is active: preparing detailed cost breakdown.'}
              </div>
            )}

            {(isResearching || researchJob || researchResults) && (
              <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-800">
                {isResearching && `Autonomous research running (${researchJob?.status || 'in_progress'})`}
                {!isResearching && researchJob?.status === 'completed' && `Autonomous research completed (${researchResults?.recommendations?.length || 0} recommendations)`}
                {!isResearching && researchJob?.status === 'failed' && 'Autonomous research failed'}
              </div>
            )}

            {researchResults?.recommendations?.length ? (
              <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3">
                <p className="text-xs font-semibold text-emerald-800 mb-2">Autonomous Top Picks</p>
                <div className="space-y-2">
                  {researchResults.recommendations.slice(0, 3).map((rec, idx) => (
                    <div key={`${rec.destination}-${idx}`} className="rounded-lg bg-white border border-emerald-100 px-3 py-2 flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{rec.destination}</p>
                        <p className="text-xs text-gray-600">{(rec.reasons || []).slice(0, 2).join(' • ') || 'Strong match'}</p>
                      </div>
                      <button
                        onClick={async () => {
                          await trackRecommendationAccepted(rec.destination);
                          sendMessage(`Use ${rec.destination} as my final plan and build a detailed itinerary.`);
                        }}
                        className="text-xs px-2.5 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700"
                      >
                        Use this plan
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {isReady && (
              <motion.button
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={() => setShowSummary(true)}
                className="w-full mt-4 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 transition-colors"
              >
                ✨ Get Recommendations
              </motion.button>
            )}
          </div>
        )}
      </div>

      {/* Summary Modal */}
      <AnimatePresence>
        {showSummary && extractedData && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-hidden"
            >
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4">
                <h3 className="text-xl font-bold text-white">🎉 Trip Summary</h3>
                <p className="text-blue-100 text-sm">Review your preferences before we search</p>
              </div>

              <div className="p-6 overflow-y-auto max-h-[50vh]">
                <SummarySection title="Trip Details">
                  <SummaryItem icon={MapPin} label="Departing from" value={extractedData.origin} />
                  <SummaryItem icon={Calendar} label="Dates" value={
                    extractedData.travel_start
                      ? `${extractedData.travel_start} to ${extractedData.travel_end}`
                      : ((extractedData as any).travel_dates?.start
                        ? `${(extractedData as any).travel_dates.start} to ${(extractedData as any).travel_dates?.end || ''}`.trim()
                        : undefined)
                  } />
                  <SummaryItem icon={Users} label="Travelers" value={extractedData.num_travelers ? 
                    `${extractedData.num_travelers} ${extractedData.traveling_with || 'people'}` : undefined} />
                </SummarySection>

                <SummarySection title="Preferences">
                  <SummaryItem icon={Wallet} label="Budget" value={extractedData.budget_level} />
                  <SummaryItem icon={Compass} label="Interests" value={extractedData.interests?.join(', ')} />
                  <SummaryItem icon={Sparkles} label="Weather" value={extractedData.preferred_weather} />
                  {extractedData.has_kids && (
                    <SummaryItem icon={Users} label="Kids" value={`Ages ${extractedData.kids_ages?.join(', ') || 'not specified'}`} />
                  )}
                </SummarySection>

                {extractedData.special_requests && (
                  <SummarySection title="Special Requests">
                    <p className="text-sm text-gray-600">{extractedData.special_requests}</p>
                  </SummarySection>
                )}
              </div>

              <div className="p-4 border-t border-gray-200 flex gap-3">
                <button
                  onClick={() => setShowSummary(false)}
                  className="flex-1 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-colors"
                >
                  Keep Chatting
                </button>
                <button
                  onClick={handleComplete}
                  disabled={isLoading}
                  className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {isLoading ? 'Searching...' : 'Find Destinations'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Helper Components
function ProgressBadge({ extracted, isReady }: { extracted: Partial<TravelPreferences>; isReady: boolean }) {
  const maybeDates = (extracted as any).travel_dates as { start?: string; end?: string } | undefined;
  const filledFields = [
    extracted.origin,
    (extracted.travel_start && extracted.travel_end) || (maybeDates?.start && maybeDates?.end),
    extracted.num_travelers,
    extracted.budget_level || extracted.budget_daily,
    extracted.interests && extracted.interests.length > 0,
  ].filter(Boolean).length;

  const totalFields = 5;
  const percentage = Math.round((filledFields / totalFields) * 100);

  if (isReady) {
    return (
      <span className="px-3 py-1 bg-green-500 text-white rounded-full text-xs font-medium">
        ✓ Ready
      </span>
    );
  }

  return (
    <span className="px-3 py-1 bg-white/20 text-white rounded-full text-xs font-medium">
      {percentage}%
    </span>
  );
}

function InfoSection({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
        <Icon className="w-3 h-3" />
        {title}
      </h5>
      <div className="space-y-1">
        {children}
      </div>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value?: string | number }) {
  if (!value) return null;
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium capitalize">{value}</span>
    </div>
  );
}

function SummarySection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h4 className="font-semibold text-gray-900 mb-2">{title}</h4>
      <div className="space-y-2">
        {children}
      </div>
    </div>
  );
}

function SummaryItem({ icon: Icon, label, value }: { icon: any; label: string; value?: string }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
        <Icon className="w-4 h-4 text-blue-600" />
      </div>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm font-medium text-gray-900 capitalize">{value}</p>
      </div>
    </div>
  );
}
