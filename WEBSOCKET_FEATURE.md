# 🔌 WebSocket Real-Time Updates Feature

## Overview

WebSocket support has been added to provide **instant, real-time updates** during the auto-research process. No more polling - users see progress immediately as the AI researches destinations!

## ✨ Key Features

- **Real-time progress updates** - See each research step as it happens
- **Auto-reconnect** - Connection automatically restores if interrupted
- **Connection health monitoring** - Ping/pong to keep connection alive
- **Activity log** - See exactly what the AI is doing at each step
- **Connection status indicator** - Know when you're connected

## 📊 Before vs After

### Before (Polling)
```
Client                    Server
  |                         |
  |---- GET /status/123 --->|  ← Every 2 seconds
  |<--- Status: 45% --------|  
  |                         |
  |---- GET /status/123 --->|  ← Every 2 seconds
  |<--- Status: 47% --------|
  |                         |
  [2 second delay between updates]
```

### After (WebSockets)
```
Client                    Server
  |                         |
  |---- WS Connect -------->|  ← One connection
  |<--- Connected ----------|
  |                         |
  |<--- Progress: 45% ------|  ← Instant push
  |<--- Progress: 46% ------|  ← Instant push
  |<--- Progress: 47% ------|  ← Instant push
  |                         |
  [Real-time updates!]
```

## 🛠️ Implementation

### Backend

**Files Created:**
- `app/api/websocket_routes.py` - WebSocket endpoints and connection manager

**WebSocket Endpoints:**
```
ws://localhost:8000/api/v1/ws/research/{job_id}  # Job-specific updates
ws://localhost:8000/api/v1/ws/user/{user_id}     # User-wide updates
ws://localhost:8000/api/v1/ws/global             # Global broadcasts
```

**Message Types:**
```json
// Connection established
{"type": "connected", "job_id": "abc-123"}

// Research started
{"type": "started", "job_id": "abc-123", "preferences": {...}}

// Progress update
{
  "type": "progress",
  "job_id": "abc-123",
  "step": "researching_weather",
  "percentage": 45,
  "message": "Checking weather for Bali..."
}

// Research completed
{
  "type": "completed",
  "job_id": "abc-123",
  "results_summary": {
    "destinations_count": 5,
    "top_destination": "Bali, Indonesia",
    "top_score": 87
  }
}

// Error occurred
{"type": "error", "job_id": "abc-123", "error": "Something went wrong"}

// Ping/pong (keepalive)
{"type": "pong", "timestamp": 1234567890}
```

### Frontend

**Files Created:**
- `src/hooks/useWebSocketResearch.ts` - WebSocket research hook

**Updated:**
- `src/components/AutoResearchForm.tsx` - Now uses WebSockets

**Hook Usage:**
```tsx
import { useWebSocketResearch } from '@/hooks/useWebSocketResearch';

function MyComponent() {
  const {
    jobId,
    jobStatus,
    results,
    isConnected,
    isResearching,
    lastMessage,
    messages,
    error,
    connectionError,
    startResearch,
    clearResults,
    reconnect
  } = useWebSocketResearch();

  // Start research - automatically connects WebSocket
  const handleSubmit = async (preferences) => {
    await startResearch(preferences);
  };

  return (
    <div>
      {isConnected && <span>Live updates active</span>}
      {connectionError && <button onClick={reconnect}>Reconnect</button>}
      
      {/* Progress updates in real-time */}
      <ProgressBar progress={jobStatus?.progress_percentage} />
      
      {/* Activity log shows each step */}
      <ActivityLog messages={messages} />
    </div>
  );
}
```

## 🔄 Connection Flow

1. **User submits form** → HTTP POST to start research
2. **Job created** → Returns job_id immediately
3. **WebSocket connects** → `ws://.../ws/research/{job_id}`
4. **Real-time updates** → Server pushes progress as it happens
5. **Research completes** → Server sends "completed" message
6. **Auto-fetch results** → Client fetches full results via HTTP
7. **Connection closes** → Clean disconnection

## 🛡️ Reliability Features

