[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BackendRunner = Join-Path $PSScriptRoot 'run_backend_windows.ps1'
$FrontendRunner = Join-Path $PSScriptRoot 'run_frontend_windows.ps1'
$Python = Join-Path $Root 'backend\.venv\Scripts\python.exe'
$FrontendNodeModules = Join-Path $Root 'frontend\node_modules'

if (-not (Test-Path $Python)) { throw 'Backend environment is missing. Run .\scripts\setup_windows.ps1 first.' }
if (-not (Test-Path $FrontendNodeModules)) { throw 'Frontend dependencies are missing. Run .\scripts\setup_windows.ps1 first.' }

function Test-HttpEndpoint([string]$Uri) {
    try {
        $null = Invoke-WebRequest -Uri $Uri -TimeoutSec 2 -UseBasicParsing
        return $true
    } catch {
        return $false
    }
}

function Test-TcpPort([int]$Port) {
    $Client = New-Object System.Net.Sockets.TcpClient
    try {
        $Async = $Client.BeginConnect('127.0.0.1', $Port, $null, $null)
        $Connected = $Async.AsyncWaitHandle.WaitOne(350)
        return ($Connected -and $Client.Connected)
    } catch {
        return $false
    } finally {
        $Client.Close()
    }
}

Write-Host 'AI Job Hunter — Windows launcher' -ForegroundColor Magenta
Write-Host 'Both development servers bind to loopback (127.0.0.1), not the public network.'

if (-not (Test-HttpEndpoint 'http://127.0.0.1:8000/api/health')) {
    if (Test-TcpPort 8000) { throw 'Port 8000 is occupied by a service that did not return the AI Job Hunter health response. Close that service or investigate it, then retry.' }
    $QuotedBackendRunner = '"' + $BackendRunner + '"'
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $QuotedBackendRunner) -WorkingDirectory $Root | Out-Null
    Write-Host '[STARTING] Backend in a new PowerShell window.'
} else {
    Write-Host '[ALREADY RUNNING] Backend health endpoint responded.'
}

if (-not (Test-HttpEndpoint 'http://127.0.0.1:5173')) {
    if (Test-TcpPort 5173) { throw 'Port 5173 is occupied by a service that did not return the frontend page. Close that service or investigate it, then retry.' }
    $QuotedFrontendRunner = '"' + $FrontendRunner + '"'
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $QuotedFrontendRunner) -WorkingDirectory $Root | Out-Null
    Write-Host '[STARTING] Frontend in a new PowerShell window.'
} else {
    Write-Host '[ALREADY RUNNING] Frontend responded.'
}

Write-Host 'Waiting for services to become ready...'
$Deadline = (Get-Date).AddSeconds(75)
$BackendReady = Test-HttpEndpoint 'http://127.0.0.1:8000/api/health'
$FrontendReady = Test-HttpEndpoint 'http://127.0.0.1:5173'
while ((Get-Date) -lt $Deadline -and (-not $BackendReady -or -not $FrontendReady)) {
    Start-Sleep -Seconds 2
    $BackendReady = Test-HttpEndpoint 'http://127.0.0.1:8000/api/health'
    $FrontendReady = Test-HttpEndpoint 'http://127.0.0.1:5173'
}

if (-not $BackendReady -or -not $FrontendReady) {
    Write-Host 'One or both services did not become ready within 75 seconds.' -ForegroundColor Yellow
    Write-Host 'Inspect the two server windows for startup errors, then rerun this launcher.'
    Write-Host 'Backend health: http://127.0.0.1:8000/api/health'
    Write-Host 'Frontend:       http://127.0.0.1:5173'
    exit 1
}

Write-Host '[READY] Backend health and frontend page responded.' -ForegroundColor Green
Write-Host 'Backend: http://127.0.0.1:8000'
Write-Host 'API docs: http://127.0.0.1:8000/docs'
Write-Host 'Frontend: http://127.0.0.1:5173'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173' }
Write-Host 'To stop the app, press Ctrl+C in each backend/frontend server window.'
