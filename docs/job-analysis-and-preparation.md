# Job analysis and application preparation (v0.4.9)

## Analyze a saved job

`POST /api/jobs/{job_id}/analysis` returns a profile-match report from the local saved `Job` and `CandidateProfile`. The route 404s if the job is not saved and returns a rule-based fallback if the selected AI provider is unavailable.

The response includes an estimated score, fit summary, matching evidence, required skills, skills evidenced by profile/resume text, skills not found in that text, experience and location assessments, resume emphasis suggestions, suggested screening questions, concerns, and posting-time evidence.

`analysis_provider` and `ai_assisted` show whether the configured provider actually contributed. This is not an employer score or a factual guarantee. Skill absence from the resume is reported as "not found" and should be confirmed with the candidate.

## Prepare an application

Open **Find Jobs**, expand a saved fresh listing, and click **Prepare application**. The app creates or reuses the record in Application History, then drafts screening answers using the analysis questions. It does not submit. Review and edit all answers in Application History, and mark an answer verified only after confirming it is accurate. Legal/work-authorization/conflict questions stay blank unless an explicit matching fact is saved by the user.

## API use

```http
POST /api/jobs/123/analysis
```

No request body is required. AI output is optional and uses the model settings in `backend/.env`; the deterministic fallback always remains available.
