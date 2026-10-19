"""Optional JobSpy connector for multi-portal job discovery.

This connector is deliberately opt-in. It does not configure proxies, browser cookies,
accounts, or any blocking circumvention. Users must check each portal's terms and use
only supported/permitted access. All timestamps retain their observed precision; a
calendar date without a reliable time-of-day is not treated as a verified fresh post.
"""
from __future__ import annotations

import asyncio
import importlib.util
import logging
import math
import re
from datetime import date, datetime, time, timezone
from typing import Any

from .base import NormalizedPosting, infer_work_mode
from ..discovery import query_phrases

logger = logging.getLogger("ai_job_hunter.jobspy")

SUPPORTED_SITES = {
    "linkedin", "indeed", "glassdoor", "zip_recruiter", "bayt", "bdjobs", "hellowork", "naukri"
}

REGION_LOCATIONS = {
    "global": ["India", "United States", "United Kingdom", "Remote"],
    "india": ["India", "Remote"],
    "asia": ["India", "Singapore", "Remote"],
    "europe": ["United Kingdom", "Germany", "France", "Remote"],
    "americas": ["United States", "Canada", "Remote"],
    "middle_east": ["United Arab Emirates", "Saudi Arabia", "Remote"],
    "africa": ["South Africa", "Nigeria", "Remote"],
    "oceania": ["Australia", "New Zealand", "Remote"],
}

COUNTRY_INDEED = {
    "india": "India",
    "united states": "USA",
    "usa": "USA",
    "canada": "Canada",
    "united kingdom": "UK",
    "uk": "UK",
    "germany": "Germany",
    "france": "France",
    "singapore": "Singapore",
    "united arab emirates": "United Arab Emirates",
    "saudi arabia": "Saudi Arabia",
    "south africa": "South Africa",
    "nigeria": "Nigeria",
    "australia": "Australia",
    "new zealand": "New Zealand",
}


def jobspy_package_available() -> bool:
    """Check whether the optional library is installed without importing it."""
    try:
        return importlib.util.find_spec("jobspy") is not None
    except (ImportError, ValueError):
        return False


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    # Avoid pulling pandas into the base installation simply for missing-value checks.
    try:
        if isinstance(value, float) and math.isnan(value):
            return default
    except (TypeError, ValueError):
        pass
    try:
        result = str(value).strip()
    except Exception:
        return default
    if result.lower() in {"nan", "nat", "none", "<na>", "null"}:
        return default
    return result or default


def _parse_posted_value(value: Any) -> tuple[datetime | None, bool, str]:
    """Return UTC timestamp, precision-verified flag, and original evidence text.

    Day-only publication dates are intentionally left unverified. JobSpy's upstream
    hours_old filter is useful discovery assistance but is not, by itself, evidence of
    the original publication time on the employer's page.
    """
    raw = _text(value)
    if not raw:
        return None, False, "JobSpy did not return a publication date."

    # A pure date or date-like midnight value is day precision, not an exact timestamp.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None, False, f"JobSpy returned date-only value '{raw}'; time-of-day is unverified."

    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
        # Pandas often represents date-only values as midnight timestamps. Keep those
        # unverified unless the value clearly carries a time component beyond midnight.
        if parsed.time().replace(tzinfo=None) == time(0, 0) and not re.search(r"(?:Z|[+-]\d{2}:?\d{2})$", raw):
            return None, False, f"JobSpy returned '{raw}' at midnight with ambiguous precision; time-of-day is unverified."
    elif isinstance(value, date):
        return None, False, f"JobSpy returned date-only value '{raw}'; time-of-day is unverified."
    else:
        try:
            iso = raw.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(iso)
        except (TypeError, ValueError, OverflowError):
            # Date strings such as "2 days ago" are not treated as exact timestamps.
            return None, False, f"Unparsed JobSpy publication value '{raw}'; exact timestamp is unverified."
        explicit_timezone = raw.endswith("Z") or bool(re.search(r"[+-]\d{2}:?\d{2}$", raw))
        if parsed.time().replace(tzinfo=None) == time(0, 0) and not explicit_timezone:
            return None, False, f"JobSpy returned '{raw}' at midnight without timezone evidence; time precision is unverified."

    if parsed is None:
        return None, False, f"Unparsed JobSpy publication value '{raw}'."
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc), True, f"JobSpy date_posted included time precision: '{raw}'."


