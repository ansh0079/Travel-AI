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
  RefreshCw,
  CheckCircle2,
  ArrowRight,
  X,
  MessageSquare,
  Zap,
  TrendingUp,
  Shield,
} from 'lucide-react';
import { api, TravelPreferences } from '@/services/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  suggestions?: string[];
  isStreaming?: boolean;
}

interface ExtractedPreferences {
  destinations?: string[];
  origin?: string;
  travel_dates?: { start: string; end: string };
  budget_level?: 'budget' | 'moderate' | 'luxury' | 'ultra-luxury';
  interests?: string[];
  traveling_with?: 'solo' | 'couple' | 'family' | 'friends';
  intent?: string;
  [key: string]: any;
}

interface ModernChatProps {
  onComplete: (preferences: TravelPreferences) => void;
  sessionId?: string;
  isLoading?: boolean;
}

const SUGGESTION_CATEGORIES = [
  { icon: MapPin, label: 'Destination Ideas', prompt: 'Show me unique destination ideas' },
  { icon: Wallet, label: 'Budget Tips', prompt: 'How can I travel on a budget?' },
  { icon: Calendar, label: 'Best Time to Visit', prompt: "When's the best time to travel?" },
  { icon: Camera, label: 'Photography Spots', prompt: 'Best photography locations' },
  { icon: Utensils, label: 'Food & Cuisine', prompt: 'Tell me about local food scenes' },
  { icon: Shield, label: 'Travel Safety', prompt: 'Safety tips for travelers' },
];

const QUICK_STARTS = [
  '🏖️ Beach vacation under $2000',
  '🏔️ Mountain adventure in Europe',
  '🏛️ Cultural city break in Asia',
  '🌴 Tropical family getaway',
];

