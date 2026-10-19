# Location and work-type filters (v0.4.4)

## Available geography options

- Global — all regions; no geographic filtering is applied.
- India — Indian country names, many common city names, and state aliases are matched.
- Asia, Europe, Americas, Middle East, Africa, Oceania — matched against the listing location and, for remote roles, explicit regional eligibility in the description.
- Custom city/country/region — comma-separated values are accepted; a listing matches if one configured value is present in the location or a remote-work eligibility statement.

## Work arrangement

Remote, Hybrid, On-site, and Not specified are filterable independently.

## Employment type

Full-time/Permanent, Part-time, Contract/Freelance, Internship, Temporary/Seasonal, and Not specified are inferred from the title and description text. These are heuristic categories because some sources do not expose a structured employment-type field.

## Search behavior

The frontend sends selected filters to both `/api/discovery/search` and `/api/agent/run`. The backend applies geography, work-arrangement, and employment-type filters before fresh or unverified results are persisted or used to prepare application records. Discovery responses expose counts for listings excluded by each filter.

If Adzuna is configured, its country endpoints are expanded according to the selected region. The currently configured country codes do not cover all countries/regions; other enabled sources continue to be queried for supported regions. Middle East currently has no Adzuna country code in the connector's country-code list.

Generic remote listings with no explicit geography are retained in regional filters as potential leads, but location/work-eligibility must be checked on the original listing. The Global filter does not mean every website is searched; coverage is limited to enabled connectors and what each provider exposes.
