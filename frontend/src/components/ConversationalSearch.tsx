'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles } from 'lucide-react';
import { TravelRequest, Interest, TravelStyle } from '@/types/travel';
import { api } from '@/services/api';

interface ConversationalSearchProps {
  onSubmit: (data: TravelRequest) => void;
  isLoading?: boolean;
}

interface Message {
  id: string;
  role: 'bot' | 'user';
  text: string;
  suggestions?: string[];
}

const BUDGET_MAP: Record<string, { daily: number; total: number }> = {
  low: { daily: 75, total: 1500 },
  moderate: { daily: 175, total: 3500 },
  high: { daily: 375, total: 7500 },
  luxury: { daily: 600, total: 12000 },
};

function buildTravelRequest(extracted: Record<string, any>): TravelRequest {
  const budgetLevel = extracted.budget_level || 'moderate';
  const budget = BUDGET_MAP[budgetLevel] || BUDGET_MAP.moderate;
  const dailyBudget = extracted.budget_daily || budget.daily;

  const validInterestValues = [
    'nature','culture','adventure','relaxation','food',
    'nightlife','shopping','history','art','beaches','mountains','wildlife',
  ];
  const validInterests = (extracted.interests || []).filter((i: string) =>
    validInterestValues.includes(i)
  ) as Interest[];

  const travelingWith =
    extracted.traveling_with ||
    (extracted.has_kids ? 'family' :
      extracted.num_travelers === 1 ? 'solo' :
      extracted.num_travelers === 2 ? 'couple' : 'friends');

  return {
    origin: extracted.origin || 'Unknown',
    travel_start: extracted.travel_start,
    travel_end: extracted.travel_end,
    num_travelers: extracted.num_travelers || 1,
    num_recommendations: 5,
    user_preferences: {
      budget_daily: dailyBudget,
      budget_total: dailyBudget * 7,
      travel_style: (extracted.travel_style as TravelStyle) || TravelStyle.MODERATE,
      interests: validInterests,
      passport_country: extracted.passport_country || 'US',
      visa_preference: extracted.visa_preference || 'visa_free',
      traveling_with: travelingWith,
      preferred_weather: extracted.preferred_weather || undefined,
      accessibility_needs: [],
      dietary_restrictions: [],
    },
  };
}

export default function ConversationalSearch({ onSubmit, isLoading }: ConversationalSearchProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [history, setHistory] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  // Opening message
  useEffect(() => {
    setMessages([{
      id: '0',
      role: 'bot',
      text: "Hi! Describe your dream trip and I'll find perfect destinations — dates, who's coming, vibe, budget, anything you have in mind.",
      suggestions: [
        'Warm beach holiday in April with 2 kids',
        'City break in Europe next month, couple',
        'Family trip Easter holidays, budget-friendly',
      ],
    }]);
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isThinking) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsThinking(true);

    const newHistory = [...history, { role: 'user' as const, content: text }];
    setHistory(newHistory);

    try {
      const result = await api.travelChat(newHistory);

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'bot',
        text: result.reply,
        suggestions: result.ready ? [] : result.suggestions,
      };
      setMessages(prev => [...prev, botMsg]);

      const updatedHistory = [...newHistory, { role: 'assistant' as const, content: result.reply }];
      setHistory(updatedHistory);

      if (result.ready && result.extracted) {
        setTimeout(() => {
          onSubmit(buildTravelRequest(result.extracted));
        }, 1000);
      }
    } catch {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'bot',
        text: "Sorry, something went wrong. Try describing your trip again!",
      }]);
    } finally {
      setIsThinking(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [history, isThinking, onSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  return (
    <div className="flex flex-col h-full max-h-[600px]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 min-h-[400px]">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'bot' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center mr-2 flex-shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
              )}

              <div className="max-w-[80%] space-y-2">
                <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-white shadow-md border border-gray-100 text-gray-700'
                }`}>
                  {msg.text}
                </div>

                {/* Quick-reply suggestions */}
                {msg.role === 'bot' && msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 pl-1">
                    {msg.suggestions.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(s)}
                        disabled={isThinking || isLoading}
                        className="text-xs px-3 py-1.5 rounded-full border border-primary-200 bg-primary-50 text-primary-700 hover:bg-primary-100 transition-colors disabled:opacity-50"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Thinking dots */}
        {isThinking && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-start">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center mr-2 flex-shrink-0">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white shadow-md border border-gray-100 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-1.5">
                {[0, 1, 2].map(i => (
                  <motion.div
                    key={i}
                    className="w-2 h-2 rounded-full bg-primary-400"
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Searching for destinations */}
        {isLoading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center mr-2">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white shadow-md border border-gray-100 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full"
                />
                <span className="text-sm text-gray-600">Finding your perfect destinations…</span>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Text input — always visible */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-4 border-t border-gray-100"
      >
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isThinking || isLoading}
            placeholder="Tell me about your trip…"
            className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all text-sm disabled:opacity-50"
            autoFocus
          />
          <button
            onClick={() => sendMessage(inputValue)}
            disabled={!inputValue.trim() || isThinking || isLoading}
            className="px-4 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-40 transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </motion.div>
    </div>
  );
}
