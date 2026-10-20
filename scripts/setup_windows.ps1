[CmdletBinding()]
param(
    [switch]$InstallPlaywrightChromium
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$VenvPython = Join-Path $Backend '.venv\Scripts\python.exe'

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked([string]$FilePath, [string[]]$Arguments, [string]$FailureMessage) {
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage (exit code $LASTEXITCODE)."
    }
}

if (-not (Test-Path (Join-Path $Backend 'requirements.txt'))) {
    throw "Cannot find backend/requirements.txt. Run this script from the AI Job Hunter repository."
}
if (-not (Test-Path (Join-Path $Frontend 'package-lock.json'))) {
    throw "Cannot find frontend/package-lock.json. The frontend lockfile is required for a reproducible setup."
}

Write-Host 'AI Job Hunter — Windows setup' -ForegroundColor Magenta
Write-Host "Project: $Root"
Write-Host 'This script preserves existing .env files, databases, resumes, and browser data.'

$Node = Get-Command node -ErrorAction SilentlyContinue
$Npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $Node -or -not $Npm) {
    throw 'Node.js 20+ and npm are required. Install the current Node.js LTS release, reopen PowerShell, and run this script again.'
}
$NodeVersionText = (& $Node.Source --version).Trim().TrimStart('v')
try { $NodeVersion = [version]$NodeVersionText } catch { throw "Could not parse Node.js version: $NodeVersionText" }
if ($NodeVersion -lt [version]'20.0') {
    throw "Node.js 20+ is required; found $NodeVersionText. Install Node.js LTS and retry."
}
Write-Host "[OK] Node.js $NodeVersionText"

if (-not (Test-Path $VenvPython)) {
    Write-Step 'Finding a supported Python version (3.11+)'
    $PythonCommand = $null
    $PythonArguments = @()
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        foreach ($Selector in @('-3.12', '-3.11', '-3')) {
            $VersionText = & $PyLauncher.Source $Selector -c 'import sys; print(sys.version_info.major, sys.version_info.minor, sep=chr(46))' 2>$null
            if ($LASTEXITCODE -eq 0 -and $VersionText) {
                try { $CandidateVersion = [version]($VersionText | Select-Object -First 1) } catch { continue }
                if ($CandidateVersion -ge [version]'3.11') {
                    $PythonCommand = $PyLauncher.Source
                    $PythonArguments = @($Selector)
                    break
                }
            }
        }
    }
    if (-not $PythonCommand) {
        $PythonCommandInfo = Get-Command python -ErrorAction SilentlyContinue
        if ($PythonCommandInfo) {
            $VersionText = & $PythonCommandInfo.Source -c 'import sys; print(sys.version_info.major, sys.version_info.minor, sep=chr(46))' 2>$null
            if ($LASTEXITCODE -eq 0 -and $VersionText) {
                try { $CandidateVersion = [version]($VersionText | Select-Object -First 1) } catch { $CandidateVersion = [version]'0.0' }
                if ($CandidateVersion -ge [version]'3.11') {
                    $PythonCommand = $PythonCommandInfo.Source
                    $PythonArguments = @()
                }
            }
        }
    }
    if (-not $PythonCommand) {
        throw 'Python 3.11+ was not found. Install Python 3.12 from python.org, enable the Python launcher, reopen PowerShell, and retry.'
    }
    Invoke-Checked $PythonCommand ($PythonArguments + @('-m', 'venv', (Join-Path $Backend '.venv'))) 'Creating backend virtual environment failed'
}

if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment Python was not created at $VenvPython"
}
$PythonVersionText = (& $VenvPython -c 'import sys; print(sys.version_info.major, sys.version_info.minor, sys.version_info.micro, sep=chr(46))').Trim()
if ($LASTEXITCODE -ne 0) { throw 'The project virtual-environment Python could not run.' }
$PythonVersion = [version]$PythonVersionText
if ($PythonVersion -lt [version]'3.11') { throw "Python 3.11+ is required in backend/.venv; found $PythonVersionText. Remove/recreate only the virtual environment after confirming it contains no user data." }
Write-Host "[OK] Python $PythonVersionText"

$BackendEnv = Join-Path $Backend '.env'
$BackendEnvExample = Join-Path $Backend '.env.example'
if (-not (Test-Path $BackendEnv)) {
    Copy-Item -LiteralPath $BackendEnvExample -Destination $BackendEnv
    Write-Host '[CREATED] backend/.env from the example. Review it before enabling optional services.'
} else {
    Write-Host '[PRESERVED] Existing backend/.env was not overwritten.'
}
$FrontendEnv = Join-Path $Frontend '.env'
$FrontendEnvExample = Join-Path $Frontend '.env.example'
if (-not (Test-Path $FrontendEnv)) {
    Copy-Item -LiteralPath $FrontendEnvExample -Destination $FrontendEnv
    Write-Host '[CREATED] frontend/.env from the example.'
} else {
    Write-Host '[PRESERVED] Existing frontend/.env was not overwritten.'
}

Write-Step 'Installing backend dependencies'
Invoke-Checked $VenvPython @('-m', 'pip', 'install', '--upgrade', 'pip') 'Upgrading pip failed'
Invoke-Checked $VenvPython @('-m', 'pip', 'install', '-r', (Join-Path $Backend 'requirements.txt')) 'Installing backend dependencies failed'

Write-Step 'Installing frontend dependencies from package-lock.json'
Push-Location $Frontend
try {
    Invoke-Checked $Npm.Source @('ci', '--no-audit', '--no-fund') 'Installing frontend dependencies failed'
    Invoke-Checked $Npm.Source @('run', 'build') 'Frontend production build failed'
} finally {
    Pop-Location
}

if ($InstallPlaywrightChromium) {
    Write-Step 'Installing Playwright Chromium'
    Invoke-Checked $VenvPython @('-m', 'playwright', 'install', 'chromium') 'Installing Playwright Chromium failed'
} else {
    Write-Host "`n[OPTIONAL] Browser form filling needs Playwright Chromium. Install it with:" -ForegroundColor Yellow
    Write-Host '  .\scripts\setup_windows.ps1 -InstallPlaywrightChromium'
}

$Ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($Ollama) {
    Write-Host '[INFO] Ollama command found. The default models are qwen2.5:3b-instruct and nomic-embed-text.'
    Write-Host '       If needed, run: ollama pull qwen2.5:3b-instruct; ollama pull nomic-embed-text'
} else {
    Write-Host '[OPTIONAL] Ollama is not installed or not on PATH. Basic job browsing can still work; local AI drafting/semantic matching needs Ollama.' -ForegroundColor Yellow
}

Write-Host "`nSetup completed." -ForegroundColor Green
Write-Host 'Next: run .\scripts\start_windows.ps1'
Write-Host 'AUTO_SUBMIT_ENABLED remains false in the sample configuration. Review site terms and your profile before using any application workflow.'
