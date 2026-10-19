# AI Job Hunter

Current release candidate: **v0.6.3**. When one or more jobs are selected in Find & Apply, a sticky **Prepare selected (N)** action stays visible at the bottom while scrolling. Batch preparation only creates/reuses application records and drafts; it does not submit applications.

An open-source, local-first job discovery and application assistant, independent of Dots AI and licensed under MIT.

Before publishing a public release, complete the [public release checklist](docs/public-release-checklist.md) and confirm asset redistribution rights in [ASSET_NOTICES.md](ASSET_NOTICES.md).

## Phase 4 status: Simple search-to-apply, multi-portal discovery, all-reviewable leads, semantic matching, application review queue, Windows Playwright compatibility, readability uplift, and Neon Streaks dark theme (v0.6.3)



### v0.6.3 — release-candidate validation and packaging

- Adds `scripts/validate_release.py` to check required files, aligned version metadata, relative Markdown links, and private/local-file hygiene.
- Adds optional flags to run the backend tests and frontend production build as part of one pre-release command.
- Adds `scripts/package_release.py` to create a clean source ZIP while excluding local environment files, databases, browser profiles, resumes, dependency folders, and caches.
- Adds a public release checklist and security policy, plus an explicit notice that the bundled theme artwork's redistribution rights must be confirmed before public distribution.
- Extends CI to validate release metadata and documentation links.
- A passing static release check is not a substitute for a successful local frontend build, manual workflow test, and asset-rights review.

### v0.6.2 — release hardening and diagnostics

- Version metadata is now aligned across FastAPI and the frontend package (`0.6.2`).
- Added `GET /api/version` and `GET /api/system/readiness`; readiness shows database health and integration configuration states without exposing credential values.
- Added `scripts/preflight.py` for local install diagnostics and optional Ollama/embedding/Playwright readiness.
- Added `scripts/check_release.py` to catch common local databases, private candidate documents, credential files and browser-session data before public publishing.
- Added GitHub Actions CI for Python tests/compilation, Vite production build, and release hygiene checks.
- See [Release hardening checklist](docs/release-hardening.md).

### v0.6.0 — Neon Streaks theme

- Added the supplied purple/blue light-streak artwork as a local frontend asset at `frontend/public/neon-streaks-theme.png`.
- Applied a dark navy/purple surface system with neon violet, magenta, blue, and teal accents across navigation, search, job cards, profile, application history, filters, diagnostics, and modals.
- Uses the art prominently in the Overview welcome hero and subtly as the app background while keeping content surfaces dark and text contrast high.
- No backend behavior, API, or database schema changes.

### v0.5.9 — modest font-size uplift

- Slightly increases small UI text across navigation, forms, job metadata, filters, application history, diagnostics, and helper text.
- Preserves layout and existing controls; includes responsive mobile overrides.

### v0.5.8 — Windows Playwright event-loop fix

- Diagnoses the `NotImplementedError` caused when Playwright's async driver runs under Windows `SelectorEventLoop`.
- Browser readiness now checks event-loop compatibility before starting Playwright, avoiding the leaked `Task exception was never retrieved` trace.
- Adds `backend/run_server.py`, which uses a single Uvicorn process and sets the Windows Proactor event-loop policy before startup. Use it when browser form filling is needed; do not start this Windows browser-automation workflow with `--reload`.
- The browser-fill endpoint returns an actionable 503 explanation if the incompatible loop is detected.

### v0.5.6 — visible application queue action

- A sticky `Prepare selected (N)` action bar appears after selecting jobs and remains visible while scrolling.
- Includes Clear selection and explicitly states that queue preparation creates/reuses application drafts without submitting them.

### v0.5.5 — readability improvements

- Increased saved-job listing title text, company/location details, work-mode badges, posting status, verification labels, and match-score pills.
- Allows long job titles and company/location text to wrap rather than truncating them into tiny, hard-to-read snippets.
- Enlarged row spacing, company initials, icons, and list controls, with mobile-specific typography.


This phase extends the Phase 3 profile builder and adds a job-agent command, an optional JobSpy multi-portal connector (paused by default), broad-web research through an optional Brave Search API key, a ranked research report with per-job match explanations and verification evidence, local/cloud AI-assisted screening-answer drafts grounded in the user's saved profile/resume, supported-site browser form filling, application history, analytics, and Excel export.

### v0.5.4 application review queue

