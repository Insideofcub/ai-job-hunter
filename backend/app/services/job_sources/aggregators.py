from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote
import re
import httpx
from .base import NormalizedPosting, infer_work_mode
from .greenhouse import html_to_text
from ...config import settings


COUNTRY_CODES = {"in", "gb", "us", "ca", "au", "de", "fr", "nl", "sg", "pl", "za", "nz", "at", "be", "br", "ch", "es", "it", "mx"}


def _date_from_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def _date_from_epoch(value) -> datetime | None:
    if value is None:
        return None
    try:
        number = float(value)
        # Public feeds vary between seconds and milliseconds.
        if number > 100_000_000_000:
            number /= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None


async def fetch_arbeitnow(client: httpx.AsyncClient, _board_id: str, _company_name: str) -> list[NormalizedPosting]:
    """Fetch up to three pages from Arbeitnow's public job-board API."""
    results: list[NormalizedPosting] = []
    # Keep the endpoint fixed; no user-provided URL is accepted here.
    for page in range(1, 4):
        response = await client.get("https://www.arbeitnow.com/api/job-board-api", params={"page": page})
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(jobs, list) or not jobs:
            break
        for item in jobs:
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url.startswith("https://www.arbeitnow.com/"):
                continue
            description = html_to_text(str(item.get("description") or ""))
            location = str(item.get("location") or "Not specified")
            created = _date_from_epoch(item.get("created_at")) or _date_from_iso(item.get("created_at"))
            company = str(item.get("company_name") or "Unknown company")
            remote = bool(item.get("remote"))
            results.append(NormalizedPosting(
                title=title, company=company, location=location + (" · Remote" if remote and "remote" not in location.lower() else ""),
                work_mode=infer_work_mode(location, description, "Remote" if remote else None),
                source_url=url, description=description[:20000], posted_at=created,
                verified_posting_time=created is not None, provider="arbeitnow", source_company="Arbeitnow public feed",
            ))
        links = payload.get("links", {}) if isinstance(payload, dict) else {}
        if not links.get("next"):
            break
    return results


async def fetch_remoteok(client: httpx.AsyncClient, _board_id: str, _company_name: str) -> list[NormalizedPosting]:
    response = await client.get("https://remoteok.com/api", headers={"Accept": "application/json", "User-Agent": "AI-Job-Hunter open-source job discovery; links back to Remote OK postings"})
    response.raise_for_status()
    payload = response.json()
    jobs = payload[1:] if isinstance(payload, list) and payload and isinstance(payload[0], dict) else payload
    results: list[NormalizedPosting] = []
    if not isinstance(jobs, list):
        return results
    for item in jobs:
        if not isinstance(item, dict):
            continue
        title = str(item.get("position") or item.get("title") or "").strip()
        url = str(item.get("url") or item.get("apply_url") or "").strip()
        if not title or not url.startswith("https://remoteok.com/"):
            continue
        company = str(item.get("company") or "Unknown company")
        description = html_to_text(str(item.get("description") or ""))
        created = _date_from_iso(item.get("date")) or _date_from_epoch(item.get("epoch"))
        tags = item.get("tags") or []
        if isinstance(tags, list):
            description = (description + "\nTags: " + ", ".join(str(tag) for tag in tags)).strip()
        location = "Remote"
        results.append(NormalizedPosting(
            title=title, company=company, location=location, work_mode="Remote", source_url=url,
            description=description[:20000], posted_at=created, verified_posting_time=created is not None,
            provider="remoteok", source_company="Remote OK public feed",
        ))
    return results


