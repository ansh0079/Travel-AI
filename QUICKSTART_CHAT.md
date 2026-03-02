# Quick Start: Enhanced AI Chat

## 1. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## 2. Test the New Chat API

### Option A: Using cURL
```bash
# Send a message
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want a beach vacation in Thailand for 2 weeks in December"
  }'

# Response will include:
{
  "session_id": "...",
  "response": "Thailand is perfect for...",
  "extracted_preferences": {
    "destinations": ["Thailand"],
    "travel_dates": {"start": "2024-12"}
  },
  "is_ready_for_recommendations": false,
  "suggestions": ["📅 When exactly?", "💰 What's your budget?"]
}
```

### Option B: Using the API Client (Frontend)
```typescript
import { api } from '@/services/api';

const response = await api.chatMessage({
  message: "I want to visit Japan in spring",
  session_id: "my-session-123" // optional, will be generated if not provided
});

console.log(response.extracted_preferences);
// { destinations: ["Japan"], travel_dates: {...} }
```

### Option C: Streaming (Best UX)
```typescript
const response = await fetch('http://localhost:8000/api/v1/chat/message/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "Tell me about cherry blossom season in Kyoto",
    session_id: "my-session-123"
  })
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();

while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.token) {
        console.log(data.token); // Stream token by token!
      }
      if (data.done) {
        console.log('Complete!', data.extracted_preferences);
      }
    }
  }
}
```

## 3. Use the React Component

```tsx
'use client';

import ModernChat from '@/components/ModernChat';
import { TravelPreferences } from '@/services/api';

export default function TravelPlannerPage() {
  const handleChatComplete = (preferences: TravelPreferences) => {
    console.log('Ready to plan!', preferences);
    // Navigate to recommendations page
    router.push('/recommendations', { state: { preferences } });
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Plan Your Trip</h1>
      <ModernChat onComplete={handleChatComplete} />
    </div>
  );
}
```

## 4. Check Session State

```bash
# Get session info
curl http://localhost:8000/api/v1/chat/session/my-session-123

# Response:
{
  "session_id": "my-session-123",
  "message_count": 5,
  "extracted_preferences": {
    "destinations": ["Japan"],
    "budget_level": "moderate"
  },
  "is_ready_for_recommendations": true,
  "current_intent": "itinerary_planning"
}
```

## 5. Execute Actions Through Chat

```bash
# Search flights
curl -X POST http://localhost:8000/api/v1/chat/action \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session-123",
    "action_type": "search_flights",
    "params": {
      "origin_city": "New York",
      "destination_city": "Tokyo",
      "departure_date": "2024-12-15"
    }
  }'

# Get weather
curl -X POST http://localhost:8000/api/v1/chat/action \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "my-session-123",
    "action_type": "get_weather",
    "params": {
      "location": "Tokyo",
      "date": "2024-12-15"
    }
  }'
```

## 6. Get Smart Suggestions

```bash
curl http://localhost:8000/api/v1/chat/suggestions/my-session-123

# Response:
{
  "suggestions": [
    "✈️ Search flights",
    "🏨 Find accommodations",
    "🗺️ Create an itinerary",
    "📋 Visa requirements"
  ]
}
```

## 7. Clear Session

```bash
curl -X DELETE http://localhost:8000/api/v1/chat/session/my-session-123
```

## Example Conversation

Here's a complete example of how the chat works:

```
User: "I want a beach vacation in Thailand"
AI: "Thailand is perfect for beach lovers! 🏖️ When are you planning to go?"
[Extracted: {destinations: ["Thailand"], intent: "recommendation"}]

User: "Sometime in December, for about 2 weeks"
AI: "Great choice! December has ideal weather with less humidity. What's your budget range?"
[Extracted: {travel_dates: {start: "2024-12"}, duration: 14}]

User: "Around $200 per day, traveling with my partner"
AI: "Perfect! Thailand offers great value at that budget. You can enjoy nice hotels, delicious food, and exciting activities. Would you like me to search for flights and accommodations?"
[Extracted: {budget_level: "moderate", traveling_with: "couple"}]
[is_ready_for_recommendations: true ✅]
```

## Configuration

Make sure your `.env` file has:

```bash
# Required for AI
OPENAI_API_KEY=sk-...
# Or use DeepSeek
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com/v1
OPENAI_API_KEY=your-deepseek-key

# Optional: Enhanced responses
BRAVE_SEARCH_API_KEY=your-key-here

# TravelGenie agents (for actions)
AMADEUS_API_KEY=your-key
AMADEUS_API_SECRET=your-secret
OPENWEATHER_API_KEY=your-key
```

## Troubleshooting

### "Session not found"
- Session IDs are stored in memory
- Restarting the server clears sessions
- Use consistent session_id in requests

### "AI provider not configured"
- Check OPENAI_API_KEY in .env
- Verify API key is valid
- Check backend logs for details

### Streaming not working
- Ensure CORS allows streaming
- Check browser console for errors
- Verify Server-Sent Events format

## Next Steps

1. ✅ Test basic chat functionality
2. ✅ Try streaming responses
3. ✅ Integrate ModernChat component
4. ✅ Implement preference-based recommendations
5. ⏭️ Add payment/subscription
6. ⏭️ Deploy to production

## API Documentation

Full API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Look for the **"AI Chat"** and **"Travel Chat"** sections.
