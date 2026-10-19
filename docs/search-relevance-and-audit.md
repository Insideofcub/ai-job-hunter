# Search relevance and exclusion audit (v0.5.1)

## How one search is processed

1. **Fetch** — collect listing records from enabled, working sources. `raw_postings_count` covers returned postings, not every vacancy on the web.
2. **Deduplicate** — normalize URLs and compare title/company/location fingerprints. Higher-quality copies (verified original timestamp, useful location/salary, richer description) are preferred.
3. **Role relevance** — compare title and role-family variants, then selected keywords. Recruitment/HR queries recognize Recruiter, Recruiting Coordinator, Talent Acquisition, Talent Partner, Technical Sourcer, Staffing, HRBP, HR Operations, People Operations, Executive Search, and other explicit variants. Role dictionaries are intended to improve recall without accepting unrelated titles because a description casually mentions recruitment.
4. **Location** — check the listing against the selected geographic scope or custom location. This is based on provider location text and regional aliases, not a complete geocoding database.
5. **Work arrangement** — compare remote, hybrid, on-site, or unknown classification with the selected preferences.
6. **Employment type** — compare full-time, part-time, contract/freelance, internship, temporary/seasonal, or unknown classification.
7. **Posting window** — check the source's original publication time against the rolling 24-hour, 1-day, 7-day, or 30-day window. Timestamps not verified as original publication times are kept separately as unverified leads when requested.

## API counters

- `raw_postings_count`: total normalized postings received from sources without a source error.
- `unique_postings_count`: after URL/fingerprint de-duplication.
- `duplicate_removed_count`: raw duplicates removed.
- `query_matched_count`: postings matching the selected role/title intent.
- `location_matched_count`, `work_mode_matched_count`, `employment_type_matched_count`: count remaining after each filter stage.
- `fresh_count` and `unverified_count`: final verified-fresh and separately unverified listings displayed.
- `filter_funnel`: input/pass/excluded count for each stage.
- `exclusion_reason_counts`: total counts by reason code.
- `excluded_listings`: up to 500 examples with human-readable reasons; the total counts are not capped.

## Common exclusion reason codes

| Code | Meaning |
|---|---|
| `invalid_listing` | Missing a title or usable source URL. |
| `duplicate_listing` | Another copy was retained. |
| `role_keyword_mismatch` | The title/listing did not match the selected role or recognized variant. |
| `location_mismatch` | The listing did not match the selected region/custom location based on available text. |
| `work_mode_mismatch` | Detected work arrangement was not selected. |
| `employment_type_mismatch` | Detected employment type was not selected. |
| `outside_posting_window` | Original timestamp is older than the selected rolling time window. |
| `future_or_invalid_timestamp` | Timestamp is later than the search time and not considered fresh. |
| `posting_time_unverified` | Original posting time cannot be trusted; this lead is never promoted into verified Fresh Matches. |

Each record receives the first exclusion reason at the stage where it fails. Therefore the exclusion categories describe the funnel order and should not be added to derive the unique-job count across alternate searches.

## Coverage and interpretation

A search count represents records returned by configured APIs and search results, not all open jobs in a region. The Brave connector requires a `BRAVE_SEARCH_API_KEY`, uses up to 20 query requests per run, and checks up to 48 candidate original pages. Search-engine page age or a last-modified timestamp is not treated as proof of the job's original publication time. Not all sites expose dates, full descriptions, or remote eligibility.

The Himalayas connector is remote-job-oriented. It keeps the source-supplied application URL and its source attribution. It does not replace India-wide on-site/hybrid sources.
