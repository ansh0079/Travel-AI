'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot, User, Send, Sparkles, Search,
  Calendar, Lightbulb,
  Loader2, Compass, Gem
} from 'lucide-react';
import { api } from '@/services/api';

interface Message {
  id: string;
  type: 'user' | 'agent' | 'system';
  text: string;
  data?: any;
  timestamp: Date;
}

interface AgentCapability {
  id: string;
  label: string;
  icon: React.ReactNode;
  description: string;
  example: string;
}

const CAPABILITIES: AgentCapability[] = [
  {
    id: 'research',
    label: 'Deep Research',
    icon: <Search className="w-5 h-5" />,
    description: 'Comprehensive destination analysis',
    example: 'Research Bali for a cultural trip'
  },
  {
    id: 'compare',
    label: 'Compare Places',
    icon: <Compass className="w-5 h-5" />,
    description: 'Side-by-side destination comparison',
    example: 'Compare Tokyo vs Seoul'
  },
  {
    id: 'gems',
    label: 'Hidden Gems',
    icon: <Gem className="w-5 h-5" />,
    description: 'Discover off-the-beaten-path spots',
    example: 'Find hidden gems in Portugal'
  },
  {
    id: 'itinerary',
    label: 'Plan Itinerary',
    icon: <Calendar className="w-5 h-5" />,
    description: 'Day-by-day trip planning',
    example: 'Plan a 5-day Italy itinerary'
  }
];

