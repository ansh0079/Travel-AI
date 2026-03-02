'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Sparkles,
  Loader2,
  MapPin,
  Calendar,
  Users,
  Heart,
  Wallet,
  Plane,
  Hotel,
  Camera,
  Utensils,
  Clock,
  CheckCircle2,
  ArrowRight,
  Zap,
  MessageSquare,
  Mic,
  StopCircle,
  Plus,
  Trash2,
  Settings,
  Share,
  Download,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
} from 'lucide-react';
import { api, TravelPreferences } from '@/services/api';
import { useChatPipeline, PIPELINE_STEPS, STAGE_LABELS } from '@/hooks/useChatPipeline';
import { buildAutonomousSuggestionPrompt, getAutonomousSuggestionAction } from '@/utils/autonomousSuggestionActions';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  suggestions?: string[];
  isStreaming?: boolean;
  metadata?: {
    destination?: string;
    image?: string;
    price?: string;
    rating?: number;
  };
}

interface ExtractedPreferences {
  destinations?: string[];
  origin?: string;
  travel_dates?: { start: string; end: string };
  budget_level?: 'budget' | 'moderate' | 'luxury' | 'ultra-luxury';
  interests?: string[];
  traveling_with?: 'solo' | 'couple' | 'family' | 'friends';
  [key: string]: any;
}

interface UltraModernChatProps {
  onComplete: (preferences: TravelPreferences) => void;
  sessionId?: string;
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
  return 'mild';
}

const QUICK_STARTS = [
  { icon: '🏖️', text: 'Beach vacation under $2000', prompt: 'I want a beach vacation under $2000' },
  { icon: '🏔️', text: 'Mountain adventure in Europe', prompt: 'Plan a mountain adventure in Europe' },
  { icon: '🏛️', text: 'Cultural city break in Asia', prompt: 'Suggest a cultural city break in Asia' },
  { icon: '🌴', text: 'Tropical family getaway', prompt: 'Plan a tropical family getaway' },
];

const SMART_SUGGESTIONS = [
  { icon: MapPin, label: 'Destination Ideas', prompt: 'Show me unique destination ideas for my budget' },
  { icon: Wallet, label: 'Budget Tips', prompt: 'How can I travel more on a budget?' },
  { icon: Calendar, label: 'Best Time to Visit', prompt: "When's the best time to visit Japan?" },
  { icon: Camera, label: 'Photography Spots', prompt: 'Best photography locations in Europe' },
  { icon: Utensils, label: 'Food & Cuisine', prompt: 'Tell me about local food scenes in Thailand' },
  { icon: Heart, label: 'Romantic Getaways', prompt: 'Suggest romantic destinations for couples' },
];