async def fetch_adzuna(client: httpx.AsyncClient, country_code: str, query: str, company_name: str) -> list[NormalizedPosting]:
    country = country_code.lower().strip()
    if country not in COUNTRY_CODES:
        raise ValueError("Unsupported Adzuna country code. Use a configured country such as in, us, or gb.")
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        raise ValueError("Adzuna requires ADZUNA_APP_ID and ADZUNA_APP_KEY in backend/.env. Register at developer.adzuna.com.")
    pieces = [piece.strip() for piece in re.split(r"[,;|\n]+", query or "") if piece.strip()]
    search_pieces = []
    for piece in pieces:
        piece = re.split(r"\s+[—–-]\s+", piece, maxsplit=1)[0]
        piece = re.sub(r"\b(?:in india|india and global roles|global roles|global|worldwide|across india|remote roles|all platforms)\b", "", piece, flags=re.I).strip()
        if piece and len(piece) <= 80:
            search_pieces.append(piece)
    # Adzuna's `what_or` broadens a natural multi-role instruction without requiring every title.
    search_terms = " ".join(search_pieces[:5])
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": 50,
        "what": search_terms or "recruiter talent acquisition human resources",
        "what_or": " ".join(search_pieces[:5]) if len(search_pieces) > 1 else "",
        "sort_by": "date",
        "content-type": "application/json",
    }
    url = f"https://api.adzuna.com/v1/api/jobs/{quote(country, safe='')}/search/1"
    response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("results", []) if isinstance(payload, dict) else []
    results: list[NormalizedPosting] = []
    for item in items if isinstance(items, list) else []:
        title = str(item.get("title") or "").strip()
        url = str(item.get("redirect_url") or "").strip()
        if not title or not url.startswith("https://"):
            continue
        company_data = item.get("company") or {}
        location_data = item.get("location") or {}
        company = str(company_data.get("display_name") or "Unknown company")
        location = str(location_data.get("display_name") or country.upper())
        description = str(item.get("description") or "")
        created = _date_from_iso(item.get("created"))
        results.append(NormalizedPosting(
            title=title, company=company, location=location,
            work_mode=infer_work_mode(location, description), source_url=url,
            description=description[:20000], posted_at=created, verified_posting_time=created is not None,
            provider="adzuna", source_company=company_name or f"Adzuna {country.upper()}",
        ))
    return results