def _float_value(value: Any) -> float | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        result = float(raw)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _format_salary(row: dict[str, Any]) -> str:
    low = _float_value(row.get("min_amount"))
    high = _float_value(row.get("max_amount"))
    if low is None and high is None:
        return "Not disclosed"
    currency = _text(row.get("currency"), "Currency not stated")
    interval = _text(row.get("interval"))
    unit = {
        "yearly": "/year", "monthly": "/month", "weekly": "/week",
        "daily": "/day", "hourly": "/hour",
    }.get(interval.lower(), f"/{interval}" if interval else "")
    def fmt(value: float) -> str:
        return f"{value:,.0f}"
    if low is not None and high is not None:
        amount = f"{fmt(low)}–{fmt(high)}"
    else:
        amount = fmt(low if low is not None else high)  # type: ignore[arg-type]
    return f"{currency} {amount}{unit}".strip()


def _normalize_skills(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        raw = _text(value)
        values = re.split(r"[,;|]", raw) if raw else []
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))[:30]


def _search_locations(region: str, custom_location: str) -> list[str]:
    region = (region or "global").strip().lower().replace("-", "_").replace(" ", "_")
    if region == "custom":
        return [custom_location.strip()] if custom_location.strip() else []
    return list(REGION_LOCATIONS.get(region, REGION_LOCATIONS["global"]))


def _country_for_location(location: str, region: str) -> str:
    loc = (location or "").strip().lower()
    if loc == "remote":
        if region in {"india", "asia"}:
            return "India"
        if region == "europe":
            return "UK"
        if region == "middle_east":
            return "United Arab Emirates"
        if region == "africa":
            return "South Africa"
        if region == "oceania":
            return "Australia"
        if region == "americas":
            return "USA"
        return "USA"
    known_india_locations = {"delhi", "new delhi", "gurugram", "gurgaon", "noida", "mumbai", "bengaluru", "bangalore", "hyderabad", "pune", "sagar", "jabalpur", "indore", "chennai", "kolkata", "ahmedabad"}
    known_us_locations = {"new york", "san francisco", "seattle", "austin", "boston", "chicago", "los angeles"}
    if region == "custom" and any(name in loc for name in known_india_locations):
        return "India"
    if region == "custom" and any(name in loc for name in known_us_locations):
        return "USA"
    return COUNTRY_INDEED.get(loc, "India" if region == "india" else "USA")


def _sites_for_location(configured_sites: list[str], location: str, country: str) -> list[str]:
    """Limit region-specific boards to the markets their docs say they cover."""
    sites = [site for site in configured_sites if site in SUPPORTED_SITES]
    loc = location.lower()
    country_low = country.lower()
    if "naukri" in sites and country_low != "india":
        sites.remove("naukri")
    if "zip_recruiter" in sites and country_low not in {"usa", "canada"}:
        sites.remove("zip_recruiter")
    if "bdjobs" in sites and "bangladesh" not in loc:
        sites.remove("bdjobs")
    if "hellowork" in sites and country_low != "france" and "france" not in loc:
        sites.remove("hellowork")
    # JobSpy's README says Google Jobs is currently unavailable; it is intentionally not
    # part of SUPPORTED_SITES and will never be requested by this connector.
    return list(dict.fromkeys(sites))


def _make_search_plan(query: str, region: str, custom_location: str, max_searches: int) -> list[tuple[str, str]]:
    phrases = query_phrases(query)
    if not phrases and query.strip():
        phrases = [query.strip()]
    if not phrases:
        phrases = ["recruiter", "talent acquisition"]
    phrases = list(dict.fromkeys(phrases))[:8]
    locations = _search_locations(region, custom_location)
    if not locations:
        return []
    plan: list[tuple[str, str]] = []
    seen = set()
    # Diagonal/round-robin the role-location grid so a bounded run covers multiple
    # locations before spending every call on variants for one country.
    for step in range(max(len(phrases), len(locations))):
        for loc_idx, location in enumerate(locations):
            role = phrases[(step + loc_idx) % len(phrases)]
            pair = (role, location)
            if pair not in seen:
                seen.add(pair)
                plan.append(pair)
                if len(plan) >= max(1, max_searches):
                    return plan
    return plan