### Auto-Reconnect
If the connection drops during research:
```javascript
// WebSocket closes unexpectedly
ws.onclose = (event) => {
  if (isResearching && event.code !== 1000) {
    // Wait 3 seconds and reconnect
    setTimeout(() => connectWebSocket(jobId), 3000);
  }
};
```

### Ping/Pong Keepalive
Prevents connection timeout:
```javascript
// Send ping every 30 seconds
setInterval(() => {
  ws.send(JSON.stringify({ action: 'ping', timestamp: Date.now() }));
}, 30000);
```

### Connection Status UI
```tsx
<div className="flex items-center gap-2">
  <div className={`w-2 h-2 rounded-full ${
    isConnected ? 'bg-green-500' : 'bg-red-500'
  }`} />
  <span>{isConnected ? 'Live updates' : 'Disconnected'}</span>
  {connectionError && <button onClick={reconnect}>Retry</button>}
</div>
```

## 📱 User Experience

### Activity Log
Users can see exactly what the AI is doing:
```
Activity Log:
▶ started
⟳ researching_weather (20%)
⟳ researching_visa (30%)
⟳ researching_attractions (40%)
⟳ researching_flights (50%)
⟳ compiling_results (90%)
✓ completed (100%)
```

### Visual Indicators
- 🟢 **Green dot** = Connected, receiving live updates
- 🔴 **Red dot** = Disconnected, will auto-reconnect
- ⚡ **Lightning bolt** = Real-time mode active

## 🧪 Testing

### Test WebSocket Connection
```bash
# Using wscat (npm install -g wscat)
wscat -c ws://localhost:8000/api/v1/ws/research/test-job-123

# Send ping
> {"action": "ping", "timestamp": 1234567890}

# Receive pong
< {"type": "pong", "timestamp": 1234567890}
```

### Test Full Flow
1. Open http://localhost:3000/auto-research
2. Fill the questionnaire
3. Submit and watch real-time updates
4. Disconnect Wi-Fi briefly → watch auto-reconnect
5. Results appear instantly when complete

## 🔧 Configuration

### Environment Variables
```bash
# Frontend .env.local
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1

# For production with WSS
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com/api/v1
```

### Connection Options
```typescript
// Reconnect delay (default: 3000ms)
const RECONNECT_DELAY = 3000;

// Ping interval (default: 30000ms)
const PING_INTERVAL = 30000;

// Max reconnect attempts (default: unlimited during research)
const MAX_RECONNECT_ATTEMPTS = Infinity;
```

## 📈 Future Enhancements

- [ ] **Multi-job tracking** - Monitor multiple research jobs simultaneously
- [ ] **Server-Sent Events (SSE) fallback** - For environments that block WebSockets
- [ ] **Compression** - Enable per-message deflate for large payloads
- [ ] **Authentication** - JWT token validation on WebSocket connection
- [ ] **Rate limiting** - Prevent connection spam
- [ ] **Analytics** - Track connection health and user engagement

## 🐛 Troubleshooting

### Connection Refused
```
Error: WebSocket connection failed
```
**Fix:** Ensure backend is running on correct port

### CORS Error
```
Access to WebSocket at 'ws://...' from origin 'http://...' has been blocked
```
**Fix:** Update CORS settings in `app/main.py`

### Connection Drops Frequently
**Check:** 
- Proxy/firewall timeout settings
- Keepalive ping interval
- Network stability

## 📁 Files Changed

### Backend
- `app/api/websocket_routes.py` (NEW)
- `app/services/auto_research_agent.py` (Updated - emits WebSocket events)
- `app/main.py` (Updated - registered WebSocket routes)

### Frontend
- `src/hooks/useWebSocketResearch.ts` (NEW)
- `src/components/AutoResearchForm.tsx` (Updated - uses WebSockets)

## 🎉 Result

Users now get **instant feedback** during research with:
- Real-time progress updates
- Live activity log
- Connection status indicator
- Auto-reconnect on failure
- Smoother, more responsive experience

No more polling! 🚀
