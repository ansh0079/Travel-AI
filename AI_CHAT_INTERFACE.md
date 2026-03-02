# Enhanced AI Chat Interface

## Overview

The new AI chat interface provides a **ChatGPT-like conversational experience** for travel planning, with significant improvements over the previous implementation.

## Key Features

### ✨ What's New

1. **Conversation Memory & Context**
   - Remembers entire conversation history
   - Maintains session state across messages
   - Context-aware responses

2. **Streaming Responses**
   - Real-time typing effect (like ChatGPT)
   - Lower perceived wait time
   - Better user experience

3. **Automatic Preference Extraction**
   - AI automatically extracts travel preferences from conversation
   - No manual form filling required
   - Real-time progress tracking

4. **Smart Suggestions**
   - Context-aware conversation suggestions
   - Quick-start templates
   - Intent-based recommendations

5. **Rich Message Formatting**
   - Markdown support (bold, lists, etc.)
   - Structured information display
   - Emoji-enhanced responses

6. **Action Execution**
   - Search flights, hotels, attractions through chat
   - Get weather forecasts
   - Find events and activities

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ModernChat.tsx                                   │   │
│  │  - Streaming SSE client                          │   │
│  │  - Real-time typing indicator                    │   │
│  │  - Extracted preferences display                 │   │
│  │  - Smart suggestion chips                        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/SSE
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │  chat_routes.py                                   │   │
│  │  - /chat/message (standard)                      │   │
│  │  - /chat/message/stream (SSE streaming)          │   │
│  │  - /chat/session/{id} (session info)             │   │
│  │  - /chat/action (execute actions)                │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  chat_service.py                                  │   │
│  │  - Conversation memory management                │   │
│  │  - Preference extraction                         │   │
│  │  - Intent recognition                            │   │
│  │  - Context-aware responses                       │   │
│  │  - Action execution                              │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              AI Providers (OpenAI/DeepSeek)              │
│  - GPT-3.5-turbo / GPT-4                                │
│  - DeepSeek-chat                                        │
│  - Streaming completions                                │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. Send Message (Standard)

```http
POST /api/v1/chat/message
Content-Type: application/json
Authorization: Bearer {token}

{
  "message": "I want a beach vacation in Thailand for 2 weeks in December",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "session_id": "session_123",
  "response": "Thailand is perfect for beach vacations! December is ideal...",
  "extracted_preferences": {
    "destinations": ["Thailand"],
    "travel_dates": {"start": "2024-12", "end": "2024-12"},
    "budget_level": "moderate",
    "intent": "recommendation"
  },
  "is_ready_for_recommendations": true,
  "suggestions": ["✈️ Search flights", "🏨 Find accommodations"]
}
```

### 2. Send Message (Streaming)

```http
POST /api/v1/chat/message/stream
Content-Type: application/json
Authorization: Bearer {token}

{
  "message": "Tell me about Tokyo",
  "session_id": "session_123"
}
```

**Response:** Server-Sent Events (SSE) stream
```
data: {"token": "Tok"}
data: {"token": "yo"}
data: {"token": " is"}
data: {"token": " an"}
data: {"token": " amazing"}
...
data: {"done": true, "extracted_preferences": {...}, "is_ready": false}
```

### 3. Get Session Info

```http
GET /api/v1/chat/session/{session_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "session_id": "session_123",
  "message_count": 5,
  "extracted_preferences": {
    "destinations": ["Tokyo", "Kyoto"],
    "budget_level": "moderate",
    "traveling_with": "couple"
  },
  "is_ready_for_recommendations": true,
  "current_intent": "itinerary_planning"
}
```

### 4. Execute Action

```http
POST /api/v1/chat/action
Content-Type: application/json
Authorization: Bearer {token}

{
  "session_id": "session_123",
  "action_type": "search_flights",
  "params": {
    "origin_city": "New York",
    "destination_city": "Tokyo",
    "departure_date": "2024-12-15"
  }
}
```

### 5. Get Suggestions

```http
GET /api/v1/chat/suggestions/{session_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "suggestions": [
    "✈️ Search flights",
    "🏨 Find accommodations",
    "🗺️ Create an itinerary",
    "📋 Visa requirements"
  ]
}
```

## Usage Examples

### React Component

```tsx
import ModernChat from '@/components/ModernChat';
import { TravelPreferences } from '@/services/api';

function TravelPlannerPage() {
  const handleChatComplete = (preferences: TravelPreferences) => {
    console.log('User preferences extracted:', preferences);
    // Continue with recommendations...
  };

  return (
    <ModernChat 
      onComplete={handleChatComplete}
      isLoading={false}
    />
  );
}
```

