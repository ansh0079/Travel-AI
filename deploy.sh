#!/bin/bash

# TravelAI Deployment Script
# Usage: ./deploy.sh [docker|railway|render|vercel]

set -e

DEPLOY_TARGET=${1:-docker}

echo "🚀 TravelAI Deployment"
echo "======================"
echo "Target: $DEPLOY_TARGET"
echo ""

case $DEPLOY_TARGET in
  docker)
    echo "📦 Deploying with Docker Compose..."
    
    # Check Docker is running
    if ! docker info > /dev/null 2>&1; then
      echo "❌ Docker is not running. Please start Docker first."
      exit 1
    fi
    
    # Build and start
    echo "Building images..."
    docker-compose build
    
    echo "Starting services..."
    docker-compose up -d
    
    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "🌐 Access your app:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend:  http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "📊 View logs: docker-compose logs -f"
    echo "🛑 Stop: docker-compose down"
    ;;
    
  railway)
    echo "🚂 Deploying to Railway..."
    
    # Check railway CLI
    if ! command -v railway &> /dev/null; then
      echo "Installing Railway CLI..."
      npm install -g @railway/cli
    fi
    
    # Login
    railway login
    
    # Link project
    railway link
    
    # Deploy
    railway up
    
    echo ""
    echo "✅ Deployed to Railway!"
    echo "🌐 View your app: railway open"
    ;;
    
  render)
    echo "📋 Render Deployment Instructions:"
    echo ""
    echo "1. Go to https://dashboard.render.com"
    echo "2. Create a new Web Service for the backend"
    echo "   - Root Directory: backend"
    echo "   - Build Command: pip install -r requirements.txt"
    echo "   - Start Command: uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo "3. Create a PostgreSQL database"
    echo ""
    echo "4. Set environment variables in Render dashboard"
    echo ""
    echo "5. Create a Static Site for the frontend"
    echo "   - Root Directory: frontend"
    echo "   - Build Command: npm install && npm run build"
    echo ""
    ;;
    
  vercel)
    echo "▲ Deploying Frontend to Vercel..."
    
    # Check Vercel CLI
    if ! command -v vercel &> /dev/null; then
      echo "Installing Vercel CLI..."
      npm install -g vercel
    fi
    
    cd frontend
    vercel --prod
    cd ..
    
    echo ""
    echo "✅ Frontend deployed to Vercel!"
    ;;
    
  *)
    echo "Usage: ./deploy.sh [docker|railway|render|vercel]"
    echo ""
    echo "Options:"
    echo "  docker  - Deploy locally with Docker Compose (default)"
    echo "  railway - Deploy to Railway.app"
    echo "  render  - Show Render deployment instructions"
    echo "  vercel  - Deploy frontend to Vercel"
    exit 1
    ;;
esac