- Select multiple verified-fresh or timestamp-unverified leads from Find & Apply and prepare them in one batch (up to 50 at a time).
- Batch queueing creates/reuses Application History records, saves untracked leads for review without claiming their posting dates are verified, and retains per-job match scores and source URLs.
- Duplicate URLs reuse existing Application History instead of creating duplicate records; existing user-edited answers and statuses are preserved.
- Application History now offers an Apply manually action that opens the original listing and records `needs_manual_action` when appropriate. It does not mark a role submitted.
- Queue preparation never submits to employer websites. Automatic submission remains a separate per-application action, disabled by default and restricted to configured supported sites.

### v0.5.1 discovery and audit improvements

- Expands recruitment/HR title-family matching: recruiter/recruiting/recruitment, talent acquisition, sourcer, staffing, HR executive/generalist/operations/HRBP, people operations, executive search, resourcing, and related role-title variants. Title matching remains deliberately role-focused to avoid accepting unrelated roles merely because their descriptions mention hiring.
- Adds the public Himalayas remote-jobs feed as an optional no-key source. It uses the supplied `applicationLink` for the Apply action and retains visible source attribution as required by the source.
- Broadens India-specific web research with India and major-hub queries and adds further role-family variations; the Brave query plan is capped at 20 queries per run and original-page checking at 48 candidates per run. Use `BRAVE_SEARCH_API_KEY` to activate broad indexed-web discovery.
- Deduplicates results before role/location/work/employment/date filtering and records a transparent search funnel for each stage.
- Shows exclusion reason codes and explanations (e.g. duplicate, role mismatch, region mismatch, work arrangement, employment type, outside date window, or unverified posting time) so an empty result set can be diagnosed. Detailed exclusion examples are capped at 500 to bound response size; counts cover the full result set.
- Distinguishes a successful source returning zero jobs (`empty`) from a failed source (`error`). External-source calls in the automated test suite are mocked so tests run reproducibly without relying on live websites.

### What works in this phase

- Run a job-agent search across enabled/configured Greenhouse and Lever company boards, plus configured public aggregators (Arbeitnow, Remote OK, Jobicy, and Himalayas; Adzuna when credentials are provided). The optional JobSpy multi-portal connector can be enabled after installing its extra requirements and checking the target portals' terms.
- Filter jobs based on source-provided original timestamps; unknown timestamps are not falsely labeled fresh.
- Optional broad-web research queries the Brave Search API with portal-specific and regional searches. Supported indexed public domains include LinkedIn Jobs, Naukri, Indeed, Foundit, Shine, iimjobs, Instahyre, Cutshort, Wellfound, Glassdoor, regional job boards, and company career/ATS pages. It checks candidate original pages for structured `JobPosting.datePosted` data or explicit relative publication time where safely accessible. Search-engine page age alone is not treated as proof that a job was posted within the selected window.
- Source attribution is retained for discovered listings where the URL domain can be identified. Search diagnostics show query scope success and portal/domain result counts. The research plan is capped at 20 Brave queries per run and can check up to 48 candidate original pages, balancing verification attempts across source domains. Query count and candidate/page verification budgets affect coverage and API usage.
- Show a Gemini-style research report: ranked results table, estimated profile-fit score, why the role matches, inferred/observed skill evidence, posting-time verification, salary and experience when found, concerns, original listing URL, and a summary view. Scores are rule-based estimates, not employer assessments.
- Expand a saved job and choose **Analyze against my resume** for a resume/profile-grounded breakdown: match summary, required skills found/not found in the saved profile text, experience and location fit notes, resume points to emphasize, suggested screening questions, concerns, and the match-scoring method. It uses the configured Ollama/OpenAI-compatible provider for advisory text when available and returns a transparent rule-based fallback if AI is unavailable.
- Choose **Prepare application** from a job's detailed report to create or reuse an Application History record and draft tailored screening answers from the job analysis. This action does not submit an application. Answer drafts still need human review; the model never fills missing legal/work-authorization/conflict declarations by guessing.
- Match fresh jobs against the candidate profile with explainable role, skills, experience, and location/work-mode components. When local embeddings are available, combine the evidence baseline (70%) with a calibrated semantic-similarity ranking signal (30%).
- Create application-history records for qualifying fresh matches and avoid duplicate applications by canonical URL.
- Generate answers for the actual screening prompts detected on supported application pages, plus common screening prompts. Configure `AI_PROVIDER=ollama` for a local Ollama model or `AI_PROVIDER=openai` for an OpenAI-compatible cloud endpoint. Non-sensitive generated text remains a draft until you review and mark it verified. Legal, visa/work-authorization, conflicts, and other unknown personal declarations stay blank and `needs_review` unless a matching fact was explicitly saved in the profile.
- Update application status: ready for review, manual action, submitted, unconfirmed submission, interview, offer, rejected, withdrawn, and failed.
- View application counts and statuses in the Analytics panel.
- Download `.xlsx` workbook with Analytics, Applications, and Screening Answers sheets.
- Launch a visible browser session to fill mapped fields, generate drafts for unrecognized non-sensitive screening questions, and attach the user's stored resume for supported Greenhouse/Lever-hosted application pages. Automatic submission is blocked unless a valid resume is attached and all filled screening answers marked for submission are verified.
- Optional submission is disabled by default, requires explicit local environment configuration and a per-action confirmation, and stops when required fields are unresolved or a CAPTCHA/human verification is detected.

