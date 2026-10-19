"""Optional broad-web job research through the Brave Search API.

Search results are treated as leads, not proof of posting date. A posting's time is
verified only when the original page exposes structured JobPosting.datePosted or an
explicit relative publication age. This is optional and requires BRAVE_SEARCH_API_KEY.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import socket
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from .job_sources.base import NormalizedPosting
from .discovery import query_phrases, canonicalize_job_url

REGION_COUNTRIES = {
    "global": ["IN", "US", "GB", "SG", "DE", "AE", "AU"],
    "india": ["IN"],
    "asia": ["IN", "SG", "JP", "KR"],
    "europe": ["GB", "DE", "FR", "NL"],
    "americas": ["US", "CA", "BR"],
    "middle_east": ["AE", "SA", "QA"],
    "africa": ["ZA", "NG", "EG"],
    "oceania": ["AU", "NZ"],
}
COUNTRY_NAMES = {
    "IN": "India", "US": "United States", "GB": "United Kingdom", "SG": "Singapore",
    "DE": "Germany", "AE": "United Arab Emirates", "AU": "Australia", "JP": "Japan",
    "KR": "South Korea", "FR": "France", "NL": "Netherlands", "CA": "Canada",
    "BR": "Brazil", "SA": "Saudi Arabia", "QA": "Qatar", "ZA": "South Africa",
    "NG": "Nigeria", "EG": "Egypt", "NZ": "New Zealand",
}
JOB_WORDS = ("job", "jobs", "career", "careers", "vacancy", "vacancies", "apply", "recruiter", "recruiting", "recruitment", "talent acquisition", "talent sourcer", "talent partner", "staffing", "headhunter", "human resources", "human resource", "hr executive", "hr generalist", "hrbp", "hr business partner", "hr operations", "people operations", "people ops", "people partner", "executive search", "resourcing", "sourcing specialist", "hiring")
ROLE_SKILLS = (
    "it recruitment", "technical recruitment", "non-it recruitment", "end-to-end recruitment",
    "talent acquisition", "boolean search", "linkedin recruiter", "candidate sourcing", "talent mapping",
    "stakeholder management", "interview coordination", "executive search", "leadership hiring",
    "ai hiring", "machine learning", "data science", "python", "sql", "power bi", "sap", "salesforce",
    "ats", "workday", "greenhouse", "lever", "naukri", "indeed", "excel", "recruitment analytics",
)


def freshness_code(hours: int) -> str | None:
    if hours <= 24:
        return "pd"
    if hours <= 168:
        return "pw"
    if hours <= 744:
        return "pm"
    return None


def _custom_country(location: str) -> list[str]:
    value = (location or "").lower()
    patterns = {
        "IN": ("india", "delhi", "gurugram", "gurgaon", "noida", "mumbai", "bengaluru", "bangalore", "hyderabad", "pune", "chennai"),
        "US": ("united states", "usa", "new york", "california", "texas", "seattle", "austin"),
        "GB": ("united kingdom", "uk", "england", "london", "manchester"),
        "SG": ("singapore",), "DE": ("germany", "berlin", "munich"), "AE": ("uae", "united arab emirates", "dubai", "abu dhabi"),
        "AU": ("australia", "sydney", "melbourne"), "CA": ("canada", "toronto", "vancouver"),
        "FR": ("france", "paris"), "NL": ("netherlands", "amsterdam"), "JP": ("japan", "tokyo"),
    }
    for code, terms in patterns.items():
        if any(term in value for term in terms):
            return [code]
    return []


def _portal_query_templates(region: str) -> list[tuple[str, str]]:
    """Return (display label, site restriction) pairs tuned for a search region.

    Search-engine discovery uses only public indexed pages. It does not sign into,
    scrape private account content from, or bypass access controls on job portals.
    """
    core = [
        ("LinkedIn Jobs", "site:linkedin.com/jobs/view"),
        ("Indeed", "site:indeed.com/viewjob OR site:indeed.com/jobs"),
    ]
    regional = {
        "india": [
            ("Naukri", "site:naukri.com/job-listings"),
            ("Foundit", "site:foundit.in/job"),
            ("Shine", "site:shine.com/jobs"),
            ("iimjobs", "site:iimjobs.com/j"),
            ("Instahyre", "site:instahyre.com"),
            ("Cutshort", "site:cutshort.io/jobs"),
            ("Wellfound", "site:wellfound.com/jobs"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:remoterocketship.com/company OR site:jobicy.com OR site:arbeitnow.com OR site:remoteok.com)"),
        ],
        "asia": [
            ("Asian job boards", "(site:jobstreet.com OR site:jobsdb.com OR site:foundit.sg OR site:foundit.in)"),
            ("India recruitment boards", "(site:naukri.com/job-listings OR site:iimjobs.com/j OR site:instahyre.com OR site:cutshort.io/jobs)"),
            ("Wellfound and startup roles", "(site:wellfound.com/jobs OR site:glassdoor.com/Job)"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:jobicy.com OR site:remoteok.com OR site:remoterocketship.com/company)"),
        ],
        "europe": [
            ("European job boards", "(site:stepstone.com OR site:eures.europa.eu OR site:totaljobs.com OR site:reed.co.uk)"),
            ("Glassdoor and Wellfound", "(site:glassdoor.com/Job OR site:wellfound.com/jobs)"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:jobicy.com OR site:remoteok.com OR site:remoterocketship.com/company)"),
        ],
        "americas": [
            ("Glassdoor and ZipRecruiter", "(site:glassdoor.com/Job OR site:ziprecruiter.com/jobs)"),
            ("Wellfound and startup roles", "site:wellfound.com/jobs"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:jobicy.com OR site:remoteok.com OR site:remoterocketship.com/company)"),
        ],
        "middle_east": [
            ("Middle East job boards", "(site:bayt.com OR site:gulftalent.com OR site:naukrigulf.com)"),
            ("Glassdoor and Wellfound", "(site:glassdoor.com/Job OR site:wellfound.com/jobs)"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:jobicy.com OR site:remoteok.com OR site:remoterocketship.com/company)"),
        ],
        "africa": [
            ("African job boards", "(site:careers24.com OR site:pnet.co.za OR site:jobberman.com)"),
            ("Glassdoor and Wellfound", "(site:glassdoor.com/Job OR site:wellfound.com/jobs)"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:jobicy.com OR site:remoteok.com OR site:remoterocketship.com/company)"),
        ],
        "oceania": [
            ("Australia and New Zealand job boards", "(site:seek.com.au OR site:seek.co.nz OR site:jora.com)"),
            ("Glassdoor and Wellfound", "(site:glassdoor.com/Job OR site:wellfound.com/jobs)"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:jobicy.com OR site:remoteok.com OR site:remoterocketship.com/company)"),
        ],
        "custom": [
            ("Naukri and Indian niche boards", "(site:naukri.com/job-listings OR site:foundit.in/job OR site:shine.com/jobs OR site:iimjobs.com/j)"),
            ("International boards", "(site:glassdoor.com/Job OR site:wellfound.com/jobs OR site:ziprecruiter.com/jobs)"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:jobicy.com OR site:remoteok.com OR site:remoterocketship.com/company)"),
        ],
    }
    if region == "global":
        return core + [
            ("Indian job portals", "(site:naukri.com/job-listings OR site:foundit.in/job OR site:shine.com/jobs OR site:iimjobs.com/j)"),
            ("Startup and professional job boards", "(site:wellfound.com/jobs OR site:glassdoor.com/Job OR site:cutshort.io/jobs OR site:instahyre.com)"),
            ("Company career pages and ATS boards", "(site:boards.greenhouse.io OR site:jobs.lever.co OR site:jobs.ashbyhq.com OR site:myworkdayjobs.com)"),
            ("Global and remote boards", "(site:jobicy.com OR site:remoteok.com OR site:remoterocketship.com/company OR site:arbeitnow.com)"),
        ]
    return core + regional.get(region, regional["custom"])


def portal_label_for_url(url: str) -> str:
    """Get the visible origin/site name from a listing URL without guessing its employer."""
    host = (urlsplit(url or "").hostname or "").lower().removeprefix("www.")
    labels = [
        (("linkedin.com",), "LinkedIn Jobs"), (("naukri.com",), "Naukri"),
        (("indeed.com",), "Indeed"), (("foundit.in",), "Foundit"),
        (("shine.com",), "Shine"), (("iimjobs.com",), "iimjobs"),
        (("instahyre.com",), "Instahyre"), (("cutshort.io",), "Cutshort"),
        (("wellfound.com",), "Wellfound"), (("glassdoor.com",), "Glassdoor"),
        (("stepstone.com",), "StepStone"), (("eures.europa.eu",), "EURES"),
        (("totaljobs.com",), "Totaljobs"), (("reed.co.uk",), "Reed"),
        (("jobstreet.com",), "JobStreet"), (("jobsdb.com",), "JobsDB"),
        (("seek.com.au", "seek.co.nz"), "SEEK"), (("jora.com",), "Jora"),
        (("bayt.com",), "Bayt"), (("gulftalent.com",), "GulfTalent"),
        (("naukrigulf.com",), "Naukri Gulf"), (("careers24.com",), "Careers24"),
        (("pnet.co.za",), "PNet"), (("jobberman.com",), "Jobberman"),
        (("ziprecruiter.com",), "ZipRecruiter"), (("boards.greenhouse.io", "greenhouse.io"), "Greenhouse company board"),
        (("jobs.lever.co", "lever.co"), "Lever company board"), (("jobs.ashbyhq.com", "ashbyhq.com"), "Ashby company board"),
        (("myworkdayjobs.com", "workday.com"), "Workday company careers"),
        (("jobicy.com",), "Jobicy"), (("remoteok.com",), "Remote OK"),
        (("arbeitnow.com",), "Arbeitnow"), (("remoterocketship.com",), "Remote Rocketship"),
        (("adzuna.com",), "Adzuna"),
    ]
    for domains, label in labels:
        if any(host == domain or host.endswith("." + domain) for domain in domains):
            return label
    return host or "Web search result"


def _query_scope_label(search_query: str) -> str:
    """Summarize the portal/domain targeting used by one search query."""
    domains = re.findall(r"site:([a-z0-9.-]+)", search_query.lower())
    if not domains:
        return "General web search"
    labels = list(dict.fromkeys(portal_label_for_url("https://" + domain) for domain in domains))
    if len(labels) == 1:
        return labels[0]
    if len(labels) <= 3:
        return " / ".join(labels)
    return "Multi-portal job search"


def build_search_plan(query: str, region: str, custom_location: str, hours: int) -> list[tuple[str, str]]:
    """Build a wider, multi-stage portal search plan, capped at 20 API queries/run.

    Search-index discovery is not exhaustive: country/locality and portal scopes sample
    the market. Results remain leads until the original job page can be checked.
    """
    phrases = [phrase[:70] for phrase in query_phrases(query)[:4]] or ["recruiter", "talent acquisition"]
    role_terms = " OR ".join(f'"{phrase}"' for phrase in phrases)
    region = (region or "global").lower()
    countries = _custom_country(custom_location) if region == "custom" else REGION_COUNTRIES.get(region, REGION_COUNTRIES["global"])
    if not countries:
        countries = ["IN", "US", "GB"]
    place_hint = custom_location.strip() if region == "custom" else {
        "india": "India", "asia": "Asia", "europe": "Europe", "americas": "Americas",
        "middle_east": "Middle East", "africa": "Africa", "oceania": "Australia OR New Zealand", "global": "global",
    }.get(region, "global")

    plan: list[tuple[str, str]] = []
    if region == "india":
        # Explicit Indian hubs improve recall for city-only listings while maintaining
        # India country targeting. This is a sample, not a promise every city was searched.
        localities = ["India", "Delhi NCR", "Bengaluru", "Mumbai", "Hyderabad", "Pune"]
        for place in localities:
            plan.append((f'({role_terms}) (job OR jobs OR careers OR hiring) "{place}"', "IN"))
    elif region == "global":
        for country in ["IN", "US", "GB", "DE", "AE", "AU"]:
            place = COUNTRY_NAMES.get(country, country)
            plan.append((f'({role_terms}) (job OR jobs OR careers OR hiring) "{place}"', country))
    else:
        for country in countries[:5]:
            place = custom_location.strip() if region == "custom" else COUNTRY_NAMES.get(country, country)
            plan.append((f'({role_terms}) (job OR jobs OR careers OR hiring) "{place}"', country))

    # Run distinct portal/domain searches to improve source diversity instead of one
    # large OR query dominating the results. These are public indexed-page searches only.
    portal_specs = _portal_query_templates(region)
    portal_country = countries[0] if countries else "IN"
    for _label, scope in portal_specs:
        region_terms = f'"{place_hint}"' if place_hint != "global" else '(remote OR worldwide OR international)'
        plan.append((f'({role_terms}) (job OR jobs OR career OR hiring) {scope} {region_terms}', portal_country))

    # Related title families recover listings that use common equivalents rather than
    # the exact phrase in the candidate's search box. These are not a substitute for
    # post-fetch relevance checks, which remain explainable and testable.
    variants = [
        '(recruiter OR recruiting OR recruitment OR "talent acquisition" OR "talent sourcer")',
        '("HR executive" OR "HR generalist" OR "HR operations" OR "HR business partner" OR HRBP)',
        '("technical recruiter" OR "IT recruiter" OR "staffing recruiter" OR "recruitment coordinator")',
    ]
    variant_country = countries[0] if countries else "IN"
    variant_place = f'"{custom_location.strip()}"' if region == "custom" else f'"{place_hint}"' if place_hint != "global" else '(remote OR worldwide OR international)'
    for variant in variants:
        plan.append((f'{variant} (job OR jobs OR careers OR hiring) {variant_place}', variant_country))

    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for search_query, country in plan:
        clean_query = re.sub(r"\s+", " ", search_query).strip()[:590]
        key = (clean_query.lower(), country)
        if key not in seen:
            seen.add(key)
            unique.append((clean_query, country))
    return unique[:20]


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = False
        self.in_jsonld = False
        self.in_skip = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.jsonld_parts: list[str] = []
        self._current_jsonld: list[str] = []
        self.meta: dict[str, str] = {}
        self.canonical = ""

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self.title = True
        elif tag in {"script", "style", "noscript", "svg"}:
            self.in_skip += 1
            if tag == "script" and "ld+json" in attrs.get("type", "").lower():
                self.in_jsonld = True
                self._current_jsonld = []
        elif tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
            if key and attrs.get("content"):
                self.meta[key] = attrs["content"][:10000]
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower() and attrs.get("href"):
            self.canonical = attrs["href"][:2000]

    def handle_endtag(self, tag):
        if tag == "title":
            self.title = False
        elif tag == "script":
            if self.in_jsonld and self._current_jsonld:
                self.jsonld_parts.append("".join(self._current_jsonld)[:200000])
            self.in_jsonld = False
            self._current_jsonld = []
            self.in_skip = max(0, self.in_skip - 1)
        elif tag in {"style", "noscript", "svg"}:
            self.in_skip = max(0, self.in_skip - 1)

    def handle_data(self, data):
        if self.title and data.strip():
            self.title_parts.append(data.strip())
        if self.in_jsonld:
            self._current_jsonld.append(data)
        elif self.in_skip == 0 and data.strip():
            self.text_parts.append(data.strip())


def _walk_jsonld(data):
    if isinstance(data, list):
        for item in data:
            yield from _walk_jsonld(item)
    elif isinstance(data, dict):
        types = data.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if any(str(t).lower() == "jobposting" for t in types):
            yield data
        if isinstance(data.get("@graph"), (list, dict)):
            yield from _walk_jsonld(data["@graph"])
        for key in ("mainEntity", "itemListElement"):
            if key in data:
                yield from _walk_jsonld(data[key])


def _clean_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", value or "")
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = value.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    return " ".join(value.split())[:20000]


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _jsonld_locations(job: dict) -> str:
    values = job.get("jobLocation") or job.get("applicantLocationRequirements") or []
    if isinstance(values, dict):
        values = [values]
    found = []
    for value in values if isinstance(values, list) else []:
        if not isinstance(value, dict):
            continue
        address = value.get("address") or value
        if isinstance(address, str):
            found.append(address)
            continue
        if isinstance(address, dict):
            parts = [address.get(k) for k in ("addressLocality", "addressRegion", "addressCountry")]
            name = value.get("name")
            found.extend(str(x) for x in parts if x)
            if name:
                found.append(str(name))
    return ", ".join(dict.fromkeys(found))[:250] or "Location not specified"


def _salary_from_job(job: dict, text: str) -> str:
    base = job.get("baseSalary")
    if isinstance(base, dict):
        currency = base.get("currency") or ""
        value = base.get("value") or {}
        if isinstance(value, dict):
            low, high = value.get("minValue"), value.get("maxValue")
            unit = value.get("unitText") or ""
            if low is not None and high is not None:
                return f"{currency} {low}–{high} {unit}".strip()
            if low is not None or high is not None:
                return f"{currency} {low if low is not None else high} {unit}".strip()
        elif value:
            return f"{currency} {value}".strip()
    match = re.search(r"(?:₹|INR|Rs\.?|USD|\$|GBP|£|EUR|€)\s?[\d,]+(?:\s?[-–to]+\s?(?:₹|INR|Rs\.?|USD|\$|GBP|£|EUR|€)?\s?[\d,]+)?(?:\s?(?:LPA|per year|/year|monthly|/month|per hour))?", text, re.I)
    return " ".join(match.group(0).split()) if match else "Not disclosed"


def _experience_from_text(text: str, job: dict | None = None) -> str:
    if job:
        exp = job.get("experienceRequirements")
        if isinstance(exp, dict):
            exp = exp.get("description") or exp.get("name")
        if isinstance(exp, list):
            exp = ", ".join(str(x.get("description", x)) if isinstance(x, dict) else str(x) for x in exp)
        if exp:
            return str(exp)[:250]
    patterns = [
        r"\b(\d+\s*(?:-|to)\s*\d+\s*years?\s+(?:of\s+)?experience)\b",
        r"\b(\d+\+?\s+years?\s+(?:of\s+)?experience)\b",
        r"\b(\d+\s*[-–]\s*\d+\s*years?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return "Not disclosed"


def _skills_from_text(text: str, job: dict | None = None) -> list[str]:
    if job and job.get("skills"):
        skills = job["skills"]
        if isinstance(skills, str):
            values = re.split(r"[,;|\n]", skills)
        elif isinstance(skills, list):
            values = [str(x) for x in skills]
        else:
            values = []
        return list(dict.fromkeys(x.strip() for x in values if x.strip()))[:12]
    text_low = text.lower()
    return [skill for skill in ROLE_SKILLS if skill in text_low][:10]


def _company_from_result(title: str, url: str) -> str:
    # Use explicit publisher/title suffixes when possible; otherwise show the domain,
    # not a guessed employer name.
    for sep in (" | ", " — ", " – ", " - "):
        parts = [p.strip() for p in title.split(sep) if p.strip()]
        if len(parts) >= 2 and len(parts[-1]) < 100:
            candidate = re.sub(r"\b(jobs?|careers?|job openings?)\b", "", parts[-1], flags=re.I).strip(" -|–")
            if candidate:
                return candidate[:250]
    host = urlsplit(url).hostname or "Job listing site"
    host = host.lower().removeprefix("www.")
    return host[:250]


def _parse_page(html: str, source_url: str, snippet: str, result_title: str, country: str) -> dict:
    parser = _PageParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    visible = " ".join(parser.text_parts)
    full_text = _clean_html(visible)
    job_schema = None
    for raw_json in parser.jsonld_parts:
        try:
            parsed = json.loads(raw_json)
        except (ValueError, TypeError):
            continue
        job_schema = next(_walk_jsonld(parsed), None)
        if job_schema:
            break
    meta_title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or " ".join(parser.title_parts)
    meta_desc = parser.meta.get("description") or parser.meta.get("og:description") or parser.meta.get("twitter:description") or ""
    if job_schema:
        title = str(job_schema.get("title") or job_schema.get("name") or meta_title or result_title).strip()
        org = job_schema.get("hiringOrganization") or {}
        company = (str(org.get("name") or "") if isinstance(org, dict) else str(org or "")).strip()
        description = _clean_html(str(job_schema.get("description") or meta_desc or snippet))
        location = _jsonld_locations(job_schema)
        posted_at = _parse_dt(job_schema.get("datePosted"))
        evidence = "JobPosting structured data datePosted" if posted_at else "JobPosting structured data found; datePosted missing"
        verified = posted_at is not None
        employment = job_schema.get("employmentType") or ""
        if isinstance(employment, list):
            employment = ", ".join(str(x) for x in employment)
        return {
            "title": title[:250], "company": company[:250] or _company_from_result(result_title, source_url),
            "description": description[:20000], "location": location, "posted_at": posted_at,
            "verified": verified, "evidence": evidence, "employment_type": str(employment)[:100],
            "salary": _salary_from_job(job_schema, description), "experience": _experience_from_text(description, job_schema),
            "skills": _skills_from_text(description, job_schema), "canonical": parser.canonical,
        }
    # The search snippet is never considered proof of original publication time.
    # Keep the exact page text only for analysis and send the lead to the unverified bucket.
    description = " ".join(filter(None, [meta_desc, full_text[:10000], snippet]))[:20000]
    relative = re.search(r"\bposted\s+(\d+)\s+(minutes?|hours?|days?)\s+ago\b", full_text, re.I)
    posted_at = None
    verified = False
    evidence = "Original publication time not found on the fetched job page"
    if relative:
        value = int(relative.group(1))
        unit = relative.group(2).lower()
        hours = value / 60 if unit.startswith("minute") else value if unit.startswith("hour") else value * 24
        posted_at = datetime.now(timezone.utc) - timedelta(hours=hours)
        verified = True
        evidence = f"Original page explicitly states: {relative.group(0)} (relative time)"
    title = meta_title or result_title
    company = _company_from_result(title, source_url)
    # Try to capture a company suffix from a job-page title, without making it mandatory.
    return {
        "title": title[:250], "company": company, "description": description, "location": "Location not specified",
        "posted_at": posted_at, "verified": verified, "evidence": evidence,
        "employment_type": "", "salary": _salary_from_job({}, description),
        "experience": _experience_from_text(description), "skills": _skills_from_text(description),
        "canonical": parser.canonical,
    }


def _assert_public_http_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Only public HTTP(S) job URLs may be checked")
    if parts.username or parts.password:
        raise ValueError("Credential-bearing URLs are not allowed")
    if parts.port not in (None, 80, 443):
        raise ValueError("Non-standard web ports are not allowed")
    host = parts.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".test")):
        raise ValueError("Local hostnames are not allowed")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise ValueError("Private or non-public IP addresses are not allowed")
    except ValueError:
        if re.fullmatch(r"[0-9.]+", host):
            raise ValueError("Invalid or non-public IP address")
        try:
            addresses = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ValueError("Job hostname could not be resolved") from exc
        for item in addresses:
            address = ipaddress.ip_address(item[4][0])
            if not address.is_global:
                raise ValueError("Job hostname resolves to a non-public IP address")


async def _fetch_html_safely(url: str, timeout: httpx.Timeout) -> tuple[str, str]:
    """Fetch a public page with redirect checks and a bounded response body."""
    current = url
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AIJobHunter/0.5; public job listing verification)",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
    }) as client:
        for _ in range(5):
            await asyncio.to_thread(_assert_public_http_url, current)
            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    next_url = response.headers.get("location")
                    if not next_url:
                        return "", current
                    current = urljoin(current, next_url)
                    continue
                if response.status_code >= 400:
                    return "", current
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type and "xhtml" not in content_type:
                    return "", current
                chunks = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    chunks.append(chunk)
                    if total >= 1_000_000:
                        break
                raw = b"".join(chunks)[:1_000_000]
                encoding = "utf-8"
                match = re.search(r"charset=([\w-]+)", content_type)
                if match:
                    encoding = match.group(1)
                return raw.decode(encoding, errors="replace"), current
    return "", current


async def fetch_brave_web_research(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    region: str,
    custom_location: str,
    hours: int,
    max_pages_to_verify: int = 48,
) -> tuple[list[NormalizedPosting], dict]:
    """Run Brave Search, fetch promising original pages safely, and normalize job leads."""
    if not api_key.strip():
        raise ValueError("BRAVE_SEARCH_API_KEY is not configured")
    plan = build_search_plan(query, region, custom_location, hours)
    freshness = freshness_code(hours)
    raw_results: list[dict] = []
    errors: list[str] = []
    scope_stats: dict[str, dict[str, int]] = {}
    portal_result_counts: dict[str, int] = {}
    for planned_query, _country in plan:
        label = _query_scope_label(planned_query)
        scope_stats.setdefault(label, {"planned": 0, "succeeded": 0, "results_seen": 0})
        scope_stats[label]["planned"] += 1

    async def run_query(search_query: str, country: str):
        params = {"q": search_query, "country": country, "search_lang": "en", "count": 20}
        if freshness:
            params["freshness"] = freshness
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search", params=params,
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        web = data.get("web") or {}
        return search_query, country, web.get("results") or []

    results = await asyncio.gather(*(run_query(q, country) for q, country in plan), return_exceptions=True)
    successful_queries = 0
    for plan_item, result in zip(plan, results):
        query_label = _query_scope_label(plan_item[0])
        if isinstance(result, Exception):
            errors.append(f"{query_label} ({plan_item[1]}): {type(result).__name__}: {str(result)[:120]}")
            continue
        successful_queries += 1
        scope_stats[query_label]["succeeded"] += 1
        _, country, items = result
        scope_stats[query_label]["results_seen"] += len(items)
        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            if not url or not title or not any(word in f"{title} {description}".lower() for word in JOB_WORDS):
                continue
            parts = urlsplit(url)
            if parts.scheme not in {"http", "https"} or not parts.hostname:
                continue
            portal = portal_label_for_url(url)
            portal_result_counts[portal] = portal_result_counts.get(portal, 0) + 1
            raw_results.append({"url": url, "title": title, "description": description, "country": country,
                                "page_age": item.get("page_age"), "portal": portal, "query_scope": query_label})
    unique = {}
    for item in raw_results:
        key = canonicalize_job_url(item["url"])
        if key and key not in unique:
            unique[key] = item
    # Report distinct candidate URLs by the domain they point to, not duplicate
    # appearances of a page in multiple search queries.
    portal_result_counts = {}
    for item in unique.values():
        portal = item["portal"]
        portal_result_counts[portal] = portal_result_counts.get(portal, 0) + 1

    # Round-robin across source domains so the verification budget isn't consumed
    # entirely by whichever site happened to rank first in the search API results.
    domain_groups: dict[str, list[dict]] = {}
    for item in unique.values():
        domain_groups.setdefault(item["portal"], []).append(item)
    candidates: list[dict] = []
    while domain_groups and len(candidates) < max_pages_to_verify:
        for domain in list(domain_groups):
            if domain_groups[domain] and len(candidates) < max_pages_to_verify:
                candidates.append(domain_groups[domain].pop(0))
            if not domain_groups[domain]:
                del domain_groups[domain]

    semaphore = asyncio.Semaphore(5)
    timeout = httpx.Timeout(8.0, connect=3.0)

    async def verify(item):
        async with semaphore:
            page = ""
            final_url = item["url"]
            try:
                page, final_url = await _fetch_html_safely(item["url"], timeout)
            except Exception:
                # Public search-result metadata is still useful as an unverified lead.
                pass
            parsed = _parse_page(page, final_url or item["url"], item["description"], item["title"], item["country"]) if page else {
                "title": item["title"], "company": _company_from_result(item["title"], item["url"]),
                "description": item["description"][:20000], "location": "Location not specified", "posted_at": None,
                "verified": False, "evidence": "Search result only; original job page could not be verified",
                "employment_type": "", "salary": _salary_from_job({}, item["description"]),
                "experience": _experience_from_text(item["description"]), "skills": _skills_from_text(item["description"]), "canonical": "",
            }
            source_url = parsed.get("canonical") or item["url"]
            if source_url and source_url.startswith(("http://", "https://")):
                # Preserve the original job listing URL rather than a search-engine wrapper.
                pass
            employment = str(parsed.get("employment_type") or "")
            if employment:
                parsed["description"] = (parsed["description"] + f"\nEmployment type: {employment}")[:20000]
            return NormalizedPosting(
                title=parsed["title"] or item["title"], company=parsed["company"] or _company_from_result(item["title"], item["url"]),
                location=parsed["location"] or "Location not specified", work_mode="Unknown",
                source_url=item["url"], description=parsed["description"] or item["description"],
                posted_at=parsed["posted_at"], verified_posting_time=bool(parsed["verified"]),
                provider="brave_web_search",
                source_company=f"{item['portal']} · indexed web search ({item['country']})",
                posting_time_evidence=parsed["evidence"], salary_range=parsed.get("salary") or "Not disclosed",
                experience_required=parsed.get("experience") or "Not disclosed", required_skills=parsed.get("skills") or [],
                search_region_hint=item["country"],
            )

    postings = await asyncio.gather(*(verify(item) for item in candidates))
    verified_count = sum(1 for posting in postings if posting.verified_posting_time)
    portal_breakdown = [
        {"portal": portal, "results_seen": count}
        for portal, count in sorted(portal_result_counts.items(), key=lambda item: (-item[1], item[0].lower()))
    ]
    query_breakdown = [
        {"scope": label, **stats}
        for label, stats in sorted(scope_stats.items(), key=lambda item: item[0].lower())
    ]
    diagnostics = {
        "queries_planned": len(plan), "queries_succeeded": successful_queries,
        "search_results_seen": len(raw_results), "unique_candidates_checked": len(postings),
        "original_pages_verified": verified_count, "errors": errors[:8],
        "portal_breakdown": portal_breakdown, "query_breakdown": query_breakdown,
    }
    if successful_queries == 0 and errors:
        raise RuntimeError("All Brave Search requests failed: " + "; ".join(errors[:3]))
    return list(postings), diagnostics