export default function AIAgentChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState<'idle' | 'researching' | 'error'>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          id: 'welcome',
          type: 'agent',
          text: "Hello! I'm your AI Travel Research Agent 🌍\n\nI can independently research destinations, compare places, find hidden gems, and plan itineraries using real-time web search and travel data.\n\nWhat would you like me to help you with?",
          timestamp: new Date()
        }
      ]);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const addMessage = (type: 'user' | 'agent' | 'system', text: string, data?: any) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      type,
      text,
      data,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    addMessage('user', userMessage);
    setInputValue('');
    setIsLoading(true);
    setAgentStatus('researching');

    try {
      // First, use the chat endpoint for intent detection
      const chatData = await api.agentChat(userMessage);
      
      if (chatData.response_type === 'research' && chatData.data) {
        addMessage('agent', chatData.message);
        displayResearchResults(chatData.data);
      } else if (chatData.response_type === 'comparison_prompt') {
        addMessage('agent', chatData.message);
        // Trigger comparison flow
        await handleComparison(userMessage);
      } else if (chatData.response_type === 'gems_prompt') {
        addMessage('agent', chatData.message);
        // Extract region and search
        const region = extractRegion(userMessage);
        if (region) {
          await handleHiddenGems(region);
        }
      } else if (chatData.response_type === 'itinerary_prompt') {
        addMessage('agent', chatData.message);
        const { destination, days } = extractItineraryInfo(userMessage);
        if (destination && days) {
          await handleItineraryResearch(destination, days);
        }
      } else {
        // General response - try to determine intent
        await processGeneralQuery(userMessage);
      }
    } catch (error) {
      console.error('Agent error:', error);
      addMessage('agent', "I'm sorry, I encountered an error while researching. Please try again.");
      setAgentStatus('error');
    } finally {
      setIsLoading(false);
      setAgentStatus('idle');
    }
  };

  const processGeneralQuery = async (query: string) => {
    const lowerQuery = query.toLowerCase();
    
    // Check for comparison intent
    if (lowerQuery.includes('compare') || lowerQuery.includes(' vs ') || lowerQuery.includes(' versus ')) {
      await handleComparison(query);
      return;
    }
    
    // Check for hidden gems intent
    if (lowerQuery.includes('hidden gem') || lowerQuery.includes('secret') || lowerQuery.includes('off beaten')) {
      const region = extractRegion(query) || extractDestination(query);
      if (region) {
        await handleHiddenGems(region);
        return;
      }
    }
    
    // Check for itinerary intent
    if (lowerQuery.includes('itinerary') || lowerQuery.includes('plan') || lowerQuery.includes('schedule')) {
      const { destination, days } = extractItineraryInfo(query);
      if (destination) {
        await handleItineraryResearch(destination, days || 5);
        return;
      }
    }
    
    // Default to destination research
    const destination = extractDestination(query);
    if (destination) {
      await handleDestinationResearch(destination);
    } else {
      addMessage('agent', "I can help you research destinations! Try asking me something like:\n\n• 'Research Bali for beaches and culture'\n• 'Compare Paris vs Rome'\n• 'Find hidden gems in Thailand'\n• 'Plan a 7-day Japan itinerary'");
    }
  };

  const handleDestinationResearch = async (destination: string) => {
    addMessage('system', `🔍 Researching ${destination}...`, { loading: true });
    
    try {
      const data = await api.agentResearch(destination);
      if (data.status === 'success') {
        displayResearchResults(data.result);
      }
    } catch (error) {
      addMessage('agent', `Sorry, I couldn't complete the research for ${destination}.`);
    }
  };

  const handleComparison = async (query: string) => {
    // Extract destinations from query
    const destinations = extractDestinationsForComparison(query);
    
    if (destinations.length < 2) {
      addMessage('agent', "To compare destinations, please mention at least two places. For example: 'Compare Tokyo and Seoul' or 'Paris vs London'");
      return;
    }
    
    addMessage('system', `📊 Comparing ${destinations.join(' vs ')}...`, { loading: true });
    
    try {
      const data = await api.agentCompare(destinations.slice(0, 4));
      if (data.status === 'success') {
        displayComparisonResults(data.result);
      }
    } catch (error) {
      addMessage('agent', "Sorry, I couldn't complete the comparison.");
    }
  };

  const handleHiddenGems = async (region: string) => {
    addMessage('system', `💎 Searching for hidden gems in ${region}...`, { loading: true });
    
    try {
      const data = await api.agentHiddenGems(region);
      if (data.status === 'success') {
        displayHiddenGems(data.hidden_gems, region);
      }
    } catch (error) {
      addMessage('agent', `Sorry, I couldn't find hidden gems for ${region}.`);
    }
  };

  const handleItineraryResearch = async (destination: string, days: number) => {
    addMessage('system', `📅 Planning ${days}-day itinerary for ${destination}...`, { loading: true });
    
    try {
      const data = await api.agentItineraryResearch(destination, days);
      if (data.status === 'success') {
        displayItineraryResults(data.result);
      }
    } catch (error) {
      addMessage('agent', `Sorry, I couldn't plan the itinerary for ${destination}.`);
    }
  };

  const displayResearchResults = (result: any) => {
    let text = `## Research Results: ${result.destination}\n\n`;
    
    if (result.agent_insights) {
      text += `**🤖 Agent Insights:** ${result.agent_insights}\n\n`;
    }
    
    if (result.general_info?.key_findings?.length > 0) {
      text += `**📍 Key Information:**\n`;
      result.general_info.key_findings.slice(0, 3).forEach((finding: string) => {
        text += `• ${finding}\n`;
      });
      text += '\n';
    }
    
    if (result.current_events?.events?.length > 0) {
      text += `**🎉 Current Events:**\n`;
      result.current_events.events.slice(0, 3).forEach((event: any) => {
        text += `• ${event.title}\n`;
      });
      text += '\n';
    }
    
    if (result.travel_tips?.tips?.length > 0) {
      text += `**💡 Travel Tips:**\n`;
      result.travel_tips.tips.slice(0, 2).forEach((tip: string) => {
        text += `• ${tip.substring(0, 150)}...\n`;
      });
    }
    
    addMessage('agent', text, result);
  };

  const displayComparisonResults = (result: any) => {
    let text = `## Destination Comparison\n\n`;
    
    if (result.destinations?.length > 0) {
      result.destinations.forEach((dest: any, idx: number) => {
        if (dest.destination) {
          text += `**${idx + 1}. ${dest.destination}**\n`;
          if (dest.agent_insights) {
            text += `${dest.agent_insights}\n`;
          }
          text += '\n';
        }
      });
    }
    
    if (result.recommendation) {
      text += `\n**🎯 Recommendation:** ${result.recommendation}`;
    }
    
    addMessage('agent', text, result);
  };

  const displayHiddenGems = (gems: any[], region: string) => {
    let text = `## 💎 Hidden Gems in ${region}\n\n`;
    
    if (gems.length === 0) {
      text += "I couldn't find specific hidden gems, but try exploring smaller towns and asking locals for recommendations!";
    } else {
      gems.slice(0, 5).forEach((gem, idx) => {
        text += `**${idx + 1}. ${gem.name}**\n`;
        if (gem.description) {
          text += `${gem.description.substring(0, 200)}...\n`;
        }
        text += '\n';
      });
    }
    
    addMessage('agent', text, { gems });
  };

  const displayItineraryResults = (result: any) => {
    let text = `## 📅 ${result.days}-Day Itinerary: ${result.destination}\n\n`;
    
    if (result.daily_plans?.length > 0) {
      result.daily_plans.forEach((day: any) => {
        text += `**Day ${day.day}** - ${day.theme.charAt(0).toUpperCase() + day.theme.slice(1)}\n`;
        text += `• Plan activities focused on ${day.theme}\n`;
        text += `• Explore key attractions\n`;
        text += `• Experience local culture\n\n`;
      });
    }
    
    if (result.must_see?.length > 0) {
      text += `**🌟 Must-See Attractions:**\n`;
      result.must_see.slice(0, 5).forEach((attraction: string) => {
        text += `• ${attraction}\n`;
      });
    }
    
    addMessage('agent', text, result);
  };

  // Helper functions for extracting info from natural language
  const extractDestination = (text: string): string | null => {
    const patterns = [
      /research\s+([A-Za-z\s]+?)(?:\s+for|\s+in\s+2024|$)/i,
      /about\s+([A-Za-z\s]+?)(?:\s+\?|$)/i,
      /plan.*?(?:trip|visit)\s+(?:to\s+)?([A-Za-z\s]+?)(?:\s+for|$)/i,
      /visit\s+([A-Za-z\s]+?)(?:\s+\?|$)/i
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }
    
    // Fallback: extract capitalized words
    const words = text.split(' ');
    const capitalized = words.filter(w => w[0] === w[0]?.toUpperCase() && w.length > 2);
    if (capitalized.length > 0) {
      return capitalized.slice(0, 2).join(' ');
    }
    
    return null;
  };

  const extractRegion = (text: string): string | null => {
    const patterns = [
      /in\s+([A-Za-z\s]+?)(?:\?|$)/i,
      /(?:region|area|part)\s+(?:of\s+)?([A-Za-z\s]+?)(?:\?|$)/i
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }
    
    return null;
  };

  const extractDestinationsForComparison = (text: string): string[] => {
    const destinations: string[] = [];
    
    // Pattern: "Compare X and Y" or "X vs Y" or "X versus Y"
    const patterns = [
      /compare\s+([A-Za-z]+)\s+(?:and|vs|versus)\s+([A-Za-z]+)/i,
      /([A-Za-z]+)\s+(?:vs|versus)\s+([A-Za-z]+)/i
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        destinations.push(match[1], match[2]);
        return destinations;
      }
    }
    
    // Fallback: extract capitalized words as potential destinations
    const words = text.split(' ');
    const capitalized = words.filter(w => w[0] === w[0]?.toUpperCase() && w.length > 2);
    return capitalized.slice(0, 4);
  };

  const extractItineraryInfo = (text: string): { destination: string | null; days: number | null } => {
    const destination = extractDestination(text);
    
    // Extract days
    const dayMatch = text.match(/(\d+)[-\s]?(?:day|days)/i);
    const days = dayMatch ? parseInt(dayMatch[1]) : null;
    
    return { destination, days };
  };

  const handleCapabilityClick = (capability: AgentCapability) => {
    setInputValue(capability.example);
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-2xl shadow-xl overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold">AI Research Agent</h3>
              <div className="flex items-center gap-2 text-white/70 text-sm">
                {agentStatus === 'researching' ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Researching...
                  </>
                ) : (
                  <>
                    <span className="w-2 h-2 rounded-full bg-green-400" />
                    Online • Autonomous
                  </>
                )}
              </div>
            </div>
          </div>
          <Sparkles className="w-6 h-6 text-white/50" />
        </div>
      </div>

      {/* Capabilities Bar */}
      <div className="bg-gray-50 px-4 py-3 border-b">
        <p className="text-xs text-gray-500 mb-2">I can help you:</p>
        <div className="flex gap-2 overflow-x-auto">
          {CAPABILITIES.map(cap => (
            <button
              key={cap.id}
              onClick={() => handleCapabilityClick(cap)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-lg border border-gray-200 hover:border-violet-300 hover:bg-violet-50 transition-colors text-xs whitespace-nowrap"
            >
              <span className="text-violet-600">{cap.icon}</span>
              <span className="font-medium text-gray-700">{cap.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`flex ${
                message.type === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.type !== 'user' && (
                <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-2 flex-shrink-0 ${
                  message.type === 'agent' 
                    ? 'bg-gradient-to-br from-violet-500 to-purple-600' 
                    : 'bg-gray-200'
                }`}>
                  {message.type === 'agent' ? (
                    <Bot className="w-4 h-4 text-white" />
                  ) : (
                    <Loader2 className="w-4 h-4 text-gray-600 animate-spin" />
                  )}
                </div>
              )}
              
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  message.type === 'user'
                    ? 'bg-violet-600 text-white'
                    : message.type === 'system'
                    ? 'bg-gray-100 text-gray-600'
                    : 'bg-white border border-gray-200 text-gray-800'
                }`}
              >
                <div className="text-sm whitespace-pre-line">{message.text}</div>
                
                {message.data && message.type === 'agent' && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Lightbulb className="w-3 h-3" />
                      <span>AI-Generated Research</span>
                    </div>
                  </div>
                )}
              </div>
              
              {message.type === 'user' && (
                <div className="w-8 h-8 rounded-full bg-violet-100 flex items-center justify-center ml-2 flex-shrink-0">
                  <User className="w-4 h-4 text-violet-600" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask me to research, compare, or plan..."
              disabled={isLoading}
              className="w-full pl-4 pr-10 py-3 rounded-xl border border-gray-200 focus:border-violet-500 focus:ring-2 focus:ring-violet-200 transition-all disabled:bg-gray-50"
            />
            {inputValue && (
              <button
                onClick={() => setInputValue('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            )}
          </div>
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="px-4 py-3 bg-violet-600 text-white rounded-xl hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        
        {/* Quick Suggestions */}
        <div className="mt-2 flex gap-2 overflow-x-auto">
          {[
            "Research Bali",
            "Compare Tokyo vs Seoul",
            "Hidden gems in Portugal",
            "Plan 5-day Italy trip"
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setInputValue(suggestion)}
              className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-600 whitespace-nowrap transition-colors"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