## Important coverage limitation

There is no single API that grants universal access to every global job site. Discovery combines configured public sources (Greenhouse, Lever, Arbeitnow, Remote OK, Jobicy, Himalayas, and Adzuna when credentials are provided) with optional Brave Search indexing (requires a Brave API key). The Brave connector uses targeted public web searches for domains such as LinkedIn Jobs, Naukri, Indeed, Foundit, Shine, iimjobs, Instahyre, Cutshort, Wellfound, Glassdoor, regional job boards, and company career/ATS pages. This is search-index discovery, not a direct LinkedIn/Naukri/Indeed API integration, and it does not access private/login-only content or automatically submit applications to those portals. Results depend on what the search provider indexes, query budget, and whether original pages are accessible. When Adzuna credentials are configured, the chosen geography selects supported country endpoints; provider country coverage is not universal. Unsupported application sites remain available for manual application.

Browser form filling is limited to a hostname allowlist for Greenhouse and Lever. Do not bypass CAPTCHA, identity checks, MFA, anti-bot controls, access restrictions, or a platform's terms. Some jobs require human-entered answers or additional consent. The agent is not allowed to invent candidate facts.

## Prerequisites

- Python 3.11+
- Node.js 20+
- npm
- For visible application-form filling: Playwright Chromium (`python -m playwright install chromium`)

## Run on Windows (PowerShell)

### 1. Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Optional once you deliberately choose to enable submission, after reviewing site rules:
# Set AUTO_SUBMIT_ENABLED=true in backend/.env and restart the backend.
python -m playwright install chromium
# Use the no-reload runner for browser automation on Windows.
python run_server.py
```

API: http://127.0.0.1:8000
Interactive API docs: http://127.0.0.1:8000/docs

### 2. Frontend (new PowerShell window)

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Frontend: http://localhost:5173


## Broad web research setup

To enable a wider search similar to the attached research-report reference, create a Brave Search API key using the provider's official API console and add it to `backend/.env`:

```dotenv
BRAVE_SEARCH_API_KEY=your_private_brave_search_key
```

Restart FastAPI after saving the key. Keep the key private and out of GitHub. The research connector plans up to 20 region- and portal-targeted web-search requests per run, with up to 20 results per request and original-page checks capped at 48 candidates per run; it de-duplicates candidates, balances original-page checks across domains, and reports both query-scope and source-domain diagnostics. API quota, access, and any charges are governed by your Brave account. See the official [Brave Search API documentation](https://api.search.brave.com/app/documentation/web-search/get-started) for current terms and usage details.

The connector uses Brave's country targeting and supported freshness options as a discovery aid. The selected local posting window is still applied to original publication times when the page exposes trustworthy evidence. A search result's crawl/page age is not the same thing as a job's original datePosted. Pages without sufficient evidence remain in the timestamp-unverified section. Some job boards block requests, require sign-in, or provide no publication date; those vacancies may be visible as leads but cannot be reported as verified fresh.

The research table includes role, company, location/work mode, posted-time evidence, required experience, salary when discoverable, an explainable estimated match score, source link, reasons, skills and concerns. Fields not found in the listing are shown as unknown/not disclosed rather than fabricated.

## AI provider configuration

Local Ollama is the default:

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b-instruct
```

