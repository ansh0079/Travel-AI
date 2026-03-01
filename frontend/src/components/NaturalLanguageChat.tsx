'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, Loader2, MapPin, Calendar, Users, Heart, Wallet } from 'lucide-react';
import { api, TravelPreferences } from '@/services/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  suggestions?: string[];
}

interface NaturalLanguageChatProps {
  onComplete: (preferences: TravelPreferences) => void;
  isLoading?: boolean;
}

const WELCOME_MESSAGE = `Hi there! 👋 I'm your AI travel assistant.

Tell me about your dream trip in your own words — where you want to go, when, who's coming, what you love doing, your budget... anything!

For example:
• "I want a beach vacation in Thailand for 2 weeks in December with my partner, mid-range budget"
• "Family trip to Japan with kids aged 5 and 8, interested in culture and food, about $300/day"
• "Solo backpacking through Europe this summer, love hiking and meeting locals, tight budget"

What's on your mind?`;

export default function NaturalLanguageChat({ onComplete, isLoading }: NaturalLanguageChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: WELCOME_MESSAGE }
  ]);
  const [input, setInput] = useState('');
  const [extracted, setExtracted] = useState<Partial<TravelPreferences> | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isTyping) return;

    const userMessage: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const data = await api.travelChat([...messages, userMessage].map(m => ({
        role: m.role,
        content: m.content
      })));
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.reply,
        suggestions: data.suggestions || []
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setExtracted(data.extracted);
      setIsReady(data.ready);

      // If ready, auto-submit after a short delay
      if (data.ready) {
        setTimeout(() => {
          handleComplete(data.extracted);
        }, 2000);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I had trouble processing that. Could you try again?',
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleComplete = (prefs: Partial<TravelPreferences>) => {
    // Convert extracted data to TravelPreferences format
    const travelPrefs: TravelPreferences = {
      origin: prefs.origin || '',
      destinations: prefs.destinations || [],
      travel_start: prefs.travel_start || '',
      travel_end: prefs.travel_end || '',
      budget_level: prefs.budget_level || 'moderate',
      interests: prefs.interests || [],
      traveling_with: prefs.traveling_with || 'solo',
      passport_country: prefs.passport_country || 'US',
      visa_preference: prefs.visa_preference || 'visa_free',
      weather_preference: prefs.preferred_weather || 'warm',
      num_travelers: prefs.num_travelers || 1,
      has_kids: prefs.has_kids || false,
      kids_ages: prefs.kids_ages || [],
      activity_pace: prefs.activity_pace || 'moderate',
      accommodation_type: prefs.accommodation_type,
      dietary_restrictions: prefs.dietary_restrictions || [],
      accessibility_needs: prefs.accessibility_needs || [],
      special_occasion: prefs.special_occasion,
      nightlife_priority: prefs.nightlife_priority,
      car_hire: prefs.car_hire,
      flight_class: prefs.flight_class,
      past_destinations: prefs.past_destinations || [],
      special_requests: prefs.special_requests || '',
    };
    
    onComplete(travelPrefs);
  };

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion);
  };

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
    }
  }, [input]);

  return (
    <div className="flex flex-col h-[600px] bg-gradient-to-b from-blue-50/50 to-white rounded-2xl border border-blue-100 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-white border-b border-blue-100 flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900">AI Travel Assistant</h3>
          <p className="text-xs text-gray-500">Natural conversation • Extracts your preferences</p>
        </div>
        {extracted && (
          <div className="ml-auto flex items-center gap-2">
            <ExtractedInfoBadge extracted={extracted} />
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence>
          {messages.map((message, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                
                {/* Suggestion buttons */}
                {message.suggestions && message.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {message.suggestions.map((suggestion, i) => (
                      <button
                        key={i}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="text-xs px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors border border-blue-200"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-100">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your dream trip..."
            className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 resize-none min-h-[50px] max-h-[120px]"
            rows={1}
            disabled={isTyping || isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping || isLoading}
            className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
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
  );
}

// Component to show extracted info badge
function ExtractedInfoBadge({ extracted }: { extracted: Partial<TravelPreferences> }) {
  const filledFields = Object.entries(extracted).filter(([_, v]) => {
    if (v === null || v === undefined) return false;
    if (Array.isArray(v)) return v.length > 0;
    if (typeof v === 'boolean') return true;
    return Boolean(v);
  }).length;

  const totalFields = Object.keys(extracted).length;
  const progress = Math.round((filledFields / Math.max(totalFields, 1)) * 100);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-xs">
      <div className="w-2 h-2 bg-green-500 rounded-full" />
      {progress}% complete
    </div>
  );
}