export default function ModernChat({ onComplete, sessionId: propSessionId, isLoading }: ModernChatProps) {
  const [sessionId, setSessionId] = useState(propSessionId || `session_${Date.now()}`);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [extracted, setExtracted] = useState<ExtractedPreferences | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [streamBuffer, setStreamBuffer] = useState('');

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
        role: 'assistant',
        content: `Hi there! 👋 I'm your AI travel assistant.

Tell me about your dream trip in your own words. Where do you want to go? When? Who's coming? What do you love doing? What's your budget?

**Examples:**
• *"I want a beach vacation in Thailand for 2 weeks in December with my partner, mid-range budget"*
• *"Family trip to Japan with kids aged 5 and 8, interested in culture and food, about $300/day"*
• *"Solo backpacking through Europe this summer, love hiking and meeting locals, tight budget"*

What's on your mind? 🌍`,
        timestamp: new Date(),
        suggestions: QUICK_STARTS,
      }]);
    }
  }, []);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isTyping) return;

    const userMessage: Message = {
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
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        suggestions: data.suggestions,
      };

      setMessages(prev => [...prev, assistantMessage]);
      setExtracted(data.extracted_preferences);
      setIsReady(data.is_ready_for_recommendations);

    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I had trouble processing that. Could you try again?',
        timestamp: new Date(),
        suggestions: ['Try again'],
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const sendMessageStreaming = async (text: string) => {
    if (!text.trim() || isTyping) return;

    const userMessage: Message = {
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
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api/v1'}/chat/message/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
        }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No reader available');

      let fullResponse = '';
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;

        if (value) {
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.token) {
                  fullResponse += data.token;
                  setStreamBuffer(fullResponse);
                }

                if (data.done) {
                  setExtracted(data.extracted_preferences);
                  setIsReady(data.is_ready);
                  
                  // Add complete message
                  setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: fullResponse,
                    timestamp: new Date(),
                  }]);
                }

                if (data.error) {
                  throw new Error(data.error);
                }
              } catch (e) {
                console.warn('Parse error:', e);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      setMessages(prev => [...prev, {
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
    // Use streaming for better UX
    sendMessageStreaming(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    sendMessageStreaming(suggestion);
  };

  const handleComplete = () => {
    if (!extracted) return;

    const travelPrefs: TravelPreferences = {
      origin: extracted.origin || '',
      destinations: extracted.destinations || [],
      travel_start: extracted.travel_dates?.start || '',
      travel_end: extracted.travel_dates?.end || '',
      budget_level: extracted.budget_level || 'moderate',
      interests: extracted.interests || [],
      traveling_with: extracted.traveling_with || 'solo',
      passport_country: 'US',
      visa_preference: extracted.visa_preference || 'visa_free',
      weather_preference: extracted.weather_preference || 'mild',
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

  return (
    <div className="flex flex-col h-[700px] bg-gradient-to-b from-slate-50 to-white rounded-3xl border border-slate-200 shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-white/80 backdrop-blur-sm border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-lg">AI Travel Assistant</h3>
            <p className="text-xs text-slate-500 flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Powered by advanced AI
            </p>
          </div>
        </div>

        {extracted && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-3"
          >
            <div className="text-right">
              <p className="text-xs text-slate-500">Profile Complete</p>
              <p className="text-sm font-bold text-slate-900">{progress}%</p>
            </div>
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-white" />
            </div>
          </motion.div>
        )}
      </div>

      {/* Progress Bar */}
      <AnimatePresence>
        {extracted && Object.keys(extracted).length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-slate-50 border-b border-slate-200 overflow-hidden"
          >
            <div className="px-6 py-3">
              <div className="flex items-center gap-4 text-xs">
                <span className="text-slate-600 font-medium">Extracted:</span>
                <div className="flex flex-wrap gap-2">
                  {extracted.destinations && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-md flex items-center gap-1">
                      <MapPin className="w-3 h-3" />
                      {extracted.destinations.join(', ')}
                    </span>
                  )}
                  {extracted.budget_level && (
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded-md flex items-center gap-1">
                      <Wallet className="w-3 h-3" />
                      {extracted.budget_level}
                    </span>
                  )}
                  {extracted.traveling_with && (
                    <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-md flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      {extracted.traveling_with}
                    </span>
                  )}
                  {extracted.travel_dates && (
                    <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded-md flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {extracted.travel_dates.start}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-slate-50/50 to-white">
        <AnimatePresence>
          {messages.map((message, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-3xl px-5 py-4 ${
                  message.role === 'user'
                    ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg shadow-blue-200'
                    : 'bg-white border border-slate-200 text-slate-800 shadow-md'
                }`}
              >
                {/* Message content with markdown-like formatting */}
                <div className="text-sm whitespace-pre-wrap leading-relaxed">
                  {message.content.split('**').map((part, i) =>
                    i % 2 === 1 ? <strong key={i}>{part}</strong> : part
                  )}
                </div>

                {/* Suggestion chips */}
                {message.suggestions && message.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-4">
                    {message.suggestions.map((suggestion, i) => (
                      <button
                        key={i}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="text-xs px-4 py-2 rounded-full bg-gradient-to-r from-blue-50 to-purple-50 text-slate-700 hover:from-blue-100 hover:to-purple-100 transition-all border border-slate-200 hover:border-blue-300 flex items-center gap-1.5"
                      >
                        <ArrowRight className="w-3 h-3" />
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}

                {/* Timestamp */}
                <p className={`text-xs mt-2 ${message.role === 'user' ? 'text-blue-200' : 'text-slate-400'}`}>
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Streaming buffer */}
        {streamBuffer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="max-w-[85%] rounded-3xl px-5 py-4 bg-white border border-slate-200 text-slate-800 shadow-md">
              <div className="text-sm whitespace-pre-wrap leading-relaxed">
                {streamBuffer}
                <span className="inline-block w-2 h-4 bg-blue-600 ml-1 animate-pulse" />
              </div>
            </div>
          </motion.div>
        )}

        {/* Typing indicator */}
        {isTyping && !streamBuffer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="bg-white border border-slate-200 rounded-3xl px-5 py-4 shadow-md">
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2.5 h-2.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2.5 h-2.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </motion.div>
        )}

        {/* Ready to complete badge */}
        {isReady && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center"
          >
            <button
              onClick={handleComplete}
              className="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-full font-semibold shadow-lg shadow-green-200 hover:shadow-xl hover:scale-105 transition-all flex items-center gap-2"
            >
              <CheckCircle2 className="w-5 h-5" />
              Continue with These Preferences
              <ArrowRight className="w-5 h-5" />
            </button>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestions (shown when few messages) */}
      {showSuggestions && messages.length <= 1 && (
        <div className="px-6 py-4 bg-white/80 backdrop-blur-sm border-t border-slate-200">
          <p className="text-xs text-slate-500 mb-3 font-medium">Quick Start</p>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_STARTS.map((start, i) => (
              <button
                key={i}
                onClick={() => handleSuggestionClick(start)}
                className="text-xs px-4 py-3 rounded-xl bg-gradient-to-r from-slate-50 to-slate-100 text-slate-700 hover:from-blue-50 hover:to-purple-50 transition-all border border-slate-200 hover:border-blue-300 text-left"
              >
                {start}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-slate-200">
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your dream trip..."
              className="w-full px-5 py-4 rounded-2xl border border-slate-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 resize-none min-h-[56px] max-h-[200px] text-sm transition-all"
              rows={1}
              disabled={isTyping || isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isTyping || isLoading}
            className="px-5 py-4 bg-gradient-to-br from-blue-600 to-purple-600 text-white rounded-2xl hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-200 hover:shadow-xl hover:scale-105 disabled:hover:scale-100"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2 text-center">
          Press Enter to send, Shift+Enter for new line • AI-powered travel planning
        </p>
      </form>
    </div>
  );
}
