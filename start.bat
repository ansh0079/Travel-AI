@echo off
echo ==========================================
echo      TravelAI - Quick Start Script
echo ==========================================
echo.

:: Check if .env file exists
if not exist "backend\.env" (
    echo Creating .env file from example...
    copy "backend\.env.example" "backend\.env"
    echo Please edit backend\.env and add your API keys!
    echo.
)

:: Start backend
echo Starting Backend...
start cmd /k "cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --reload"

:: Wait a bit for backend to start
timeout /t 5

:: Start frontend
echo Starting Frontend...
start cmd /k "cd frontend && npm install && npm run dev"

echo.
echo ==========================================
echo TravelAI is starting up!
echo.
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo ==========================================
echo.
pause