async def fetch_jobicy(client: httpx.AsyncClient, _board_id: str, _company_name: str) -> list[NormalizedPosting]:
    """Fetch public Jobicy remote vacancies for global and APAC coverage.

    Jobicy's public API exposes listings published in its latest seven-day window.
    We keep Jobicy's own listing URL and do not attempt to submit through this feed.
    """
    results: list[NormalizedPosting] = []
    seen_urls: set[str] = set()
    # Two broad geographic passes improve coverage for globally-remote and APAC roles.
    # The endpoint is fixed and the response URL is validated before being retained.
    for geo in ("anywhere", "apac"):
        response = await client.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": 200, "geo": geo},
        )
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
        if not isinstance(jobs, list):
            continue
        for item in jobs:
            if not isinstance(item, dict):
                continue
            title = str(item.get("jobTitle") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url.startswith("https://jobicy.com/") or url in seen_urls:
                continue
            seen_urls.add(url)
            company = str(item.get("companyName") or "Unknown company").strip()
            location = str(item.get("jobGeo") or geo.upper()).strip()
            description = html_to_text(str(item.get("jobDescription") or item.get("jobExcerpt") or ""))
            industries = item.get("jobIndustry") or []
            job_types = item.get("jobType") or []
            if isinstance(industries, list) and industries:
                description += "\nIndustries: " + ", ".join(str(value) for value in industries)
            if isinstance(job_types, list) and job_types:
                description += "\nJob types: " + ", ".join(str(value) for value in job_types)
            salary_bits = []
            for field, label in (("salaryMin", "min"), ("salaryMax", "max")):
                if item.get(field) is not None:
                    salary_bits.append(f"{label} {item[field]}")
            if salary_bits:
                description += "\nSalary: " + " – ".join(salary_bits) + " " + str(item.get("salaryCurrency") or "") + " " + str(item.get("salaryPeriod") or "")
            published = _date_from_iso(item.get("pubDate"))
            results.append(NormalizedPosting(
                title=title,
                company=company or "Unknown company",
                location=location or "Remote",
                work_mode=infer_work_mode(location, description, "Remote"),
                source_url=url,
                description=description[:20000],
                posted_at=published,
                verified_posting_time=published is not None,
                provider="jobicy",
                source_company="Jobicy public remote jobs API",
            ))
    return results


async def fetch_himalayas(client: httpx.AsyncClient, _board_id: str, query: str, company_name: str = "Himalayas Remote Jobs") -> list[NormalizedPosting]:
    """Search Himalayas' public remote-jobs API and preserve its required attribution.

    Himalayas requests that clients use applicationLink for the Apply action and visibly
    credit Himalayas as the source. This connector therefore stores that link and marks
    source_company accordingly. The API updates daily and is a remote-only source.
    """
    pieces = [piece.strip() for piece in re.split(r"[,;|\n]+", query or "") if piece.strip()]
    # Avoid sending the whole natural-language instruction as a single literal query.
    queries = []
    if pieces:
        for piece in pieces[:3]:
            cleaned = re.sub(r"\b(?:jobs?|vacancies|openings|in india|global roles|worldwide|across india)\b", "", piece, flags=re.I).strip()
            if cleaned and cleaned.lower() not in {x.lower() for x in queries}:
                queries.append(cleaned[:80])
    if not queries:
        queries = ["recruiter", "talent acquisition"]

    results: list[NormalizedPosting] = []
    seen: set[str] = set()
    # Two pages for each of up to three distinct phrases balances recall against the
    # public unauthenticated API's shared rate limits.
    semaphore = __import__("asyncio").Semaphore(3)

    async def fetch_page(search_term: str, page: int):
        async with semaphore:
            response = await client.get(
                "https://himalayas.app/jobs/api/search",
                params={"q": search_term, "sort": "recent", "page": page},
                headers={"Accept": "application/json", "User-Agent": "AI-Job-Hunter/0.5 (+https://github.com/)"},
            )
            response.raise_for_status()
            return search_term, page, response.json()

    jobs_pages = await __import__("asyncio").gather(
        *(fetch_page(term, page) for term in queries for page in (1, 2)),
        return_exceptions=True,
    )
    failures = []
    for page_result in jobs_pages:
        if isinstance(page_result, Exception):
            failures.append(type(page_result).__name__)
            continue
        _term, _page, payload = page_result
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
        for item in jobs if isinstance(jobs, list) else []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("applicationLink") or "").strip()
            company = str(item.get("companyName") or "Unknown company").strip()
            if not title or not url.startswith("https://") or url in seen:
                continue
            seen.add(url)
            description = html_to_text(str(item.get("description") or item.get("excerpt") or ""))
            employment_type = str(item.get("employmentType") or "").strip()
            categories = item.get("categories") or []
            parent_categories = item.get("parentCategories") or []
            if employment_type:
                description += "\nEmployment type: " + employment_type
            if isinstance(categories, list) and categories:
                description += "\nCategories: " + ", ".join(str(value) for value in categories)
            if isinstance(parent_categories, list) and parent_categories:
                description += "\nParent categories: " + ", ".join(str(value) for value in parent_categories)
            restrictions = item.get("locationRestrictions") or []
            location = ", ".join(str(value) for value in restrictions) if restrictions else "Worldwide eligible (remote)"
            salary_min, salary_max = item.get("minSalary"), item.get("maxSalary")
            salary = "Not disclosed"
            if salary_min is not None or salary_max is not None:
                range_text = str(salary_min if salary_min is not None else salary_max)
                if salary_min is not None and salary_max is not None:
                    range_text = f"{salary_min}–{salary_max}"
                salary = f"{item.get('currency') or ''} {range_text} {item.get('salaryPeriod') or 'annual'}".strip()
            published = _date_from_iso(item.get("pubDate"))
            exp = str(item.get("seniority") or "Not disclosed")
            results.append(NormalizedPosting(
                title=title[:250], company=company or "Unknown company", location=location,
                work_mode="Remote", source_url=url, description=description[:20000],
                posted_at=published, verified_posting_time=published is not None,
                provider="himalayas", source_company="Himalayas (source attribution required)",
                posting_time_evidence=("Himalayas API pubDate field" if published else "Himalayas API did not provide a publication date"),
                salary_range=salary[:180], experience_required=exp[:250],
                required_skills=[str(value) for value in (categories if isinstance(categories, list) else [])[:12]],
            ))
    if not results and failures:
        raise RuntimeError("Himalayas requests failed: " + ", ".join(failures[:4]))
    return results
