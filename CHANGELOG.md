# Changelog

## v0.6.3 — release-candidate validation and packaging

- Adds a pre-release validator for required files, version consistency, Markdown links, and local/private data.
- Adds a clean source ZIP packager that excludes secrets, data, browser profiles, personal documents, node modules, build output, and Python caches.
- Adds public release/security guidance and an explicit human review gate for redistribution rights of the bundled theme artwork.
- Expands CI release checks.


## v0.6.1 — Release hardening and diagnostics

- Aligns FastAPI/OpenAPI, frontend package, and release metadata to v0.6.1.
- Adds `/api/version` and `/api/system/readiness` for safe runtime checks. Readiness reports database connectivity and optional integrations without printing API keys.
- Adds `scripts/preflight.py` to verify local Python dependencies and report optional Ollama/embedding/Playwright browser readiness.
- Adds `scripts/check_release.py` to flag common secrets, local databases, candidate documents, browser profiles, and application data before a public push.
- Adds GitHub Actions CI for Python compilation/backend tests, frontend production build, and release hygiene audit.
- Keeps local data and `.env` files excluded from the release bundle. This is release hygiene, not a replacement for authentication or cloud security hardening.

## v0.6.0 — Neon Streaks theme
- Added the supplied neon purple/blue light-streak artwork as a local frontend asset.
- Applied a high-contrast dark navy theme with neon violet, magenta, blue, and teal accents.
- Re-themed navigation, panels, job cards, search filters, profile, settings, application history, diagnostics, tables, and modals.
- Preserved the existing search/application flows and responsive layout.
- No backend behavior or database schema changes.

## v0.5.9 — modest font-size uplift
- Increased small UI typography by roughly 1px across navigation, form labels/inputs, filters, job metadata, application statuses, source diagnostics, and help text.
- Preserved the existing layout, colors, and job-title hierarchy; added mobile overrides for responsive readability.

# Changelog

## v0.5.7 — Browser application workflow diagnostics

- Added `/api/automation/diagnostics` to identify whether Playwright, its driver, Chromium, and the browser profile directory are ready in the active backend Python environment.
- Browser launch failures now include actionable details (active Python path, missing Chromium install, profile-directory lock/permission hints) instead of a vague HTTP 503.
- Frontend reads and displays server error details robustly when the browser workflow fails.
- Added a **Check browser setup** button under Settings so users can run a no-window preflight check.
- Added regression tests for diagnostics output and HTTP 503 detail propagation.

## v0.5.6 — Visible application queue action

- Added a sticky **Prepare selected (N)** action bar that appears after one or more jobs are selected, and stays visible while scrolling the results list.
- Added a visible Clear selection action and a clear note that batch preparation does not submit applications.
- Added responsive layout for desktop and mobile.


## 0.5.5 — Readability improvements

- Increased typography and spacing for saved-job and match rows.
- Job titles use a larger font and wrap to multiple lines rather than being truncated on one line.
- Company/location, work-model, posting-time, verification, and match-score text are larger.
- Larger company marks and external-link controls, with mobile-responsive type sizes.

## 0.5.4 — Application review queue and safe manual apply tracking

- Added `POST /api/applications/queue` to create or reuse up to 50 selected vacancy records in one request.
- Selected fresh and timestamp-unverified leads can enter Application History; previously unverified leads are saved with `verified_posting_time=false` rather than being mislabeled fresh.
- Added multi-select controls and a batch prepare action on Find & Apply.
- Queue preparation preserves existing application statuses and screening answers for already tracked vacancies, deduplicates canonical URLs, and explicitly reports that no submissions occurred.
- Added a dedicated Apply manually action in Application History; opening a listing moves it to `needs_manual_action` only when it is not already in a later/terminal state, and never records it as submitted.
- Added deterministic API coverage for batch creation, idempotent reuse, unverified leads, and zero submissions.
- All 76 backend tests pass. Frontend JSX transpile syntax check passes; Vite production build still requires local dependency installation.


## 0.5.1 — Search relevance, source expansion, and exclusion explanations

