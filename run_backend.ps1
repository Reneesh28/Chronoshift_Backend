# PowerShell Launcher for ChronoShift Backend Monolith Services
# Activates venv automatically and boots all parallel services.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "     LAUNCHING CHRONOSHIFT MODULAR MONOLITH BACKEND SERVICES HUD" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# Check if Python venv exists
$VenvPython = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    Write-Host "[INIT] Activating python environment: venv" -ForegroundColor Green
    & $VenvPython run_backend.py
} else {
    Write-Host "[INIT] Virtual environment not found, running with system python..." -ForegroundColor Yellow
    python run_backend.py
}
