@echo off
cd /d "C:\Users\ansh0\Downloads\Travel planner\travel_ai_app\backend"
call .\venv\Scripts\activate
echo Starting Backend Server on http://localhost:8000
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