### Programmatic Usage

```typescript
import { api } from '@/services/api';

// Start conversation
const response = await api.chatMessage({
  message: "I want to visit Japan in spring",
  session_id: "my-session-123"
});

console.log(response.extracted_preferences);
// { destinations: ["Japan"], travel_dates: {...}, ... }

// Stream response
const streamResponse = await fetch('/api/v1/chat/message/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "Tell me about cherry blossom season",
    session_id: "my-session-123"
  })
});

const reader = streamResponse.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  // Process SSE data...
}
```

## Preference Extraction

The AI automatically extracts these fields from conversation:

| Field | Type | Description |
|-------|------|-------------|
| `origin` | string | Departure city/country |
| `destinations` | string[] | Mentioned destinations |
| `travel_dates` | {start, end} | Travel period |
| `duration` | number | Trip length in days |
| `budget_level` | enum | budget/moderate/luxury/ultra-luxury |
| `interests` | string[] | Activities they enjoy |
| `traveling_with` | enum | solo/couple/family/friends |
| `kids_ages` | number[] | Children's ages |
| `accommodation_type` | enum | hotel/hostel/airbnb/resort |
| `activity_pace` | enum | relaxed/moderate/active |
| `special_occasion` | string | honeymoon/anniversary/birthday |
| `dietary_restrictions` | string[] | Food restrictions |
| `accessibility_needs` | string[] | Accessibility requirements |
| `visa_preference` | enum | visa_free/easy_visa/any |
| `weather_preference` | enum | warm/cold/mild/tropical |
| `nightlife_priority` | enum | low/medium/high |
| `car_hire` | boolean | Needs rental car |
| `flight_class` | enum | economy/premium/business/first |

## Conversation Flow

```
User: "I want a beach vacation in Thailand"
  ↓
AI extracts: {destinations: ["Thailand"], intent: "recommendation"}
  ↓
AI: "Thailand is perfect! When are you planning to go?"
  ↓
User: "Sometime in December, for about 2 weeks"
  ↓
AI extracts: {travel_dates: {start: "2024-12", duration: 14}}
  ↓
AI: "Great choice! December has ideal weather. What's your budget range?"
  ↓
User: "Around $200 per day, traveling with my partner"
  ↓
AI extracts: {budget_level: "moderate", traveling_with: "couple"}
  ↓
AI checks: is_ready_for_recommendations = true
  ↓
AI shows: "Continue with These Preferences" button
```

## Configuration

### Environment Variables

```bash
# Backend .env

# AI Provider (OpenAI or DeepSeek)
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=your-key-here

# Or use DeepSeek
# LLM_PROVIDER=deepseek
# LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_MODEL=deepseek-chat
# OPENAI_API_KEY=your-deepseek-key

# Optional: Web search for enhanced responses
BRAVE_SEARCH_API_KEY=your-key-here
```

## Migration from Old Chat

### Old API (Deprecated)
```typescript
// Old endpoint
POST /api/v1/chat/travel
{
  "messages": [{role: "user", content: "Hello"}]
}
```

### New API (Recommended)
```typescript
// New endpoint with memory
POST /api/v1/chat/message
{
  "message": "Hello",
  "session_id": "my-session"
}
```

## Best Practices

1. **Session Management**
   - Generate unique session IDs per conversation
   - Store session IDs for conversation continuity
   - Clear sessions when starting fresh

2. **Streaming**
   - Use streaming for better UX
   - Show typing indicator during stream
   - Handle connection errors gracefully

3. **Preference Display**
   - Show extracted preferences in real-time
   - Allow users to correct extracted info
   - Display progress toward completion

4. **Error Handling**
   - Fallback to mock responses if AI unavailable
   - Show friendly error messages
   - Retry failed requests

## Performance

- **Latency**: Standard responses ~1-2s, Streaming starts ~500ms
- **Token Usage**: ~100-300 tokens per exchange
- **Session Memory**: Last 10 messages retained for context
- **Concurrent Sessions**: Supports 1000+ concurrent sessions

## Security

- JWT authentication required for authenticated endpoints
- Session isolation per user
- Input sanitization and validation
- Rate limiting: 100 messages/minute

## Future Enhancements

- [ ] Multi-modal input (image upload for destinations)
- [ ] Voice input/output
- [ ] Multi-language support
- [ ] Integration with booking systems
- [ ] Collaborative trip planning (multi-user sessions)
- [ ] AI-powered negotiation for better deals
