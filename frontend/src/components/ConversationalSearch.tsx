'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, MapPin, Calendar, Users, Sparkles, ArrowRight, Check } from 'lucide-react';
import { TravelRequest, Interest, TravelStyle } from '@/types/travel';

interface ConversationalSearchProps {
  onSubmit: (data: TravelRequest) => void;
  isLoading?: boolean;
}

type MessageType = 'bot' | 'user';

interface Message {
  id: string;
  type: MessageType;
  text?: string;
  options?: Option[];
  isTyping?: boolean;
}

interface Option {
  id: string;
  label: string;
  value: string | number;
  icon?: string;
  description?: string;
}

const TRAVEL_STYLES: Option[] = [
  { id: 'budget', label: 'Budget Explorer', value: 'budget', icon: '🎒', description: 'Hostels, street food, adventures' },
  { id: 'moderate', label: 'Balanced Traveler', value: 'moderate', icon: '🧳', description: 'Mid-range comfort, good value' },
  { id: 'comfort', label: 'Comfort Seeker', value: 'comfort', icon: '🏨', description: 'Nice hotels, great dining' },
  { id: 'luxury', label: 'Luxury Experience', value: 'luxury', icon: '✨', description: '5-star, fine dining, premium' },
];

const TRAVELER_COUNTS: Option[] = [
  { id: '1', label: 'Just me', value: 1, icon: '🧍', description: 'Solo adventure' },
  { id: '2', label: 'Two of us', value: 2, icon: '👫', description: 'Couple or friend' },
  { id: '3-4', label: 'Small group', value: 3, icon: '👥', description: '3-4 travelers' },
  { id: '5+', label: 'Big group', value: 5, icon: '🎉', description: '5 or more' },
];

const TRIP_TYPES: Option[] = [
  { id: 'weekend', label: 'Quick getaway', value: 'weekend', icon: '⚡', description: '2-3 days' },
  { id: 'week', label: 'Week trip', value: 'week', icon: '📅', description: '5-7 days' },
  { id: 'extended', label: 'Extended vacation', value: 'extended', icon: '🌴', description: '10-14 days' },
  { id: 'long', label: 'Long adventure', value: 'long', icon: '🎒', description: '2+ weeks' },
];

const INTERESTS: Option[] = [
  { id: 'beaches', label: 'Beaches', value: 'beaches', icon: '🏖️' },
  { id: 'mountains', label: 'Mountains', value: 'mountains', icon: '🏔️' },
  { id: 'culture', label: 'Culture', value: 'culture', icon: '🏛️' },
  { id: 'food', label: 'Food', value: 'food', icon: '🍜' },
  { id: 'adventure', label: 'Adventure', value: 'adventure', icon: '🧗' },
  { id: 'relaxation', label: 'Relaxation', value: 'relaxation', icon: '🧘' },
  { id: 'nature', label: 'Nature', value: 'nature', icon: '🌿' },
  { id: 'history', label: 'History', value: 'history', icon: '📜' },
  { id: 'nightlife', label: 'Nightlife', value: 'nightlife', icon: '🌃' },
  { id: 'art', label: 'Art', value: 'art', icon: '🎨' },
];

const BUDGET_RANGES: Option[] = [
  { id: 'low', label: 'Under $100/day', value: 'low', icon: '💵', description: 'Budget-friendly' },
  { id: 'mid', label: '$100-250/day', value: 'mid', icon: '💰', description: 'Moderate spend' },
  { id: 'high', label: '$250-500/day', value: 'high', icon: '💎', description: 'Comfortable' },
  { id: 'luxury', label: '$500+/day', value: 'luxury', icon: '👑', description: 'No limits' },
];