export default function UltraModernChat({ onComplete, sessionId: propSessionId, isLoading }: UltraModernChatProps) {
  const apiBaseUrl = (process.env.NEXT_PUBLIC_API_URL || '/api/v1').replace(/\/+$/, '');
  const [sessionId, setSessionId] = useState(
    () => propSessionId || (typeof window !== 'undefined' ? localStorage.getItem('travelai_ultra_session') : null) || `session_${Date.now()}`
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [extracted, setExtracted] = useState<ExtractedPreferences | null>(null);
  const [streamBuffer, setStreamBuffer] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeAgentPanel, setActiveAgentPanel] = useState<'compare' | 'itinerary' | 'budget' | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const announcedResearchJobRef = useRef<string | null>(null);

  const {
    planningStage,
    setPlanningStage,
    rankedDestinations,
    isRanking,
    isReady,
    setIsReady,
    researchJob,
    researchResults,
    isResearching,
    syncMessageResult,
    submitFeedback,
    advanceStage,
    clearSession,
    trackRecommendationAccepted,
  } = useChatPipeline<ExtractedPreferences>({
    sessionId,
    onHydrate: (prefs) => setExtracted(prefs),
  });

  useEffect(() => {
    if (propSessionId && propSessionId !== sessionId) {
      setSessionId(propSessionId);
    }
  }, [propSessionId, sessionId]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('travelai_ultra_session', sessionId);
    }
  }, [sessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamBuffer]);

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: `Hi there! 👋 I'm your AI travel assistant.

I can help you plan the perfect trip by understanding your preferences, budget, and travel style. Just tell me about your dream trip in your own words!

**What I can help with:**
• 🌍 Destination recommendations based on your interests
• 💰 Budget optimization and cost-saving tips
• 📅 Best times to visit based on weather and events
• 🎯 Personalized itineraries tailored to you
• 🛂 Visa requirements and travel advisories
• 🏨 Hotel and flight recommendations

**Try asking me something like:**
• "I want a beach vacation in Thailand for 2 weeks in December with my partner, mid-range budget"
• "Family trip to Japan with kids aged 5 and 8, interested in culture and food, about $300/day"
• "Solo backpacking through Europe this summer, love hiking and meeting locals, tight budget"

What's on your mind? 🌍`,
        timestamp: new Date(),
        suggestions: QUICK_STARTS.map(q => q.prompt),
      }]);
    }
  }, []);

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
        timestamp: new Date(),
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
      id: `msg_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);
    setShowSuggestions(false);

    try {
      const data = await api.chatMessage({
        message: text,
        session_id: sessionId,
      });

      const assistantMessage: Message = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        suggestions: data.suggestions,
      };

      setMessages(prev => [...prev, assistantMessage]);
      await syncMessageResult({
        extractedPreferences: (data.extracted_preferences || {}) as ExtractedPreferences,
        ready: Boolean(data.is_ready_for_recommendations),
        stage: data.planning_stage,
      });

    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I had trouble processing that. Could you try again?',
        timestamp: new Date(),
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const sendMessageStreaming = async (text: string) => {
    if (!text.trim() || isTyping) return;

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);
    setShowSuggestions(false);
    setStreamBuffer('');

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${apiBaseUrl}/chat/message/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Streaming request failed (${response.status})`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No reader available');

      let fullResponse = '';
      let done = false;
      let pending = '';

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;

        if (value) {
          pending += decoder.decode(value, { stream: !readerDone });
          const lines = pending.split('\n');
          pending = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.token) {
                  fullResponse += data.token;
                  setStreamBuffer(fullResponse);
                }

                if (data.done) {
                  const extractedPreferences = (data.extracted_preferences || {}) as ExtractedPreferences;

                  setMessages(prev => [...prev, {
                    id: `msg_${Date.now()}`,
                    role: 'assistant',
                    content: fullResponse,
                    timestamp: new Date(),
                  }]);
                  await syncMessageResult({
                    extractedPreferences,
                    ready: Boolean(data.is_ready),
                    stage: data.planning_stage,
                  });
                }

                if (data.error) {
                  throw new Error(data.error);
                }
              } catch (e) {
                console.warn('SSE parse error:', e);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      setMessages(prev => [...prev, {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I had trouble with that request. Please try again!',
        timestamp: new Date(),
      }]);
    } finally {
      setIsTyping(false);
      setStreamBuffer('');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessageStreaming(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSuggestionClick = (prompt: string) => {
    const action = getAutonomousSuggestionAction(prompt);
    if (action) setActiveAgentPanel(action);
    const autonomousPrompt = buildAutonomousSuggestionPrompt(prompt, rankedDestinations, researchResults);
    sendMessageStreaming(autonomousPrompt || prompt);
  };

  const handleComplete = () => {
    if (!extracted) return;

    const travelPrefs: TravelPreferences = {
      origin: extracted.origin || '',
      destinations: extracted.destinations || [],
      travel_start: extracted.travel_dates?.start || '',
      travel_end: extracted.travel_dates?.end || '',
      budget_level: normalizeBudgetLevel(extracted.budget_level),
      interests: extracted.interests || [],
      traveling_with: extracted.traveling_with || 'solo',
      passport_country: 'US',
      visa_preference: extracted.visa_preference || 'visa_free',
      weather_preference: normalizeWeatherPreference(extracted.weather_preference),
      num_travelers: extracted.num_travelers || 1,
      has_kids: extracted.traveling_with === 'family',
      kids_ages: extracted.kids_ages || [],
      activity_pace: extracted.activity_pace || 'moderate',
      accommodation_type: extracted.accommodation_type,
      dietary_restrictions: extracted.dietary_restrictions || [],
      accessibility_needs: extracted.accessibility_needs || [],
      special_occasion: extracted.special_occasion,
      nightlife_priority: extracted.nightlife_priority || 'medium',
      car_hire: extracted.car_hire,
      flight_class: extracted.flight_class || 'economy',
      past_destinations: [],
      special_requests: '',
    };

    onComplete(travelPrefs);
  };

  const copyMessage = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const clearChat = async () => {
    await clearSession();
    const newSessionId = `session_${Date.now()}`;
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: `Chat cleared! Let's start fresh. Where would you like to travel? 🌍`,
      timestamp: new Date(),
    }]);
    setExtracted(null);
    setIsReady(false);
    setPlanningStage('discover');
    setSessionId(newSessionId);
  };

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  const progress = extracted
    ? Math.round(
        (Object.values(extracted).filter(v => v && (Array.isArray(v) ? v.length > 0 : true)).length /
          Object.keys(extracted).length) *
          100
      )
    : 0;

  const formatContent = (content: string) => {
    return content.split('**').map((part, i) =>
      i % 2 === 1 ? <strong key={i} className="font-semibold">{part}</strong> : part
    );
  };

  return (
    <div ref={chatContainerRef} className="flex flex-col h-[750px] bg-gradient-to-b from-slate-900 via-purple-900/20 to-slate-900 rounded-3xl border border-white/10 shadow-2xl overflow-hidden backdrop-blur-xl">
      {/* Header */}
      <div className="px-6 py-4 bg-white/5 backdrop-blur-md border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-400 via-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-emerald-500/30"
          >
            <Sparkles className="w-6 h-6 text-white" />
          </motion.div>
          <div>
            <h3 className="font-bold text-white text-lg">AI Travel Assistant</h3>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Online • Powered by Advanced AI
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {extracted && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="hidden sm:flex items-center gap-3 mr-3"
            >
              <div className="text-right">
                <p className="text-xs text-gray-400">Profile Complete</p>
                <p className="text-sm font-bold text-emerald-400">{progress}%</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 text-white" />
              </div>
            </motion.div>
          )}
          
          <button
            onClick={clearChat}
            className="p-2.5 rounded-xl hover:bg-white/10 transition-colors group"
            title="Clear chat"
          >
            <Trash2 className="w-5 h-5 text-gray-400 group-hover:text-red-400 transition-colors" />
          </button>
          <button
            className="p-2.5 rounded-xl hover:bg-white/10 transition-colors group"
            title="Settings"
          >
            <Settings className="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <AnimatePresence>
        {extracted && Object.keys(extracted).length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-white/5 border-b border-white/10 overflow-hidden"
          >
            <div className="px-6 py-3">
              <div className="flex items-center gap-3 text-xs flex-wrap">
                <span className="text-gray-400 font-medium">Extracted:</span>
                <div className="flex flex-wrap gap-2">
                  {extracted.destinations && (
                    <motion.span 
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="px-3 py-1.5 bg-blue-500/20 text-blue-300 rounded-full flex items-center gap-1.5 border border-blue-500/30"
                    >
                      <MapPin className="w-3 h-3" />
                      {extracted.destinations.join(', ')}
                    </motion.span>
                  )}
                  {extracted.budget_level && (
                    <motion.span 
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="px-3 py-1.5 bg-green-500/20 text-green-300 rounded-full flex items-center gap-1.5 border border-green-500/30"
                    >
                      <Wallet className="w-3 h-3" />
                      {extracted.budget_level}
                    </motion.span>
                  )}
                  {extracted.traveling_with && (
                    <motion.span 
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="px-3 py-1.5 bg-purple-500/20 text-purple-300 rounded-full flex items-center gap-1.5 border border-purple-500/30"
                    >
                      <Users className="w-3 h-3" />
                      {extracted.traveling_with}
                    </motion.span>
                  )}
                  {extracted.travel_dates && (
                    <motion.span 
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="px-3 py-1.5 bg-orange-500/20 text-orange-300 rounded-full flex items-center gap-1.5 border border-orange-500/30"
                    >
                      <Calendar className="w-3 h-3" />
                      {extracted.travel_dates.start}
                    </motion.span>
                  )}
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 flex-wrap">
                <span className="text-[11px] text-gray-500 uppercase tracking-wide">Pipeline</span>
                {PIPELINE_STEPS.map((step) => {
                  const currentIndex = PIPELINE_STEPS.indexOf((planningStage as any) || 'discover');
                  const stepIndex = PIPELINE_STEPS.indexOf(step);
                  const isActive = step === planningStage;
                  const isCompleted = stepIndex < currentIndex;
                  return (
                    <span
                      key={step}
                      className={`px-2.5 py-1 rounded-full text-[11px] border ${
                        isActive
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/40'
                          : isCompleted
                          ? 'bg-cyan-500/20 text-cyan-200 border-cyan-400/30'
                          : 'bg-white/5 text-gray-400 border-white/10'
                      }`}
                    >
                      {STAGE_LABELS[step]}
                    </span>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <AnimatePresence>
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex gap-3 max-w-[90%] ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                {/* Avatar */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center ${
                  message.role === 'user' 
                    ? 'bg-gradient-to-br from-blue-500 to-purple-600' 
                    : message.role === 'assistant'
                    ? 'bg-gradient-to-br from-emerald-400 to-cyan-600'
                    : 'bg-gray-600'
                }`}>
                  {message.role === 'user' ? (
                    <Users className="w-5 h-5 text-white" />
                  ) : (
                    <Sparkles className="w-5 h-5 text-white" />
                  )}
                </div>

                {/* Message Bubble */}
                <div
                  className={`rounded-3xl px-5 py-4 ${
                    message.role === 'user'
                      ? 'bg-gradient-to-br from-blue-600 to-purple-700 text-white shadow-lg shadow-blue-500/20'
                      : message.role === 'assistant'
                      ? 'bg-white/10 backdrop-blur-md border border-white/10 text-gray-100'
                      : 'bg-gray-800/50 text-gray-400'
                  }`}
                >
                  {/* Content */}
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    {formatContent(message.content)}
                  </div>

                  {/* Action Buttons for Assistant Messages */}
                  {message.role === 'assistant' && (
                    <motion.div 
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.5 }}
                      className="flex items-center gap-2 mt-3 pt-3 border-t border-white/10"
                    >
                      <button
                        onClick={() => copyMessage(message.content, message.id)}
                        className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                        title="Copy"
                      >
                        {copiedId === message.id ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                      <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                        <ThumbsUp className="w-4 h-4 text-gray-400" />
                      </button>
                      <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                        <ThumbsDown className="w-4 h-4 text-gray-400" />
                      </button>
                      <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                        <RefreshCw className="w-4 h-4 text-gray-400" />
                      </button>
                    </motion.div>
                  )}

                  {/* Suggestion Chips */}
                  {message.suggestions && message.suggestions.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-4">
                      {message.suggestions.map((suggestion, i) => (
                        <motion.button
                          key={i}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: i * 0.05 }}
                          onClick={() => handleSuggestionClick(suggestion)}
                          className="text-xs px-4 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-gray-200 transition-all border border-white/10 hover:border-emerald-500/50 flex items-center gap-2"
                        >
                          <ArrowRight className="w-3 h-3" />
                          {suggestion}
                        </motion.button>
                      ))}
                    </div>
                  )}

                  {/* Timestamp */}
                  <p className={`text-xs mt-2 ${message.role === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Streaming Buffer */}
        {streamBuffer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="flex gap-3 max-w-[90%]">
              <div className="flex-shrink-0 w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-400 to-cyan-600 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div className="rounded-3xl px-5 py-4 bg-white/10 backdrop-blur-md border border-white/10 text-gray-100">
                <div className="text-sm whitespace-pre-wrap leading-relaxed">
                  {formatContent(streamBuffer)}
                  <motion.span 
                    animate={{ opacity: [1, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                    className="inline-block w-0.5 h-4 bg-emerald-400 ml-1"
                  />
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Typing Indicator */}
        {isTyping && !streamBuffer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="flex gap-3">
              <div className="flex-shrink-0 w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-400 to-cyan-600 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div className="rounded-3xl px-5 py-4 bg-white/10 backdrop-blur-md border border-white/10">
                <div className="flex gap-1.5">
                  <span className="w-2.5 h-2.5 bg-emerald-400 rounded-full typing-dot" />
                  <span className="w-2.5 h-2.5 bg-emerald-400 rounded-full typing-dot" style={{ animationDelay: '0.2s' }} />
                  <span className="w-2.5 h-2.5 bg-emerald-400 rounded-full typing-dot" style={{ animationDelay: '0.4s' }} />
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Ready to Complete Badge */}
        {isReady && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center"
          >
            <div className="flex items-center gap-3 flex-wrap justify-center">
                  <button
                onClick={async () => {
                  await advanceStage();
                }}
                className="px-5 py-3 bg-white/10 text-gray-100 rounded-full font-medium border border-white/20 hover:bg-white/20 transition-all"
              >
                Move to Next Stage
              </button>
              <button
                onClick={handleComplete}
                className="px-8 py-4 bg-gradient-to-r from-emerald-500 to-cyan-600 text-white rounded-full font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 hover:scale-105 transition-all flex items-center gap-3"
              >
                <CheckCircle2 className="w-5 h-5" />
                Continue with These Preferences
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </motion.div>
        )}

        {(isRanking || rankedDestinations.length > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/5 border border-white/10 rounded-2xl p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-white">Ranked Destinations</h4>
              {isRanking && <span className="text-xs text-emerald-300">Ranking...</span>}
            </div>
            <div className="space-y-2">
              {rankedDestinations.slice(0, 5).map((dest) => (
                <div key={dest.destination} className="rounded-xl bg-black/20 border border-white/10 px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">{dest.destination}</p>
                      <p className="text-xs text-gray-300">{dest.reasons?.join(' • ') || 'Matches your preferences'}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-300">{dest.score}</span>
                      <button
                        onClick={() => submitFeedback(dest.destination, 1, extracted)}
                        className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                        title="I like this"
                      >
                        <ThumbsUp className="w-3.5 h-3.5 text-gray-300" />
                      </button>
                      <button
                        onClick={() => submitFeedback(dest.destination, -1, extracted)}
                        className="p-1.5 rounded-lg hover:bg-white/10 transition-colors"
                        title="Less like this"
                      >
                        <ThumbsDown className="w-3.5 h-3.5 text-gray-300" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {activeAgentPanel && (
          <div className="bg-violet-500/10 border border-violet-400/30 rounded-2xl px-4 py-3 text-xs text-violet-200">
            {activeAgentPanel === 'compare' && 'Compare panel is active: I am focusing responses on destination comparison.'}
            {activeAgentPanel === 'itinerary' && 'Itinerary panel is active: I am now generating trip-day structure.'}
            {activeAgentPanel === 'budget' && 'Budget panel is active: I am now focusing on cost breakdown details.'}
          </div>
        )}

        {(isResearching || researchJob || researchResults) && (
          <div className="bg-blue-500/10 border border-blue-400/30 rounded-2xl px-4 py-3 text-xs text-blue-200">
            {isResearching && `Autonomous research running (${researchJob?.status || 'in_progress'})`}
            {!isResearching && researchJob?.status === 'completed' && `Autonomous research completed (${researchResults?.recommendations?.length || 0} recommendations)`}
            {!isResearching && researchJob?.status === 'failed' && 'Autonomous research failed'}
          </div>
        )}

        {researchResults?.recommendations?.length ? (
          <div className="bg-emerald-500/10 border border-emerald-400/30 rounded-2xl p-4">
            <p className="text-xs font-semibold text-emerald-200 mb-2">Autonomous Top Picks</p>
            <div className="space-y-2">
              {researchResults.recommendations.slice(0, 3).map((rec, idx) => (
                <div key={`${rec.destination}-${idx}`} className="rounded-xl bg-black/20 border border-emerald-400/20 px-3 py-2 flex items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-white">{rec.destination}</p>
                    <p className="text-xs text-gray-300">{(rec.reasons || []).slice(0, 2).join(' • ') || 'Strong match'}</p>
                  </div>
                  <button
                    onClick={async () => {
                      await trackRecommendationAccepted(rec.destination);
                      sendMessageStreaming(`Use ${rec.destination} as my final plan and build a detailed itinerary.`);
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

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestions (shown when few messages) */}
      {showSuggestions && messages.length <= 1 && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="px-6 py-4 bg-white/5 backdrop-blur-md border-t border-white/10"
        >
          <p className="text-xs text-gray-400 mb-3 font-medium flex items-center gap-2">
            <Zap className="w-3 h-3" />
            Quick Start
          </p>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_STARTS.map((start, i) => (
              <motion.button
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                onClick={() => handleSuggestionClick(start.prompt)}
                className="text-xs px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white transition-all border border-white/10 hover:border-emerald-500/50 text-left flex items-center gap-2"
              >
                <span className="text-lg">{start.icon}</span>
                {start.text}
              </motion.button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-white/5 backdrop-blur-md border-t border-white/10">
        <div className="flex gap-3 items-end">
          {/* Voice Input Button */}
          <button
            type="button"
            onClick={() => setIsListening(!isListening)}
            className={`p-4 rounded-2xl transition-all ${
              isListening 
                ? 'bg-red-500/20 border-red-500/50 animate-pulse' 
                : 'bg-white/5 hover:bg-white/10 border-white/10'
            } border`}
          >
            {isListening ? (
              <StopCircle className="w-5 h-5 text-red-400" />
            ) : (
              <Mic className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {/* Text Input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your dream trip..."
              className="w-full px-5 py-4 rounded-2xl border border-white/10 bg-white/5 focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 resize-none min-h-[56px] max-h-[200px] text-sm transition-all text-white placeholder:text-gray-500"
              rows={1}
              disabled={isTyping || isLoading}
            />
          </div>

          {/* Send Button */}
          <motion.button
            type="submit"
            disabled={!input.trim() || isTyping || isLoading}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="px-5 py-4 bg-gradient-to-br from-emerald-500 to-cyan-600 text-white rounded-2xl hover:from-emerald-600 hover:to-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 disabled:hover:scale-100"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </motion.button>
        </div>
        <p className="text-xs text-gray-500 mt-2 text-center">
          Press Enter to send, Shift+Enter for new line • AI-powered by TravelAI
        </p>
      </form>
    </div>
  );
}