Make sure Ollama is running and the selected model is available. To use an OpenAI-compatible cloud API instead, set `AI_PROVIDER=openai`, configure `OPENAI_BASE_URL`, `OPENAI_MODEL`, and `OPENAI_API_KEY` in `backend/.env`. In cloud mode, candidate profile and resume excerpts may be sent to that provider to draft answers. Keep the API key private. If the configured AI provider is unavailable, the app falls back to conservative rule-based drafts; legal/sensitive answers are never supplied by the model.

## Job agent workflow

1. Complete your profile and upload the resume you intend to use. Add explicit facts such as notice period, salary, work authorization, and other sensitive declarations to the verified-facts profile field only when they are accurate.
2. In Overview, enter a job instruction such as `Talent Acquisition, IT Recruiter, HR Recruiter, Technical Recruiter`.
3. Add supported Greenhouse/Lever company boards in Find Jobs. The agent checks all enabled boards configured in your local source list.
4. Click **Run job agent**. It searches verified-fresh listings, ranks them with the current transparent keyword score, and adds suitable opportunities to Application History.
5. In Find Jobs, expand a fresh listing and choose **Analyze against my resume** to inspect profile fit, skill evidence and potential gaps. Choose **Prepare application** to create/reuse its history record and draft job-specific screening questions. This action does not submit anything.
6. In Application History, review/edit screening answers and choose **I reviewed this answer** to mark an answer verified. Open the original listing or choose **Fill supported form**. The visible browser remains open for your review; the app remembers the local browser session so you can manually sign in if the site supports it.
7. For optional submission, set `AUTO_SUBMIT_ENABLED=true` in `backend/.env`, restart the backend, and use the explicit **Fill & submit** action. Submission is blocked if the site is unsupported, required fields remain unmapped, or human verification is detected. A clicked submit without a clear success message is recorded as unconfirmed.
8. Use **Download Excel** to export the current application history and answer drafts.


## Search error handling update (v0.4.2)

- Find Jobs query input accepts up to 2,000 characters so short natural-language instructions are not rejected by the older 500-character limit.
- API validation arrays and object-shaped errors are rendered as readable messages instead of `[object Object]`.
- Discovery extracts role phrases from the first sentence and strips common instruction wrappers before keyword filtering.
- An unexpected connector response is reported in that source's status row, where possible, instead of stopping all sources.

Read [Search relevance and exclusion audit](docs/search-relevance-and-audit.md) for the funnel stages and exclusion reason codes.

## API overview

- `GET /api/health` - API status
- `GET /api/jobs`, `POST /api/jobs` - saved job tracker
- `GET /api/jobs/matches` - explainable baseline match score
- `GET/POST/PATCH/DELETE /api/sources` - configured Greenhouse/Lever boards and public aggregators
- `POST /api/discovery/search` - source discovery, optional Brave broad-web research, research scoring, and freshness filtering
- `POST /api/agent/run` - run search, rank fresh matches, create application records, optionally perform supported browser apply attempts when submission is configured
- `GET/POST /api/applications`, `POST /api/applications/from-job/{id}`, `PATCH /api/applications/{id}` - application history
- `POST /api/applications/{id}/answers/generate` - AI-assisted, resume-grounded answer drafts
- `PATCH /api/applications/{id}/answers/{index}` - save/edit a draft or mark a reviewed answer verified
- `POST /api/applications/{id}/browser-fill` - visible supported browser form filling
- `GET /api/automation/settings` - auto-submit state and supported host list
- `GET /api/analytics` - application analytics
- `GET /api/analytics/export.xlsx` - Excel export
- `GET/PUT /api/profile`, plus resume/photo upload endpoints - candidate profile

## Excel export

The workbook contains:

1. `Analytics`: totals, submitted attempts, review queue, interviews/offers/rejections, 7-/30-day counts, status totals, and platform totals.
2. `Applications`: job title, employer, location, work mode, source/platform, status, match score, direct URL, application/creation/update timestamps, resume filename, matched keywords, notes, last result, and confirmation ID.
3. `Screening Answers`: question, answer draft, review status, confidence, and evidence/source note for each application.

Exported spreadsheets contain personal job-search records. Keep them private and do not commit them to GitHub.

## Local data and privacy

- SQLite defaults to `backend/ai_job_hunter.db`.
- Resumes: `backend/data/resumes/`.
- Profile photos: `backend/data/photos/`.
- Browser login profile: `backend/data/browser-profile/`.
- These data paths are excluded by `.gitignore`. Never commit a CV, photo, browser cookies, tokens, or application history.
- This build is single-user/local-first. Do not expose the development server directly to the public internet. Before cloud deployment, add authentication, authorization, per-user data isolation, secure file access, database migrations, rate limiting, and secrets management.