def _scrape_sync(
    query: str,
    region: str,
    custom_location: str,
    hours: int,
    configured_sites: list[str],
    max_searches: int,
    results_wanted: int,
) -> tuple[list[NormalizedPosting], dict[str, Any]]:
    try:
        from jobspy import scrape_jobs
    except ImportError as exc:
        raise RuntimeError("JobSpy is not installed. Run `pip install -r backend/requirements-jobspy.txt`, then restart the backend.") from exc

    plan = _make_search_plan(query, region, custom_location, max_searches)
    all_postings: list[NormalizedPosting] = []
    calls = 0
    successful_calls = 0
    sites_attempted: set[str] = set()
    errors: list[str] = []
    warnings: list[str] = []
    for role, location in plan:
        country = _country_for_location(location, region)
        sites = _sites_for_location(configured_sites, location, country)
        if not sites:
            warnings.append(f"No configured JobSpy sites apply to location '{location}'.")
            continue
        calls += 1
        sites_attempted.update(sites)
        try:
            frame = scrape_jobs(
                site_name=sites,
                search_term=role,
                location=location,
                results_wanted=max(1, min(int(results_wanted), 30)),
                hours_old=max(1, min(int(hours), 720)),
                country_indeed=country,
                fetch_description=False,
                verbose=0,
            )
        except Exception as exc:
            errors.append(f"{', '.join(sites)} for '{role}' in '{location}': {type(exc).__name__}: {str(exc)[:180]}")
            logger.warning("JobSpy query failed for role=%r location=%r sites=%s: %s", role, location, sites, exc)
            continue

        successful_calls += 1
        attrs = getattr(frame, "attrs", {}) or {}
        board_errors = attrs.get("errors", {}) if isinstance(attrs, dict) else {}
        board_warnings = attrs.get("warnings", {}) if isinstance(attrs, dict) else {}
        if isinstance(board_errors, dict):
            errors.extend(f"{site}: {message}" for site, message in board_errors.items())
        if isinstance(board_warnings, dict):
            warnings.extend(f"{site}: {message}" for site, message in board_warnings.items())

        if frame is None or bool(getattr(frame, "empty", True)):
            continue
        for _, series in frame.iterrows():
            row = series.to_dict() if hasattr(series, "to_dict") else dict(series)
            title = _text(row.get("title"))
            company = _text(row.get("company"), "Unknown company")
            source_url = _text(row.get("job_url")) or _text(row.get("job_url_direct"))
            if not title or not source_url.startswith("https://"):
                continue

            description = _text(row.get("description"))
            job_type = _text(row.get("job_type"))
            work_from_home = _text(row.get("work_from_home_type"))
            is_remote = str(row.get("is_remote", "")).strip().lower() in {"true", "1", "yes"}
            location_text = _text(row.get("location"), location)
            if is_remote and "remote" not in location_text.lower():
                location_text = f"{location_text} · Remote" if location_text else "Remote"
            extra = []
            if job_type:
                type_label = {
                    "fulltime": "full time", "parttime": "part time", "contract": "contract",
                    "temporary": "temporary", "internship": "internship", "perdiem": "contract",
                }.get(job_type.lower(), job_type)
                extra.append(f"Employment type: {type_label}.")
            if work_from_home:
                extra.append(f"Work-from-home type: {work_from_home}.")
            combined_description = (description + "\n\n" + " ".join(extra)).strip()[:20000]
            posted_at, verified, date_evidence = _parse_posted_value(row.get("date_posted"))
            site = _text(row.get("site"), "jobspy").lower()
            evidence = (
                f"{date_evidence} JobSpy query requested hours_old={hours}; this query filter is not a substitute "
                "for original-page verification when the date is day-level or absent."
            )
            experience = _text(row.get("experience_range"), "Not disclosed")
            skills = _normalize_skills(row.get("skills"))
            all_postings.append(NormalizedPosting(
                title=title[:250], company=company[:250], location=location_text[:250],
                work_mode=infer_work_mode(location_text, combined_description, "Remote" if is_remote else work_from_home or None),
                source_url=source_url, description=combined_description,
                posted_at=posted_at, verified_posting_time=verified,
                provider="jobspy", source_company=f"JobSpy · {site.title()}",
                posting_time_evidence=evidence[:1000], salary_range=_format_salary(row),
                experience_required=experience[:250], required_skills=skills,
            ))

    # Stable de-duplication by URL; the main discovery pipeline will run its common
    # cross-source canonical URL and fingerprint dedupe as well.
    by_url: dict[str, NormalizedPosting] = {}
    for posting in all_postings:
        key = posting.source_url.split("#", 1)[0].rstrip("/")
        prior = by_url.get(key)
        if prior is None or len(posting.description) > len(prior.description):
            by_url[key] = posting
    diagnostics = {
        "searches_planned": len(plan),
        "searches_attempted": calls,
        "searches_succeeded": successful_calls,
        "sites_attempted": sorted(sites_attempted),
        "errors": errors[:20],
        "warnings": warnings[:20],
        "timestamp_precision_note": "Only JobSpy date_posted values with time-of-day precision are marked verified; date-only values remain unverified.",
    }
    return list(by_url.values()), diagnostics


async def fetch_jobspy_postings(
    query: str,
    region: str,
    custom_location: str,
    hours: int,
    sites: list[str],
    max_searches: int = 6,
    results_wanted: int = 12,
) -> tuple[list[NormalizedPosting], dict[str, Any]]:
    """Run the synchronous JobSpy scraping pipeline on a worker thread.

    JobSpy itself gathers multiple boards for each search. We intentionally keep the
    outer role/location plan sequential and bounded to avoid request bursts.
    """
    return await asyncio.to_thread(
        _scrape_sync, query, region, custom_location, hours, sites, max_searches, results_wanted
    )
