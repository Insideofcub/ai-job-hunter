# Release hardening checklist (v0.6.1)

AI Job Hunter is local-first and single-user in this release. Before publishing or offering a cloud-hosted deployment, complete these checks.

## Local preflight

From the project root:

```powershell
py scripts/preflight.py
```

This checks required Python imports and optionally reports whether the backend `.env`, local Ollama models, and Playwright Chromium are available. It prints configuration states, not secret values. Optional warnings do not prevent starting the app.

## Before pushing to a public repository

```powershell
py scripts/check_release.py --root .
git status --short
git diff --cached --stat
```

Remove any `.env`, database, resume, profile photo, browser profile, token, credential file, or private application export that is staged. The checker catches common filenames and folders but is not a substitute for reviewing staged content or running GitHub secret scanning.

## CI

GitHub Actions runs three independent checks on pushes and pull requests:

- compile Python and run backend tests;
- install frontend dependencies and run the Vite production build;
- audit the repository for common local/private files.

## Runtime smoke test

After starting the backend with `python backend/run_server.py` (or from `backend`, `python run_server.py`), verify:

- `GET /api/health` responds with `status=ok` and the expected version;
- `GET /api/system/readiness` returns a database check and optional provider/configuration states without returning secret values;
- `GET /api/automation/diagnostics` checks browser automation readiness;
- the frontend loads at `http://localhost:5173`;
- search, resume upload, match analysis, application preparation, manual apply tracking, and Excel export are tested manually.

## Before cloud or multi-user deployment

Do not expose this local development API directly to the public internet. A hosted multi-user product needs authentication, per-user database and file isolation, secure session storage, CSRF/origin considerations for browser actions, request rate limits, database migrations, upload malware scanning, observability, and a defined data-retention policy. Those controls are not included just because CI passes.