export default function ConversationalSearch({ onSubmit, isLoading }: ConversationalSearchProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<Partial<TravelRequest>>({
    origin: '',
    travel_start: '',
    travel_end: '',
    num_travelers: 1,
    num_recommendations: 5,
    user_preferences: {
      budget_daily: 150,
      budget_total: 3000,
      travel_style: 'moderate',
      interests: [],
      passport_country: 'US',
      visa_preference: 'visa_free',
      traveling_with: 'solo',
      accessibility_needs: [],
      dietary_restrictions: [],
    },
  });
  const [inputValue, setInputValue] = useState('');
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize with first question
  useEffect(() => {
    addBotMessage("Hi there! ✨ I'm your AI travel assistant. Ready to find your perfect destination?", [
      { id: 'start', label: "Let's go! 🚀", value: 'start', icon: '' },
    ]);
  }, []);

  const addBotMessage = (text: string, options?: Option[]) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      type: 'bot',
      text,
      options,
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  const addUserMessage = (text: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      text,
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  const handleOptionSelect = (option: Option) => {
    addUserMessage(option.label);
    
    switch (currentStep) {
      case 0: // Start
        setTimeout(() => {
          addBotMessage("Where will you be traveling from? 📍");
          setCurrentStep(1);
        }, 500);
        break;
        
      case 1: // Origin - handled by text input
        break;
        
      case 2: // Trip type selected
        const tripType = option.value as string;
        const startDate = new Date();
        const endDate = new Date();
        
        if (tripType === 'weekend') {
          endDate.setDate(startDate.getDate() + 3);
        } else if (tripType === 'week') {
          endDate.setDate(startDate.getDate() + 7);
        } else if (tripType === 'extended') {
          endDate.setDate(startDate.getDate() + 14);
        } else {
          endDate.setDate(startDate.getDate() + 21);
        }
        
        setFormData((prev) => ({
          ...prev,
          travel_start: startDate.toISOString().split('T')[0],
          travel_end: endDate.toISOString().split('T')[0],
        }));
        
        setTimeout(() => {
          addBotMessage("How many people are traveling? 👥", TRAVELER_COUNTS);
          setCurrentStep(3);
        }, 500);
        break;
        
      case 3: // Number of travelers
        setFormData((prev) => ({
          ...prev,
          num_travelers: option.value as number,
        }));
        
        setTimeout(() => {
          addBotMessage("What's your travel style? 🎒", TRAVEL_STYLES);
          setCurrentStep(4);
        }, 500);
        break;
        
      case 4: // Travel style
        const style = option.value as TravelStyle;
        const budgetMap: Record<string, number> = {
          budget: 75,
          moderate: 175,
          comfort: 350,
          luxury: 600,
        };
        
        setFormData((prev) => ({
          ...prev,
          user_preferences: {
            ...prev.user_preferences!,
            travel_style: style,
            budget_daily: budgetMap[style],
            budget_total: budgetMap[style] * 7,
          },
        }));
        
        setTimeout(() => {
          addBotMessage("What are you interested in? Pick a few! 🎯", undefined);
          setCurrentStep(5);
        }, 500);
        break;
        
      case 6: // Budget
        const budgetVal = option.value as string;
        const budgetRanges: Record<string, { daily: number; total: number }> = {
          low: { daily: 75, total: 1500 },
          mid: { daily: 175, total: 3500 },
          high: { daily: 375, total: 7500 },
          luxury: { daily: 600, total: 12000 },
        };
        
        setFormData((prev) => ({
          ...prev,
          user_preferences: {
            ...prev.user_preferences!,
            budget_daily: budgetRanges[budgetVal].daily,
            budget_total: budgetRanges[budgetVal].total,
          },
        }));
        
        setTimeout(() => {
          addBotMessage("What type of weather do you prefer? ☀️", [
            { id: 'hot', label: 'Hot (30°C+)', value: 'hot', icon: '🔥' },
            { id: 'warm', label: 'Warm (20-30°C)', value: 'warm', icon: '☀️' },
            { id: 'mild', label: 'Mild (10-20°C)', value: 'mild', icon: '🌤️' },
            { id: 'cold', label: 'Cold (0-10°C)', value: 'cold', icon: '❄️' },
          ]);
          setCurrentStep(7);
        }, 500);
        break;
        
      case 7: // Weather preference
        setFormData((prev) => ({
          ...prev,
          user_preferences: {
            ...prev.user_preferences!,
            preferred_weather: option.value as string,
          },
        }));
        
        setTimeout(() => {
          addBotMessage("Perfect! Let me search for destinations tailored just for you... 🔍");
          setCurrentStep(8);
          
          setTimeout(() => {
            handleSubmit();
          }, 1500);
        }, 500);
        break;
    }
  };

  const handleTextSubmit = () => {
    if (!inputValue.trim()) return;
    
    addUserMessage(inputValue);
    
    if (currentStep === 1) {
      setFormData((prev) => ({ ...prev, origin: inputValue }));
      setInputValue('');
      
      setTimeout(() => {
        addBotMessage("What kind of trip are you looking for? 🌴", TRIP_TYPES);
        setCurrentStep(2);
      }, 500);
    }
  };

  const handleInterestToggle = (interest: Option) => {
    const isSelected = selectedInterests.includes(interest.id);
    let newInterests: string[];
    
    if (isSelected) {
      newInterests = selectedInterests.filter((i) => i !== interest.id);
    } else {
      newInterests = [...selectedInterests, interest.id];
    }
    
    setSelectedInterests(newInterests);
    
    setFormData((prev) => ({
      ...prev,
      user_preferences: {
        ...prev.user_preferences!,
        interests: newInterests as Interest[],
      },
    }));
  };

  const handleInterestsConfirm = () => {
    if (selectedInterests.length === 0) {
      addUserMessage("I'll keep my options open!");
    } else {
      const selectedLabels = INTERESTS
        .filter((i) => selectedInterests.includes(i.id))
        .map((i) => i.label)
        .join(', ');
      addUserMessage(selectedLabels);
    }
    
    setTimeout(() => {
      addBotMessage("What's your daily budget per person? 💰", BUDGET_RANGES);
      setCurrentStep(6);
    }, 500);
  };

  const handleSubmit = () => {
    if (formData.origin && formData.travel_start && formData.travel_end) {
      onSubmit(formData as TravelRequest);
    }
  };

  return (
    <div className="flex flex-col h-full max-h-[600px]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4 min-h-[400px]">
        <AnimatePresence>
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.type === 'bot' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center mr-2 flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
              )}
              
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.type === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-white shadow-md border border-gray-100'
                }`}
              >
                {message.text && (
                  <p className={`text-sm ${message.type === 'user' ? 'text-white' : 'text-gray-700'}`}>
                    {message.text}
                  </p>
                )}
                
                {/* Options */}
                {message.options && (
                  <div className="mt-3 space-y-2">
                    {message.options.map((option) => (
                      <motion.button
                        key={option.id}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => handleOptionSelect(option)}
                        className="w-full flex items-center gap-3 p-3 rounded-xl bg-gray-50 hover:bg-primary-50 border border-gray-100 hover:border-primary-200 transition-colors text-left"
                      >
                        {option.icon && (
                          <span className="text-xl">{option.icon}</span>
                        )}
                        <div>
                          <p className="font-medium text-gray-900">{option.label}</p>
                          {option.description && (
                            <p className="text-xs text-gray-500">{option.description}</p>
                          )}
                        </div>
                        <ArrowRight className="w-4 h-4 text-gray-400 ml-auto" />
                      </motion.button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {/* Interest Selection */}
        {currentStep === 5 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-600 flex items-center justify-center mr-2 flex-shrink-0">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div className="bg-white shadow-md border border-gray-100 rounded-2xl px-4 py-3 max-w-[80%]">
              <div className="grid grid-cols-2 gap-2 mb-3">
                {INTERESTS.map((interest) => {
                  const isSelected = selectedInterests.includes(interest.id);
                  return (
                    <motion.button
                      key={interest.id}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => handleInterestToggle(interest)}
                      className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${
                        isSelected
                          ? 'bg-primary-50 border-primary-500'
                          : 'bg-gray-50 border-gray-100 hover:border-primary-200'
                      }`}
                    >
                      <span>{interest.icon}</span>
                      <span className="text-sm">{interest.label}</span>
                      {isSelected && <Check className="w-3 h-3 text-primary-600 ml-auto" />}
                    </motion.button>
                  );
                })}
              </div>
              <button
                onClick={handleInterestsConfirm}
                className="w-full py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition-colors"
              >
                Continue →
              </button>
            </div>
          </motion.div>
        )}
        
        {/* Loading */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
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
                <span className="text-sm text-gray-600">Finding your perfect destinations...</span>
              </div>
            </div>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      {currentStep === 1 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 border-t border-gray-100"
        >
          <div className="flex gap-2">
            <div className="relative flex-1">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleTextSubmit()}
                placeholder="Type your city..."
                className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all"
              />
            </div>
            <button
              onClick={handleTextSubmit}
              disabled={!inputValue.trim()}
              className="px-4 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </motion.div>
      )}
    </div>
  );
}
