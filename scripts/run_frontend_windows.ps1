$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Frontend = Join-Path $Root 'frontend'
$Npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $Npm) { throw 'npm was not found. Install Node.js 20+ and run setup again.' }
if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) { throw 'Frontend dependencies are missing. Run .\scripts\setup_windows.ps1 first.' }
Set-Location $Frontend
Write-Host 'AI Job Hunter frontend — http://127.0.0.1:5173' -ForegroundColor Cyan
Write-Host 'Press Ctrl+C in this window to stop the frontend.'
& $Npm.Source 'run' 'dev' '--' '--host' '127.0.0.1' '--strictPort'
if ($LASTEXITCODE -ne 0) { Write-Host "Frontend stopped with exit code $LASTEXITCODE" -ForegroundColor Red }
