# AI Job Hunter — Windows quick start

This guide is for Windows 10/11 using PowerShell. AI Job Hunter is a local-first, single-user application. The launcher binds the frontend and backend to `127.0.0.1`; do not expose the development servers directly to the public internet.

## Prerequisites

- Python 3.11 or newer (Python 3.12 recommended)
- Node.js 20 or newer, including npm
- Git (to clone the repository)
- Optional: Ollama for local AI drafting and semantic matching
- Optional: Playwright Chromium for supported visible browser form filling

## One-time setup

Open PowerShell in the repository root and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```

The script creates `backend/.venv` if needed, installs backend dependencies, creates `backend/.env` and `frontend/.env` only when they do not already exist, installs frontend dependencies from `package-lock.json`, and runs a production build. It never overwrites existing environment files.

If you need supported visible browser form filling, install Chromium explicitly:

```powershell
.\scripts\setup_windows.ps1 -InstallPlaywrightChromium
```

AI features use Ollama if it is configured in `backend/.env`. The setup script does not install Ollama or download large models automatically. If you want the default local models, install Ollama separately, then run:

```powershell
ollama pull qwen2.5:3b-instruct
ollama pull nomic-embed-text
```

Check `backend/.env` and `frontend/.env` locally if you need optional integrations. Keep API keys private and never commit `.env` files. The sample keeps `AUTO_SUBMIT_ENABLED=false` and `JOBSPY_ENABLED=false`; do not enable job-source integrations without reviewing the applicable provider/site terms.

## Start the app

From the repository root:

```powershell
.\scripts\start_windows.ps1
```

The launcher opens separate PowerShell windows for the backend and frontend, waits for the API health endpoint and frontend page to respond, then opens `http://127.0.0.1:5173` in your browser. You can skip opening the browser automatically with:

```powershell
.\scripts\start_windows.ps1 -NoBrowser
```

Useful URLs:

- Frontend: <http://127.0.0.1:5173>
- API health: <http://127.0.0.1:8000/api/health>
- Interactive API docs: <http://127.0.0.1:8000/docs>

## Stop the app

Press `Ctrl+C` in each backend/frontend server window. Close those windows afterward if desired. Existing databases, resumes, browser profiles, and environment files are stored locally and are not removed by setup or startup scripts.

## Troubleshooting

- **Port 8000 or 5173 is occupied:** Check whether an existing AI Job Hunter process is running. Do not blindly kill unrelated processes.
- **Setup reports missing Node/Python:** Install the supported version, close and reopen PowerShell, and rerun setup.
- **API readiness says Ollama isn't configured or reachable:** Start Ollama and check the model names in `backend/.env`.
- **Browser automation isn't available:** Run setup with `-InstallPlaywrightChromium`.
- **PowerShell blocks scripts:** The `Set-ExecutionPolicy -Scope Process ...` command changes policy only for the current PowerShell process; it does not change the machine-wide policy.

For manual installation and feature documentation, see the main [README](../README.md) and the troubleshooting docs in `docs/`.