## Local diagnostics and release checks (v0.6.2)

From the project root:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\preflight.py
py scripts/check_release.py --root .
```

The first command checks local prerequisites. The second flags common local/private files before a public GitHub push. Review the staged Git diff manually too; neither script can guarantee that all secrets or personal information have been removed.

API checks:
- `GET /api/health` (includes the release version)
- `GET /api/version`
- `GET /api/system/readiness`

See [docs/release-hardening.md](docs/release-hardening.md).

## Tests

From `backend`:

```powershell
$env:PYTHONPATH = "."
python -m pytest -q
```

## Roadmap

1. Project foundation (complete)
2. Public job-board discovery and freshness verification (configured company boards and public aggregators; Adzuna needs credentials)
3. Resume/profile builder and basic match scoring (complete)
4. Simple search-to-apply workflow, application history, analytics, and Excel export (complete)
5. Multi-portal search, recruiter/HR title variants, semantic/rule-based matching, and exclusion audit (v0.5.1)
6. Improve matching calibration using user-reviewed results and add optional scheduled search runs
7. Add more permitted portal/ATS-specific adapters and validate browser flows per supported site
8. Authentication, multi-user isolation, database migration strategy, and cloud deployment hardening

## License

MIT. See [LICENSE](LICENSE).

## Posting-time filters

The Find Jobs page and Run Job Agent command share a configurable posting window: past 24 hours, past 1 day, past 7 days, or past 1 month. The 1-day preset is also 24 hours; the 1-month preset is defined as 30 days (720 hours). Results are only called timestamp-verified when the source provides a trustworthy original publication timestamp. Listings without one are kept separate as unverified.

## Search diagnostics and default public feeds (v0.4.3)

On first startup, the local application automatically registers the public Arbeitnow and Remote OK feeds (once only) alongside configured company-specific Greenhouse/Lever boards. If Adzuna API credentials are already configured, India, UK, and US Adzuna sources are also added. Users may pause or remove these sources in the dashboard.

After a search, the Find Jobs screen reports total postings fetched, postings matching the query, listings excluded by the selected date window, and matching listings whose publication timestamps could not be verified. It also places per-source success/error details above the results so zero-result searches can be diagnosed.

The 24-hour, 7-day, and 30-day filters use rolling time windows. “Include unverified timestamps” does not mark unknown dates as fresh; it displays those listings in a separate section. A timestamp provided by a source is treated as verified only when its adapter recognizes that field as the original publication timestamp.

Public feeds and Brave-indexed queries improve discovery coverage but do not make this a universal connector for every job board. LinkedIn, Naukri, Indeed, and other portals are searched through public indexed pages when the search provider has indexed them; this is not a direct integration with their private APIs or logged-in content, and it does not automate submitting applications on those portals. Some sources need API credentials, and unsupported application flows must be completed manually.


## v0.4.3: search coverage and diagnostics

- Added the no-key Jobicy public remote-jobs API for global/remote and APAC-oriented discovery. Jobicy states that the public API returns listings published in its latest seven-day window; the UI retains the Jobicy listing URL and displays its source label.
- First startup adds Arbeitnow, Remote OK, and Jobicy once. If Adzuna credentials are present at first startup, it also adds India, UK, and US sources. A database marker prevents deleted feeds from being re-added after later restarts.
- The search results now report raw fetched postings, query-matched postings, listings excluded by the date window, and timestamp-unverified candidates. Source errors are shown near the top of the results.
- Recruiting/HR searches now include common title variants such as Senior Recruiter and Recruiting Coordinator without treating any job whose description merely mentions recruitment as a match.
- Timestamps supplied by a source but not verified as the original publication time are routed to the unverified bucket rather than silently dropped.


## v0.4.4: Geographic and work-type filters

Find Jobs and Run Job Agent share a common search-filter model:

- Geography: Global (all regions), India (all states and commonly listed cities), Asia, Europe, Americas, Middle East, Africa, Oceania, and Custom city/country/region.
- Work arrangement: Remote, Hybrid, On-site, and Not specified.
- Employment type: Full-time/Permanent, Part-time, Contract/Freelance, Internship, Temporary/Seasonal, and Not specified.
- The selected location, arrangements, and employment types are applied in the backend before results are saved to the local job tracker or passed into application preparation.
- Diagnostic counters show how many keyword-matching listings were filtered by geography, work arrangement, and employment type.
- If Adzuna credentials are configured, India/Asia, Europe, Americas, Africa, Oceania, and Global searches select the corresponding supported country endpoints. Adzuna does not currently provide an endpoint for every region (for example, Middle East), and the existing public feeds cannot guarantee comprehensive coverage of every city or website.
- Generic remote listings whose eligible countries are not disclosed may remain visible in a regional search; open the original listing to verify where the employer permits remote work.

The location filters are a practical rule-based filter over the listings returned by enabled sources, not a geocoding database. India city aliases cover many common listings, but provider inventory and location formatting determine actual coverage. A Global search removes region restrictions; it still searches only enabled/configured sources and country endpoints exposed by those providers.

## Multi-portal discovery update (v0.4.7)

- India searches use dedicated portal queries for LinkedIn Jobs, Naukri, Indeed, Foundit, Shine, iimjobs, Instahyre, Cutshort, Wellfound, ATS/company career pages, and remote boards.
- Region-specific searches add the relevant regional boards (for example, StepStone/EURES in Europe, Bayt/GulfTalent/Naukrigulf in the Middle East, and SEEK/Jora in Oceania).
- Global searches sample several country-localized searches alongside dedicated portal families. This is broad multi-source discovery, not exhaustive coverage of every city or employer.
- The report identifies the hosting portal/domain when it can be inferred from the original listing URL and includes query-success and domain result counts in the search diagnostics.
- Public index results are leads. Original-page posting dates must still be verified; a page's search-index age or last-modified date is not enough on its own.


## Troubleshooting update (v0.4.7)

- If `auto_apply` is requested while `AUTO_SUBMIT_ENABLED=false`, `/api/agent/run` now continues discovery and application preparation, skips submission, and returns a clear warning instead of rejecting the entire run with HTTP 403. The individual browser-submit endpoint remains protected.
- When a configured Lever board returns HTTP 404, the connector reports a readable configuration message and automatically pauses that board to avoid repeated stack traces. Remove the invalid board and add a real Lever site slug to restore that source.


## v0.4.8 — Job analysis and application preparation

- Added `POST /api/jobs/{job_id}/analysis` to return an explainable, resume-grounded breakdown for a saved job. It combines the current rule-based score with a configured Ollama/OpenAI-compatible analysis when the provider responds.
- The response separates skills evidenced by saved profile/resume text from skills not found there; absence from the text is not treated as proof the candidate lacks a skill.
- The Find Jobs research report now exposes **Analyze against my resume** and **Prepare application** for saved job listings. Prepare application creates/reuses a local application record and generates suggested screening-answer drafts based on the role analysis, but does not submit.
- AI summary/recommendation content is advisory and must be reviewed; rule-based evidence stays visible, unknown facts remain unknown, and legal/sensitive screening responses are not fabricated.
- Adds API tests for rule-based fallback, AI-provider responses, and missing job handling.


## v0.4.9 — Optional local semantic matching

- Added an Ollama `/api/embed` integration for embedding-based ranking using the configurable `OLLAMA_EMBEDDING_MODEL` (default `nomic-embed-text`).
- Added a hybrid score for discovery results, saved-job matches, and detailed job analysis: 70% explainable rule-based evidence plus 30% calibrated semantic similarity. The semantic scale is a heuristic ranking signal, not a probability of getting hired.
- Added visible method labels and score breakdowns for role relevance, skills alignment, experience fit, and location/work-mode fit, plus semantic similarity when available.
- Semantic ranking is optional. If Ollama is unavailable or the embedding model is missing, the application continues with its rule-based score and explains how to enable embeddings.
- Added regression tests for cosine similarity, score calibration/blending, provider outage fallback, disabled mode, and async endpoint compatibility with application workflows.

## v0.5.1 — Search relevance, source coverage, and exclusion audit

- Expanded recruitment/HR query synonyms and introduced title-family explanations to improve relevant vacancy recall without accepting unrelated roles by default.
- Added the public Himalayas remote-job feed using source-supplied application links and attribution.
- Expanded the Brave search plan to up to 20 targeted queries and up to 48 original-page checks per run; this requires user-configured API credentials and remains limited by provider indexes.
- Added a search funnel (raw → unique → role relevance → location → work arrangement → employment type → posting window), exclusion reason counts, and sample excluded listings with human-readable reasons.
- Distinguishes an empty successful source response from an actual source error.
- Added an offline-safe test fixture so integration tests do not depend on live job boards; all 66 backend tests pass.

## v0.5.0 — Simple search-to-apply workflow

The default landing view is now **Find & Apply**: search enabled sources, attach/replace your resume, see saved profile-fit scores on result cards, then choose **Apply manually** or **Auto-apply**. Manual apply opens the original listing and records it in Application History. Auto-apply prepares the application and screening drafts; actual submission only runs when `AUTO_SUBMIT_ENABLED=true`, a supported site is detected, a resume is attached, and the browser workflow allows submission. Human verification or unknown required fields stop automation.

Location, posting-window, work arrangement, employment-type, source diagnostics, source management, and saved-job management are available in expandable sections to keep the primary workflow simple.

Read the [simple search-to-apply workflow](docs/simple-search-to-apply.md) for the CV upload, manual apply, and guarded auto-apply behavior.


## Optional JobSpy connector (experimental)

AI Job Hunter can optionally use `python-jobspy` to query several job boards from one connector. It is **disabled by default** and its source appears paused in Manage Sources. It does not use proxies, cookies, account sessions, or mechanisms intended to bypass blocking. Check the terms for each target site and use only where permitted. Source behavior may vary by market, rate limits, and upstream changes.

To opt in on Windows, from `C:\Projects\ai-job-hunter-phase4` run:

```powershell
cd backend
..\.venv\Scripts\Activate.ps1
pip install -r requirements-jobspy.txt
```

Then add to `backend/.env` and restart the backend:

```dotenv
JOBSPY_ENABLED=true
JOBSPY_SITES=linkedin,indeed,naukri,glassdoor,zip_recruiter,bayt,bdjobs,hellowork
JOBSPY_MAX_SEARCHES=6
JOBSPY_RESULTS_WANTED=12
```

Finally, open **Find & Apply → Manage sources** and enable **JobSpy Multi-Portal Search**. The connector makes at most `JOBSPY_MAX_SEARCHES` bounded role/location search calls per run, with a modest results cap. It does not include Google Jobs because JobSpy's current README says Google Jobs is unavailable. No original posting timestamp is invented: date-only `date_posted` values remain unverified and appear separately.

This connector is discovery-only. It does not submit applications through JobSpy. Apply using supported application workflows or the original listing, and pause the connector if a portal returns access restrictions or rate limits.


## v0.5.3 results behavior

By default, Find & Apply shows both verified-fresh jobs and relevant listings with unverified original posting dates. The two groups remain clearly separated; an unknown timestamp is never labelled fresh. Turn off “Also show relevant leads with unverified posting dates” for a strict verified-only display. Rerun the search after installing this update to load unverified leads for that search.

## Browser automation troubleshooting (v0.5.7)

If the UI shows `Browser application workflow could not start (HTTP 503)`, open **Settings → Browser automation readiness → Check browser setup**. The check reports the exact Python interpreter running FastAPI, whether Playwright can be imported, and whether Chromium is installed.

On Windows, run all commands in the same virtual environment used to start Uvicorn:

```powershell
cd C:\Projects\ai-job-hunter-phase4\backend
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable); import playwright; print(playwright.__file__)"
python -m pip install -r requirements.txt
python -m playwright install chromium
```

If your virtual environment is located at the project root instead of `backend\.venv`, activate `..\.venv\Scripts\Activate.ps1` instead. After installing, stop and restart Uvicorn. Do not activate one environment and install Playwright into another.

Browser automation is limited to supported Greenhouse/Lever hosts. If the page redirects to another host or requires CAPTCHA / human verification, complete the application manually.
## Neon Streaks theme (v0.6.2)
The app now includes a dark neon theme inspired by purple/blue light streak artwork. The background image is bundled locally at `frontend/public/neon-streaks-theme.png`; the app does not need a network request to load this image.

To update an existing local installation, back up the project, extract the release ZIP over the same project directory, preserve your `.env` and local database, and restart Vite (`npm run dev`).



## v0.6.2 hotfix

- Isolates pytest against a temporary SQLite database so tests never mutate a developer's local application database.
- Reports JobSpy as operationally disabled unless both its saved source toggle and `JOBSPY_ENABLED=true` are enabled.