- Expanded role-family matching for recruiter, talent acquisition, talent sourcing, staffing, HR, people operations, executive search, and resourcing title variants.
- Added the public Himalayas remote-jobs adapter with the source-provided application link and required source attribution.
- Expanded India/global web-search queries (up to 20 per run) and original-page timestamp checks (up to 48 per run) when Brave Search is configured.
- Deduplicated before applying relevance, location, work-arrangement, employment-type, and posting-window filters.
- Returned a structured funnel and reason-coded exclusion samples; total reason counts cover all exclusions while detailed examples are capped at 500.
- Separated successful empty source responses from connector errors.
- Added deterministic no-network fixture for integration tests; 66 backend tests pass.


## 0.5.0 — Simple search-to-apply workflow
- Make Find & Apply the default landing view.
- Add a concise search form with collapsible location/work/employment filters.
- Add inline CV upload/replace; re-run discovery after replacement when a result set already exists.
- Display per-job profile-fit cards and quick actions for manual or supported automatic application.
- Track manual application opens in Application History.
- Keep auto-submission off by default and explicitly explain draft-only mode.
- Move connector management, source diagnostics, full research report, and saved jobs into expandable sections.


## 0.4.8 — Resume-grounded job analysis and application preparation

- Added `POST /api/jobs/{job_id}/analysis` for saved-job analysis using the candidate's stored professional profile and extracted resume text.
- Added transparent match evidence, required skills found/not found in profile text, experience/location assessments, resume emphasis suggestions, screening-question suggestions, and concerns.
- Uses configured Ollama/OpenAI-compatible AI when it returns valid JSON; otherwise returns a rule-based fallback without blocking the workflow.
- Added **Analyze against my resume** and **Prepare application** actions to the detailed job report.
- Preparing an application creates or reuses a local history record and drafts role-specific screening questions; it does not submit.
- Added API tests for deterministic fallback, mocked AI output, and unknown job IDs.

## 0.4.9 — Optional local semantic matching

- Added local Ollama embedding support through `/api/embed` with configurable `OLLAMA_EMBEDDING_MODEL` and a safe fallback if the model is missing or Ollama is offline.
- Added hybrid ranking: 70% transparent rule-based evidence + 30% calibrated semantic similarity. The score is a ranking estimate, not an employment outcome probability.
- Added per-result scoring method, component breakdowns, and fallback notes to API payloads and the UI.
- Kept the synchronous baseline helper for existing application-creation flows while the API route and agent use async semantic reranking.
- Added tests for vector math, score blending, and fallback behavior.


## v0.5.2 — Optional JobSpy connector

- Added optional `python-jobspy` integration behind the existing job-source interface.
- Seeded a paused JobSpy source by default; requires optional dependency installation plus `JOBSPY_ENABLED=true`.
- Added bounded role/location search planning, regional site selection, structured source diagnostics, and salary/skills/experience normalization.
- Keeps day-only posting dates unverified; does not configure proxies or bypass blocks.
- Added deterministic mocked tests for connector mapping, search planning, and disabled-by-default behavior.
- All 73 backend tests passed in the development environment.


## v0.5.3 — Show all relevant leads by default

- Include timestamp-unverified leads by default so users can review more relevant jobs instead of seeing only the strict verified-fresh subset.
- The main result count is now “Jobs to review” and totals verified-fresh plus returned unverified-date leads.
- Split results into “Verified fresh matches” and “More leads to review — posting date unverified”, with clear guidance that unknown dates are not confirmed fresh.
- Users can disable the unverified-date option if they prefer a strict verified-only list.
- Set API schema defaults to include unverified leads when clients omit the field.

## v0.5.8
- Fixes Windows Playwright startup under Uvicorn reload mode by detecting `SelectorEventLoop` and returning actionable diagnostics before a driver task is leaked.
- Adds a single-worker/no-reload `backend/run_server.py` launcher that sets Windows Proactor policy before starting Uvicorn.
- Adds regression coverage for Windows SelectorEventLoop detection.

## v0.6.2
- Fix JobSpy source status when the connector is disabled by configuration.
- Isolate the test suite from local user databases and .env settings.
