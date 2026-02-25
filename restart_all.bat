@echo off
echo ==========================================
echo Travel AI - Complete Server Restart
echo ==========================================
echo.

cd /d "C:\Users\ansh0\Downloads\Travel planner\travel_ai_app"

echo [1/4] Stopping any running Node.js processes...
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul
echo.

echo [2/4] Cleaning frontend cache...
cd frontend
if exist .next rmdir /s /q .next
if exist node_modules\.cache rmdir /s /q node_modules\.cache
cd ..
echo.

echo [3/4] Starting Backend on http://localhost:8000...
start "Travel AI Backend" cmd /k "cd /d C:\Users\ansh0\Downloads\Travel planner\travel_ai_app\backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [4/4] Starting Frontend on http://localhost:3000...
start "Travel AI Frontend" cmd /k "cd /d C:\Users\ansh0\Downloads\Travel planner\travel_ai_app\frontend && npm run dev"

echo.
echo ==========================================
echo Both servers starting...
echo - Backend:  http://localhost:8000
echo - Frontend: http://localhost:3000
echo - API Docs: http://localhost:8000/docs
echo ==========================================
echo.
pause
