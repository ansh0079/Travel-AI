#!/bin/bash

echo "=========================================="
echo "      TravelAI - Quick Start Script"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file from example..."
    cp "backend/.env.example" "backend/.env"
    echo "Please edit backend/.env and add your API keys!"
    echo ""
fi

# Start backend
echo "Starting Backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload &
BACKEND_PID=$!
cd ..

# Wait for backend
echo "Waiting for backend to start..."
sleep 5

# Start frontend
echo "Starting Frontend..."
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "TravelAI is running!"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait