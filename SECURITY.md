# Security Policy

## Supported version

Please test security reports against the latest version available in this repository. This project is currently local-first and single-user; it is not safe to expose its development server directly to the public internet.

## Reporting a vulnerability

Please do not publish API keys, resumes, browser cookies, application records, or other private information in a public issue. Use GitHub's private vulnerability reporting feature for this repository if enabled by the maintainer. If private reporting is unavailable, open a minimal issue asking for a secure contact method without including exploit details or sensitive data.

## Security boundaries

- Keep `.env`, API tokens, browser profiles, database files, candidate resumes, photos, and exported application reports out of Git.
- Treat uploaded CVs and job descriptions as untrusted input.
- Do not bypass CAPTCHA, MFA, access controls, or job-site restrictions.
- Auto-submit is an explicit opt-in and should only be used with supported, permitted application flows and verified candidate answers.
- Before cloud or multi-user deployment, add authentication, authorization, per-user file access controls, rate limiting, and production secrets management.
