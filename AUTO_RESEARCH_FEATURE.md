# 🤖 Auto-Research Agent Feature

## Overview

The **Auto-Research Agent** is an autonomous AI agent that automatically gathers comprehensive travel information as soon as users submit their preferences from a questionnaire. No need to wait or manually trigger research - the agent starts working immediately!

## ✨ What It Does

Once users answer questions about their travel preferences, the agent automatically:

1. **Analyzes Preferences** - Understands user needs (budget, interests, dates, etc.)
2. **Suggests Destinations** - If no specific destinations provided, suggests best matches
3. **Researches Each Destination** (in parallel):
   - 🌤️ **Weather** - Forecasts and seasonal information
   - 🛂 **Visa Requirements** - Entry requirements for user's passport
   - 🎯 **Attractions** - Top places to visit based on interests
   - 🎉 **Events** - Festivals, concerts, cultural events during travel dates
   - 💰 **Affordability** - Cost analysis against budget
   - ✈️ **Flights** - Available flights from origin
   - 🏨 **Hotels** - Accommodation options
   - 🌐 **Web Research** - General info, tips, current events

4. **Scores & Ranks** - Calculates match scores for each destination
5. **Generates Recommendations** - Top 3 personalized suggestions with reasons

## 🚀 API Endpoints

### Start Research (Background)
```http
POST /api/v1/auto-research/start
```

**Request Body:**
```json
{
  "origin": "New York",
  "destinations": [],
  "travel_start": "2024-06-15",
  "travel_end": "2024-06-22",
  "budget_level": "moderate",
  "interests": ["beach", "food", "culture"],
  "traveling_with": "couple",
  "passport_country": "US"
}
```

**Response:**
```json
{
  "job_id": "abc-123-def",
  "status": "pending",
  "progress_percentage": 0,
  "current_step": "initializing",
  "results_available": false
}
```

### Check Status (Poll this)
```http
GET /api/v1/auto-research/status/{job_id}
```

### Get Results
```http
GET /api/v1/auto-research/results/{job_id}
```

### List Jobs
```http
GET /api/v1/auto-research/jobs?user_id=xxx&status=completed
```

### Get Config Options
```http
GET /api/v1/auto-research/config
```

## 📁 Files Created

### Backend
- `app/services/auto_research_agent.py` - Core agent logic
- `app/api/auto_research_routes.py` - API endpoints
- `app/database/models.py` - Added ResearchJob model
- `app/main.py` - Registered new routes

### Frontend
- `src/hooks/useAutoResearch.ts` - React hook for auto-research
- `src/services/api.ts` - Added API methods and types
- `src/components/AutoResearchForm.tsx` - Demo form component
- `src/app/auto-research/page.tsx` - Demo page

## 🔄 How It Works

```
User fills questionnaire
        ↓
POST /auto-research/start
        ↓
Job created (returns immediately)
        ↓
Background research starts
        ↓
Client polls /status/{job_id}
        ↓
Status: in_progress (0-90%)
        ↓
Status: completed
        ↓
GET /results/{job_id}
        ↓
Full research data displayed
```

## 🎯 Usage Example

### React Component
```tsx
import { useAutoResearch } from '@/hooks/useAutoResearch';

function MyComponent() {
  const { startResearch, jobStatus, results, isPolling } = useAutoResearch();

  const handleSubmit = async (preferences) => {
    await startResearch(preferences);
    // Automatically starts polling for status
  };

  return (
    <div>
      {isPolling && <ProgressBar progress={jobStatus?.progress_percentage} />}
      {results && <ResultsDisplay data={results} />}
    </div>
  );
}
```

## 📊 Research Output

The agent returns comprehensive data:

```json
{
  "preferences": { /* user input */ },
  "research_timestamp": "2024-06-01T12:00:00Z",
  "destinations": [
    {
      "name": "Bali, Indonesia",
      "overall_score": 87,
      "data": {
        "weather": { "temperature_c": 28, "condition": "Sunny" },
        "visa": { "visa_required": false },
        "attractions": [...],
        "events": [...],
        "affordability": { "budget_fit": "within_budget" },
        "flights": [...],
        "hotels": [...]
      }
    }
  ],
  "comparison": { /* side-by-side comparison */ },
  "recommendations": [
    {
      "rank": 1,
      "destination": "Bali, Indonesia",
      "score": 87,
      "reasons": [
        "Excellent overall match",
        "No visa required",
        "Great weather (28°C)",
        "Fits your budget"
      ]
    }
  ]
}
```

## 🛠️ Configuration Options

The agent supports:

| Preference | Options |
|------------|---------|
| Budget Level | low, moderate, high, luxury |
| Traveling With | solo, couple, family, group |
| Visa Preference | visa_free, visa_on_arrival, evisa_ok |
| Weather | hot, warm, mild, cold, snow |
| Interests | beach, mountain, city, history, nature, adventure, food, culture, etc. |

## 🔧 Running the Feature

1. **Backend:**
```bash
cd travel_ai_app/backend
uvicorn app.main:app --reload
```

2. **Frontend:**
```bash
cd travel_ai_app/frontend
npm run dev
```

3. **Try it:**
   - Go to http://localhost:3000/auto-research
   - Fill the questionnaire
   - Watch the AI research in real-time!

## 📈 Future Enhancements

- WebSocket support for real-time updates (no polling)
- Email notifications when research completes
- Save research for later comparison
- Export results to PDF/itinerary
- Machine learning for better destination matching
- Integration with booking APIs

---

**Note:** All features work with mock data without API keys. Add real API keys to `backend/.env` for live data!
