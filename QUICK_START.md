# Quick Start Guide - TravelAI

## Step 1: Install Prerequisites

Make sure you have installed:
- **Python 3.8+**: https://python.org/downloads
- **Node.js 18+**: https://nodejs.org/downloads

## Step 2: Open 2 Terminals

You need to run the backend and frontend in **separate terminals**.

### Terminal 1 - Backend

```powershell
# Navigate to backend folder
cd "c:\Users\ansh0\Downloads\Travel planner\travel_ai_app\backend"

# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn app.main:app --reload
```

You should see something like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Test it**: Open http://localhost:8000 in your browser. You should see a JSON response.

---

### Terminal 2 - Frontend

```powershell
# Navigate to frontend folder
cd "c:\Users\ansh0\Downloads\Travel planner\travel_ai_app\frontend"

# Install Node.js dependencies
npm install

# Start the frontend
npm run dev
```

You should see something like:
```
ready started server on 0.0.0.0:3000, url: http://localhost:3000
```

**Open it**: Go to http://localhost:3000 in your browser.

---

## Common Issues

### Issue: "pip is not recognized"
**Fix**: Make sure Python is installed and added to PATH. Try `python -m pip install -r requirements.txt`

### Issue: "npm is not recognized"
**Fix**: Make sure Node.js is installed. Restart your terminal after installation.

### Issue: "Module not found" errors
**Fix**: Make sure you installed dependencies in BOTH folders:
- Run `pip install -r requirements.txt` in backend folder
- Run `npm install` in frontend folder

### Issue: Port already in use
**Fix**: 
- For backend: `uvicorn app.main:app --reload --port 8001`
- For frontend: `npm run dev -- --port 3001`

### Issue: Backend starts but frontend shows errors
**Fix**: Check that backend is actually running:
- Open http://localhost:8000/docs - you should see the API docs
- If not, check the terminal for error messages

---

## What Success Looks Like

Once both are running:

1. **Backend** (http://localhost:8000):
   ```json
   {
     "name": "TravelAI API",
     "version": "1.0.0",
     "docs": "/docs"
   }
   ```

2. **Frontend** (http://localhost:3000):
   - You should see a beautiful landing page with a search form

---

## Need Help?

If it still doesn't work, tell me:
1. What error message you see
2. Which step failed
3. What you see in the terminal
