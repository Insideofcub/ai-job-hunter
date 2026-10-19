# Optional JobSpy connector

JobSpy is an experimental, opt-in discovery connector. It is seeded as a paused source. It requires installing `backend/requirements-jobspy.txt`, setting `JOBSPY_ENABLED=true`, restarting FastAPI, and enabling the source in Find & Apply → Manage Sources.

Configuration:

```dotenv
JOBSPY_ENABLED=false
JOBSPY_SITES=linkedin,indeed,naukri,glassdoor,zip_recruiter,bayt,bdjobs,hellowork
JOBSPY_MAX_SEARCHES=6
JOBSPY_RESULTS_WANTED=12
```

The connector uses `python-jobspy` to query supported portals such as LinkedIn, Indeed, Naukri, Glassdoor, ZipRecruiter, Bayt, BDJobs, and HelloWork. Coverage depends on the requested market and what each portal currently permits or exposes. The code does not configure proxies, login state, browser cookies, or any blocking workaround. If access is rejected or rate-limited, the result is reported rather than circumvented.

A run is bounded to a small number of role/location combinations. JobSpy's per-board errors/warnings are surfaced in source diagnostics. Search-time age filters are sent to JobSpy, but a day-only publication date is **not** represented as an exact timestamp; it remains in the unverified-date results.

This connector only discovers postings. It does not apply to jobs. Application submission remains in the separate supported application workflow.
