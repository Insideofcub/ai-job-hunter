$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Backend = Join-Path $Root 'backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Backend virtual environment is missing. Run .\scripts\setup_windows.ps1 first.' }
Set-Location $Backend
Write-Host 'AI Job Hunter backend — http://127.0.0.1:8000' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C in this window to stop the backend.'
& $Python 'run_server.py'
if ($LASTEXITCODE -ne 0) { Write-Host "Backend stopped with exit code $LASTEXITCODE" -ForegroundColor Red }
