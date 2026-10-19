# Posting Window Filters (v0.4.1)

The Find Jobs search and Overview job-agent command share one posting-window preference.

| UI option | Filter window |
|---|---:|
| Past 24 hours | 24 hours rolling from search time |
| Past 1 day | 24 hours rolling from search time |
| Past 7 days | 168 hours |
| Past 1 month | 720 hours (30 days) |

The 24-hour and 1-day presets intentionally use the same rolling interval. The two labels are provided because they were specifically requested; the 1-month preset is defined as 30 days, not a calendar-month boundary.

The API accepts `hours` from 1 through 720 for both `/api/discovery/search` and `/api/agent/run`. Listings only enter the verified-fresh results when the source supplies a trustworthy publication timestamp. Listings with unknown timestamps remain separate and must not be represented as verified fresh.
