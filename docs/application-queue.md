# Application review queue (v0.5.4)

## User workflow

1. Search in **Find & Apply**.
2. Select one or more listings from **Verified fresh matches** or **More leads to review — posting date unverified**. The UI caps a batch at 50 jobs.
3. Choose **Prepare selected**. The backend creates or reuses Application History records; no employer application is submitted.
4. Review each record and screening answer in **Applications**. Unknown legal, work authorization, conflict-of-interest, or personal declarations remain unverified until the user confirms them.
5. Choose **Apply manually** to open the original listing and record that manual action is needed. Mark a job Submitted only after completing the employer's form.
6. Use **Fill supported form** or **Fill & submit** only for supported sites. Auto-submit remains disabled by default; it never bypasses CAPTCHA or required human verification.

## API

`POST /api/applications/queue` accepts `{"jobs": [{"job_id": 123, "title": "...", "company": "...", "source_url": "https://...", "verified_posting_time": true, "match_score": 78}]}`. For untracked leads, `job_id` may be null; the API saves the job and preserves its timestamp-verification flag. The request accepts 1–50 jobs. Results contain per-item `created`, `reused`, or `failed` actions, and `submitted` is always zero.

## Duplicate handling

Canonical source URLs are used to reuse existing Application History records. Existing statuses and screening-answer JSON are preserved. A duplicate within the same batch is not submitted twice.
