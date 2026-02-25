@echo off
cd /d "C:\Users\ansh0\Downloads\Travel planner\travel_ai_app\frontend"
echo Cleaning Next.js cache...
if exist .next rmdir /s /q .next
if exist node_modules\.cache rmdir /s /q node_modules\.cache
echo.
echo Starting frontend dev server on http://localhost:3000
echo.
npm run dev
