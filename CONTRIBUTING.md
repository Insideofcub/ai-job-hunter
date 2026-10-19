# Contributing

1. Open an issue to discuss substantial changes.
2. Create a focused branch: `feature/short-description`.
3. Add tests for new behavior.
4. Run backend tests and frontend lint/build checks.
5. Never commit credentials, candidate personal data, cookies, or real application records.

## Principles

- Prefer documented, permitted data sources.
- Keep AI providers behind a common interface.
- Keep automated application submission disabled by default.
- Never invent candidate facts or answer legal declarations without verified user input.


Never commit a resume or profile photo. Do not attach real candidate data to issues, pull requests, or test fixtures. Profile sections and uploaded files are treated as private personal data.

## Broad-web research connector

- Brave Search is optional and requires the developer/user's own `BRAVE_SEARCH_API_KEY` in `backend/.env`. Never place this key in frontend source, screenshots, issues, or commits.
- Keep provider requests bounded, handle rate limits/errors independently, and show per-provider diagnostics.
- Search engine result age is not original job publication time. A result may be labelled timestamp-verified only after its original page exposes a trusted `JobPosting.datePosted` or explicit relative posting-age phrase.
- Add deterministic parser/scoring tests with mocked HTTP responses; do not make automated test runs depend on a live API key.
- Do not fabricate employer, salary, required skills, employment type, or location when page metadata does not expose those facts.


## Multi-portal search

Broad-web search is implemented as targeted search-index discovery. Keep site query generation bounded (max 12 requests per run), preserve the original posting URL, and do not claim that a site's listings were exhaustively searched. Do not add scraping that bypasses login walls, CAPTCHA, anti-bot controls, or site terms. Add regression tests for query plans, source attribution, deduplication, and posting-date evidence.


## Job analysis and application preparation

- The detailed analysis endpoint must retain a deterministic fallback when the AI provider is offline.
- Never interpret a skill absent from resume text as proof the candidate lacks it. Use wording such as "not found in saved profile text; confirm".
- Suggestions are advisory; they must not update the candidate profile or submit applications.
- Application preparation may create/reuse an application record and draft questions, but no submit action is triggered.
- Keep legal, work authorization, salary, and conflict-of-interest answers grounded in user-verified facts.

## Matching changes

Keep matching scores explainable. Any semantic or AI score must be clearly labelled as an estimate, preserve a deterministic fallback, and never be described as a probability of getting hired. Add tests for provider-unavailable behavior.


## Optional JobSpy connector

JobSpy integration is opt-in and must remain behind the existing provider interface. Do not add proxy rotation, login cookies, or blocking circumvention. Preserve direct source links, distinguish original timestamps from date-only values, and mock all JobSpy calls in tests so CI never scrapes real portals. Check every site's terms before enabling its scraper.
