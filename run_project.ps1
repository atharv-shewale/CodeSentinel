<#
.SYNOPSIS
    CodeSentinel Full-Stack Launch Script for Windows PowerShell
.DESCRIPTION
    Starts the required database infrastructure (Postgres, Redis, Qdrant, Neo4j) via Docker,
    and launches the Backend API (FastAPI), Worker daemon, and Frontend UI (Vite + React)
    in independent PowerShell windows for active development and logging.
.PARAMETER Mode
    "Local" (default): Runs databases in Docker, runs Backend & Frontend natively for hot-reloading.
    "Docker": Builds and runs the entire stack inside Docker Compose.
#>

param (
    [ValidateSet("Local", "Docker")]
    [string]$Mode = "Local"
)

$RootPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootPath

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "             Starting CodeSentinel Stack               " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Mode: $Mode" -ForegroundColor Yellow
Write-Host "Root: $RootPath" -ForegroundColor Yellow

if ($Mode -eq "Docker") {
    Write-Host "`n[1/1] Launching entire stack via Docker Compose..." -ForegroundColor Green
    docker compose up --build
    exit $LASTEXITCODE
}

# --- 1. Start Infrastructure Containers ---
Write-Host "`n[1/4] Ensuring Database Services are running (Postgres, Redis, Qdrant, Neo4j)..." -ForegroundColor Green
docker compose up -d postgres redis qdrant neo4j

# Wait for Postgres health check
Write-Host "Waiting for database readiness..." -ForegroundColor DarkGray
Start-Sleep -Seconds 2

function Start-ProcessInNewWindow {
    param (
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$ScriptContent
    )
    $fullScript = @"
`$host.UI.RawUI.WindowTitle = '$Title'
Set-Location '$WorkingDirectory'
$ScriptContent
"@
    $bytes = [System.Text.Encoding]::Unicode.GetBytes($fullScript)
    $encoded = [System.Convert]::ToBase64String($bytes)
    Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encoded
}

$PythonExe = "$RootPath\.venv\Scripts\python.exe"

# --- 2. Launch FastAPI Backend ---
Write-Host "[2/4] Launching FastAPI Backend on http://localhost:8000 ..." -ForegroundColor Green
$BackendScript = @"
Write-Host ">>> Starting CodeSentinel Backend API (FastAPI)..." -ForegroundColor Cyan
& '$PythonExe' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir '$RootPath\backend\app'
"@
Start-ProcessInNewWindow -Title "CodeSentinel - Backend API" -WorkingDirectory "$RootPath\backend" -ScriptContent $BackendScript

# --- 3. Launch Background Worker ---
Write-Host "[3/4] Launching Background Worker daemon..." -ForegroundColor Green
$WorkerScript = @"
Write-Host ">>> Starting CodeSentinel Background Worker..." -ForegroundColor Cyan
& '$PythonExe' -m app.workers.worker
"@
Start-ProcessInNewWindow -Title "CodeSentinel - Worker" -WorkingDirectory "$RootPath\backend" -ScriptContent $WorkerScript

# --- 4. Launch React Frontend ---
Write-Host "[4/4] Launching Vite Frontend on http://localhost:5173 ..." -ForegroundColor Green
$FrontendScript = @"
Write-Host ">>> Starting CodeSentinel Frontend UI (Vite)..." -ForegroundColor Cyan
npm.cmd run dev
"@
Start-ProcessInNewWindow -Title "CodeSentinel - Frontend UI" -WorkingDirectory "$RootPath\frontend" -ScriptContent $FrontendScript

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "       CodeSentinel System Successfully Launched!       " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Dashboard UI : http://localhost:5173" -ForegroundColor White
Write-Host " Backend API  : http://localhost:8000" -ForegroundColor White
Write-Host " API Docs     : http://localhost:8000/docs" -ForegroundColor White
Write-Host " Neo4j Browser: http://localhost:7474" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
