@echo off
REM TravelAI Deployment Script for Windows
REM Usage: deploy.bat [docker|railway|render|vercel]

set DEPLOY_TARGET=%1
if "%DEPLOY_TARGET%"=="" set DEPLOY_TARGET=docker

echo.
echo 🚀 TravelAI Deployment
echo ======================
echo Target: %DEPLOY_TARGET%
echo.

if "%DEPLOY_TARGET%"=="docker" goto docker
if "%DEPLOY_TARGET%"=="railway" goto railway
if "%DEPLOY_TARGET%"=="render" goto render
if "%DEPLOY_TARGET%"=="vercel" goto vercel
goto usage

:docker
echo 📦 Deploying with Docker Compose...
echo.

REM Check Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker first.
    exit /b 1
)

echo Building images...
docker-compose build

echo.
echo Starting services...
docker-compose up -d

echo.
echo ✅ Deployment complete!
echo.
echo 🌐 Access your app:
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo 📊 View logs: docker-compose logs -f
echo 🛑 Stop: docker-compose down
goto end

:railway
echo 🚂 Deploying to Railway...
echo.

REM Check railway CLI
where railway >nul 2>&1
if errorlevel 1 (
    echo Installing Railway CLI...
    npm install -g @railway/cli
)

echo Login to Railway...
railway login

echo Linking project...
railway link

echo Deploying...
railway up

echo.
echo ✅ Deployed to Railway!
echo 🌐 View your app: railway open
goto end

:render
echo 📋 Render Deployment Instructions:
echo.
echo 1. Go to https://dashboard.render.com
echo 2. Create a new Web Service for the backend
echo    - Root Directory: backend
echo    - Build Command: pip install -r requirements.txt
echo    - Start Command: uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
echo 3. Create a PostgreSQL database
echo.
echo 4. Set environment variables in Render dashboard
echo.
echo 5. Create a Static Site for the frontend
echo    - Root Directory: frontend
echo    - Build Command: npm install ^&^& npm run build
goto end

:vercel
echo ▲ Deploying Frontend to Vercel...
echo.

REM Check Vercel CLI
where vercel >nul 2>&1
if errorlevel 1 (
    echo Installing Vercel CLI...
    npm install -g vercel
)

cd frontend
vercel --prod
cd ..

echo.
echo ✅ Frontend deployed to Vercel!
goto end

:usage
echo Usage: deploy.bat [docker^|railway^|render^|vercel]
echo.
echo Options:
echo   docker  - Deploy locally with Docker Compose (default)
echo   railway - Deploy to Railway.app
echo   render  - Show Render deployment instructions
echo   vercel  - Deploy frontend to Vercel
goto end

:end
echo.
pause
