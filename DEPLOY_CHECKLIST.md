# 🚀 Deployment Checklist - Let's Ship This!

## Pre-Deployment (5 minutes)

### 1. Environment Variables
Create `backend/.env` if not exists:
```
APP_NAME=TravelAI
DEBUG=false
SECRET_KEY=change-this-to-random-string-32-chars
DATABASE_URL=sqlite:///./travel_ai.db
```

### 2. Frontend API URL
Update `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app/api/v1
NEXT_PUBLIC_WS_URL=wss://your-backend-url.railway.app/api/v1
```

### 3. Test Locally
```bash
# Make sure both servers run
cd backend && python -m uvicorn app.main:app --port 8000
cd frontend && npm run dev

# Check http://localhost:3000 works
```

---

## Option 1: Railway Deployment (Easiest - RECOMMENDED)

### Step 1: Sign Up (2 mins)
1. Go to https://railway.app
2. Sign up with GitHub
3. Verify email

### Step 2: Install Railway CLI (2 mins)
```bash
npm install -g @railway/cli
railway login
```

### Step 3: Deploy Backend (3 mins)
```bash
cd travel_ai_app/backend
railway init
# Select "Empty Project"
# Name it: travelai-backend

# Add PostgreSQL database
railway add --database postgres

# Deploy
railway up

# Get URL
railway domain
# Copy this URL!
```

### Step 4: Deploy Frontend (3 mins)
```bash
cd travel_ai_app/frontend

# Update API URL with backend URL from Step 3
echo "NEXT_PUBLIC_API_URL=https://your-backend-url.up.railway.app/api/v1" > .env.local

railway init
# Name it: travelai-frontend

railway up

# Get URL
railway domain
```

### Step 5: Custom Domain (Optional)
```bash
# Buy domain on Namecheap/Cloudflare (~$10/year)
# In Railway dashboard:
# Settings → Domains → Add Domain
```

---

## Option 2: Render Deployment (Free Tier)

### Backend Service
1. Go to https://render.com
2. Click "New Web Service"
3. Connect GitHub repo
4. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Add PostgreSQL database (free tier)
6. Set environment variables
7. Deploy!

### Frontend Static Site
1. Click "New Static Site"
2. Connect same repo
3. Settings:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `out`
4. Set `NEXT_PUBLIC_API_URL`
5. Deploy!

---

## Post-Deployment (10 minutes)

### 1. Test Everything
- [ ] Homepage loads
- [ ] Research form works
- [ ] Auto-research completes
- [ ] Results page shows
- [ ] City details load
- [ ] WebSocket connects

### 2. Add Analytics
```javascript
// Add to frontend/layout.tsx
import Script from 'next/script'

<Script 
  src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"
  strategy="afterInteractive"
/>
```

### 3. Sign Up for Affiliates
- [ ] Booking.com: https://www.booking.com/affiliate-program.html
- [ ] GetYourGuide: https://www.getyourguide.com/affiliate/
- [ ] Skyscanner: https://www.partners.skyscanner.net/

### 4. Update Links
Add affiliate links to results:
```javascript
// In ResearchDashboard results
<a 
  href={`https://booking.com/search?city=${destination}&aid=YOUR_ID`}
  target="_blank"
  rel="noopener noreferrer"
>
  🔍 Find Hotels on Booking.com
</a>
```

---

## Marketing Checklist

### Share Your App (Do this TODAY!)

**Reddit (High traffic):**
- r/travel (12M members) - "I built an AI travel planner, feedback?"
- r/solotravel (2M members)
- r/backpacking (1M members)
- r/startup (1M members)
- r/SideProject (500K members)

**Twitter/X:**
- Tweet screenshots
- Tag @TravelAI
- Use hashtags: #TravelTech #BuildInPublic

**Product Hunt:**
- Prepare launch for next week
- Need: screenshot, description, maker comment

**Indie Hackers:**
- Post in "Show & Tell"
- Share revenue numbers monthly

---

## Success Metrics

### Week 1 Goals
- [ ] 50 website visitors
- [ ] 10 research completions
- [ ] 3 affiliate clicks
- [ ] Collect 5 user feedback emails

### Month 1 Goals
- [ ] 500 visitors
- [ ] 100 research completions
- [ ] $50 affiliate revenue
- [ ] 10 email subscribers

### Month 3 Goals
- [ ] 5,000 visitors
- [ ] 1,000 research completions
- [ ] $500 affiliate revenue
- [ ] Apply for premium APIs

---

## Emergency Contacts

If deployment fails:
1. Check Railway logs: `railway logs`
2. Test locally first
3. Check environment variables
4. Google the error message
5. Ask in Railway Discord

---

## YOU'VE GOT THIS! 🚀

Deploy in the next 30 minutes. 
Don't overthink it.
Perfect is the enemy of shipped.

**Start with Option 1 (Railway).**
