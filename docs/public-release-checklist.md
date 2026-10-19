# Public GitHub release checklist

Complete this checklist before creating a public repository or publishing a release tag.

## Repository safety

- [ ] Run `python scripts/validate_release.py --root .` and resolve all errors.
- [ ] Run `python scripts/check_release.py --root .` and inspect any findings.
- [ ] Review `git status --short` and `git diff --cached --stat`.
- [ ] Confirm `.env`, API keys, browser profiles/cookies, SQLite databases, resumes, photos, uploads, and private exports are not staged.
- [ ] Run GitHub secret scanning or an equivalent secret scanner.
- [ ] Confirm license and attribution requirements for all bundled images and other assets. See `../ASSET_NOTICES.md`.

## Build and test

- [ ] In the backend virtual environment, run `python -m pytest -q` from `backend` with `PYTHONPATH=.`.
- [ ] Run `python -m compileall -q backend/app backend/run_server.py scripts`.
- [ ] In `frontend`, run `npm install --no-audit --no-fund` and `npm run build`.
- [ ] Run the local preflight and API readiness checks.
- [ ] Manually verify Find & Apply, CV upload, match score, manual apply, application queue, status tracking, and Excel export.
- [ ] Verify browser automation on a supported test application. Do not mark a submission successful without an explicit confirmation from the site.

## Documentation and release

- [ ] Confirm `VERSION`, frontend package version, and FastAPI version are aligned.
- [ ] Confirm README relative links work and setup instructions match the release.
- [ ] Confirm all required provider keys and optional dependencies are documented.
- [ ] Confirm that the theme artwork can be redistributed, or replace it with original artwork.
- [ ] Review provider terms for all enabled job discovery and application connectors.
- [ ] Create release notes and tag only after all required tests/builds pass.

## Limitations to state publicly

- Job-source coverage depends on configured sources, provider availability, search indexing, and API access.
- Posting timestamps are marked verified only when adequate original posting-time evidence is available.
- Automatic application submission works only for supported and permitted workflows and may require human interaction.
- The current build is single-user and local-first; do not expose the development server directly to the public internet.
