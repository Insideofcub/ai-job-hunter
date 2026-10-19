# Multi-portal search (v0.5.1)

## What it does

When `BRAVE_SEARCH_API_KEY` is configured, the broad-web connector creates targeted query scopes for the selected region. India mode targets public indexed pages on LinkedIn Jobs, Naukri, Indeed, Foundit, Shine, iimjobs, Instahyre, Cutshort, Wellfound, selected ATS/company career pages, and remote-job sites. Other regions swap in relevant regional boards such as StepStone/EURES, Bayt/GulfTalent/Naukrigulf, Careers24/PNet/Jobberman, and SEEK/Jora.

The current planner is capped at 20 search requests per run, with up to 20 web results per query and up to 48 original pages checked for posting evidence. It de-duplicates normalized URLs and balances original-page verification across source domains. The dashboard shows query-scope success counts, source-domain result counts, a filter funnel, and why listings were excluded. The source query plan samples India and major hubs plus portal-specific searches; it does not query every city or every vacancy.

## Verification semantics

Brave's `freshness` filter describes the search index's view of page recency (which can be based on a publication or modification date). It does not prove when a job vacancy was originally published. A listing enters the verified-fresh results only if the fetched original page has a trustworthy `JobPosting.datePosted` value or an explicit relative publication statement. Other records can be shown separately as timestamp-unverified leads when the user enables that option.

## Limitations

- Search results are public-index leads, not full integration with private or logged-in content on LinkedIn, Naukri, Indeed, or other portals.
- Coverage depends on the search provider index, the selected region, query budget, and source accessibility; it is not exhaustive by city, state, or employer.
- Some pages block automated fetches or show no publication time. In that case, the original URL can remain useful but the posting time cannot be reported as verified.
- Browser application submission remains restricted to the separately configured supported application hosts and workflows. Finding a job on a portal does not authorize submitting to that portal by automation.
- Keep API credentials in `backend/.env`. Never commit secrets to GitHub.

## API notes

The Brave Web Search API accepts search terms up to 600 characters and supports country targeting and index freshness filters; see the [official API reference](https://api-dashboard.search.brave.com/api-reference/web/search/post).


## Role-family matching and the exclusion funnel (v0.5.1)

Recruitment/HR queries expand to common title variations such as Senior Recruiter, Recruiting Coordinator, Talent Partner, Technical Sourcer, HRBP, HR Operations, People Operations, and Executive Search. Matching is title-focused; a job is not accepted only because the description makes an incidental mention of recruitment.

Every search displays a funnel showing fetched records, unique records after de-duplication, relevant roles, region matches, work-arrangement matches, employment-type matches, and listings that pass the posting-time window. Listings that do not qualify include a reason code/message when available. Unknown timestamps are not silently promoted to verified fresh jobs.

## Additional public feed

Himalayas is available as a public remote-job source. The adapter keeps the source-provided `applicationLink` for applying and labels the source for attribution. The feed is remote-oriented and therefore is not a substitute for India-wide on-site and hybrid job portals.
