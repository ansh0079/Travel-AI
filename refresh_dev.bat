@echo off
echo ==========================================
echo Travel AI - Fresh Development Start
echo ==========================================
echo.

cd /d "C:\Users\ansh0\Downloads\Travel planner\travel_ai_app"

echo [1/5] Stopping all Node.js processes...
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul
echo    Done.
echo.

echo [2/5] Cleaning frontend cache...
cd frontend
if exist .next rmdir /s /q .next
if exist node_modules\.cache rmdir /s /q node_modules\.cache
cd ..
echo    Done.
echo.

echo [3/5] Starting Backend...
start "Travel AI Backend" cmd /k "cd /d C:\Users\ansh0\Downloads\Travel planner\travel_ai_app\backend && echo Starting backend... && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 4 /nobreak >nul

echo [4/5] Starting Frontend...
start "Travel AI Frontend" cmd /k "cd /d C:\Users\ansh0\Downloads\Travel planner\travel_ai_app\frontend && echo Starting frontend... && npm run dev"

timeout /t 3 /nobreak >nul

echo [5/5] Opening browser...
start http://localhost:3000
echo    Done.
echo.
echo ==========================================
echo Servers are starting!
echo.
echo IMPORTANT: If styles still don't load:
echo 1. Press Ctrl+Shift+R in browser (hard refresh)
echo 2. OR Press F12, right-click refresh button, select "Empty Cache and Hard Reload"
echo 3. OR try Incognito/Private window
echo.
echo URLs:
echo - Frontend: http://localhost:3000
echo - Backend:  http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo ==========================================
echo.
pause
