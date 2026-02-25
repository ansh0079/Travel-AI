# Start Backend
$backendJob = Start-Job -ScriptBlock {
    Set-Location "C:\Users\ansh0\Downloads\Travel planner\travel_ai_app\backend"
    .\venv\Scripts\activate
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}

# Start Frontend  
$frontendJob = Start-Job -ScriptBlock {
    Set-Location "C:\Users\ansh0\Downloads\Travel planner\travel_ai_app\frontend"
    npm run dev
}

Write-Host "Starting servers..."
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers"

# Keep script running
try {
    while ($true) {
        Start-Sleep 1
        
        # Show output from backend
        $backendOutput = Receive-Job $backendJob
        if ($backendOutput) { Write-Host "[Backend] $backendOutput" }
        
        # Show output from frontend
        $frontendOutput = Receive-Job $frontendJob
        if ($frontendOutput) { Write-Host "[Frontend] $frontendOutput" }
    }
} finally {
    Stop-Job $backendJob
    Stop-Job $frontendJob
    Remove-Job $backendJob
    Remove-Job $frontendJob
    Write-Host "Servers stopped"
}
