# TravelAI Setup Diagnostic Script (Windows PowerShell)
# Run this to check if everything is set up correctly

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  TravelAI Setup Diagnostic" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
$currentDir = Get-Location
Write-Host "Current directory: $currentDir" -ForegroundColor Yellow

if (-not (Test-Path "backend")) {
    Write-Host "ERROR: 'backend' folder not found!" -ForegroundColor Red
    Write-Host "Please run this script from the travel_ai_app folder." -ForegroundColor Red
    exit 1
}

# Check Python
Write-Host "Checking Python..." -ForegroundColor Green
$pythonVersion = python --version 2>$null
if ($?) {
    Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python not found! Please install Python 3.8+" -ForegroundColor Red
}

# Check Node.js
Write-Host "Checking Node.js..." -ForegroundColor Green
$nodeVersion = node --version 2>$null
if ($?) {
    Write-Host "  ✓ Node.js found: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ Node.js not found! Please install Node.js 18+" -ForegroundColor Red
}

# Check backend .env
Write-Host "Checking backend configuration..." -ForegroundColor Green
if (Test-Path "backend\.env") {
    Write-Host "  ✓ backend\.env exists" -ForegroundColor Green
} else {
    Write-Host "  ✗ backend\.env missing!" -ForegroundColor Red
    Write-Host "    Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item "backend\.env.example" "backend\.env"
}

# Check if pip is available
Write-Host "Checking pip..." -ForegroundColor Green
$pipVersion = pip --version 2>$null
if ($?) {
    Write-Host "  ✓ pip found: $pipVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ pip not found!" -ForegroundColor Red
}

# Check if npm is available
Write-Host "Checking npm..." -ForegroundColor Green
$npmVersion = npm --version 2>$null
if ($?) {
    Write-Host "  ✓ npm found: v$npmVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ npm not found!" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "DIAGNOSTIC COMPLETE" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
Write-Host "Checking if backend is running..." -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 3 -ErrorAction Stop 2>$null
    Write-Host "  ✓ Backend is running on http://localhost:8000" -ForegroundColor Green
    $backendRunning = $true
} catch {
    Write-Host "  ✗ Backend is NOT running" -ForegroundColor Red
    $backendRunning = $false
}

# Check if frontend is running
Write-Host "Checking if frontend is running..." -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 3 -ErrorAction Stop 2>$null
    Write-Host "  ✓ Frontend is running on http://localhost:3000" -ForegroundColor Green
    $frontendRunning = $true
} catch {
    Write-Host "  ✗ Frontend is NOT running" -ForegroundColor Red
    $frontendRunning = $false
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if (-not $backendRunning) {
    Write-Host ""
    Write-Host "1. START BACKEND (run in new terminal):" -ForegroundColor Yellow
    Write-Host "   cd backend" -ForegroundColor White
    Write-Host "   pip install -r requirements.txt" -ForegroundColor White
    Write-Host "   uvicorn app.main:app --reload" -ForegroundColor White
}

if (-not $frontendRunning) {
    Write-Host ""
    Write-Host "2. START FRONTEND (run in new terminal):" -ForegroundColor Yellow
    Write-Host "   cd frontend" -ForegroundColor White
    Write-Host "   npm install" -ForegroundColor White
    Write-Host "   npm run dev" -ForegroundColor White
}

if ($backendRunning -and $frontendRunning) {
    Write-Host ""
    Write-Host "✓ Both servers are running!" -ForegroundColor Green
    Write-Host "  Open http://localhost:3000 in your browser" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to exit"
