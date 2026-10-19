# Simple search-to-apply workflow (v0.5.1)

AI Job Hunter now opens on **Find & Apply**. The primary journey is:

1. Enter role titles or keywords and choose a posting window.
2. Optionally open Location & work filters to select geography, work arrangement, and employment type.
3. Attach a CV. If a prior search exists, the app runs discovery again after a successful CV upload so returned match scores use the newly saved resume/profile.
4. Review each result's estimated match score, source, location, work arrangement, and posting-time status.
5. Choose **Apply manually** to open the original listing and create/update an Application History record, or **Auto-apply** to prepare the application workflow.

## Manual apply

Manual apply opens the original job listing in a new browser tab and records the vacancy in local Application History if the listing has a saved job record. After finishing the form on the employer's site, mark the status as Submitted in Application History.

## Auto-apply

The button behaves according to local configuration:

- If no resume is attached, the app takes the user to My Profile to attach one.
- If `AUTO_SUBMIT_ENABLED=false` (the default), it prepares an application record and screening-answer drafts, then opens Application History for review. It does not submit.
- If `AUTO_SUBMIT_ENABLED=true`, it attempts the existing supported browser workflow. Only supported Greenhouse/Lever hosts are eligible. Required unknown fields, unverified screening answers, CAPTCHA, identity checks, or unsupported redirects stop automation for manual completion.

Never put API keys, cookies, browser profiles, resume files, or application records in Git. Before using automatic submission, verify your profile and answer drafts and review the employer site's rules.

## Where advanced controls went

Location/work/employment filters, source diagnostics, full detailed research report, source configuration, and saved-job management are expandable sections. They remain available but no longer dominate the default screen.
