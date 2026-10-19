from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import re
import unicodedata

from .job_sources.base import NormalizedPosting

_TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source", "sourceid"}


def canonicalize_job_url(url: str) -> str:
    """Normalize cosmetic URL differences while preserving meaningful query parameters."""
    parts = urlsplit((url or "").strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    netloc = host
    if parts.port and not ((scheme == "https" and parts.port == 443) or (scheme == "http" and parts.port == 80)):
        netloc = f"{host}:{parts.port}"
    path = re.sub(r"/{2,}", "/", parts.path or "/").rstrip("/") or "/"
    kept = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        low = key.lower()
        if low in _TRACKING_KEYS or low.startswith("utm_") or low.startswith("ref_"):
            continue
        kept.append((key, value))
    kept.sort()
    return urlunsplit((scheme, netloc, path, urlencode(kept, doseq=True), ""))


def _normal_text(value: str | None) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", asciiish.lower()).split())


def fingerprint(posting: NormalizedPosting) -> tuple[str, str, str]:
    return (_normal_text(posting.title), _normal_text(posting.company), _normal_text(posting.location))


def query_phrases(query: str) -> list[str]:
    """Extract searchable role phrases from a title list or a short user instruction.

    The Find Jobs field is primarily for titles/keywords, but people sometimes paste a
    longer instruction. Keep the first sentence and strip common instruction wrappers
    so phrases like "and HR Executive jobs across India" become "hr executive" rather
    than a long literal phrase that can never match a job description.
    """
    text = (query or "").strip()
    if not text:
        return []
    # Subsequent sentences usually contain instructions, not role titles.
    text = re.split(r"[.!?]\s+", text, maxsplit=1)[0]
    text = re.sub(r"^(?:please\s+)?(?:search|find|look for|look up|discover)\s+(?:for\s+)?", "", text, flags=re.IGNORECASE)
    raw_phrases = re.split(r"[,;|\n]+", text)
    phrases = []
    for piece in raw_phrases:
        piece = piece.strip()
        piece = re.sub(r"^(?:and|or)\s+", "", piece, flags=re.IGNORECASE)
        piece = re.sub(r"\s+(?:jobs?|vacancies|openings|roles)\b.*$", "", piece, flags=re.IGNORECASE)
        piece = re.sub(r"\s+(?:across|in)\s+(?:india|the world|worldwide|global markets?|international markets?)\b.*$", "", piece, flags=re.IGNORECASE)
        normalized = _normal_text(piece)
        if normalized:
            phrases.append(normalized)
    return phrases


# Common title equivalents used for recruitment/HR searches. Keep this dictionary
# intentionally title-focused so an unrelated role is not accepted just because its
# description mentions hiring once.
_RECRUITMENT_TITLE_TERMS = (
    "recruiter", "recruiting", "recruitment", "talent acquisition", "talent sourcer",
    "talent sourcing", "talent partner", "people talent partner", "staffing", "headhunter",
    "head hunter", "executive search", "recruitment coordinator", "recruiting coordinator",
    "sourcing specialist", "resourcing", "campus recruiter", "campus recruitment",
    "technical recruiter", "it recruiter", "us it recruiter", "recruitment consultant",
    "recruitment specialist", "talent acquisition partner", "talent acquisition specialist",
    "talent acquisition executive", "recruitment operations", "talent operations",
)
_HR_TITLE_TERMS = (
    "human resources", "hr executive", "hr generalist", "hrbp", "hr business partner",
    "hr operations", "hr manager", "hr specialist", "hr coordinator", "hr analyst",
    "people operations", "people ops", "people and culture", "people & culture", "people partner",
    "employee relations", "human resource business partner", "human resources business partner",
    "hr shared services", "hr services", "hr administrator", "hr advisor", "hr consultant",
    "learning and development", "talent management", "people experience",
)


def query_match_reason(posting: NormalizedPosting, query: str = "", phrases: list[str] | None = None) -> tuple[bool, str]:
    """Return relevance and a human-readable explanation for a role query.

    Uses direct title matches first, then related title families for recruitment/HR.
    For non-HR searches it retains the generic phrase match behaviour.
    """
    phrases = phrases if phrases is not None else query_phrases(query)
    title = _normal_text(posting.title)
    description = _normal_text(posting.description)
    haystack = _normal_text(" ".join((posting.title, posting.company, posting.location, posting.description)))

    title_phrase = next((phrase for phrase in phrases if phrase and phrase in title), None)
    if title_phrase:
        return True, f"Direct title match: '{title_phrase}'."

    # Use any full phrase in the description only if the title itself is plausibly role-related.
    # This keeps descriptions useful for generic titles such as Assistant Manager - TA without
    # matching an unrelated job just because it mentions recruiting in passing.
    query_text = _normal_text(" ".join(phrases) or query)
    recruiting_intent = any(token in query_text for token in (
        "recruit", "talent acquisition", "talent sourc", "staffing", "headhunt", "executive search", "resourcing"
    ))
    hr_intent = any(token in query_text for token in (
        " hr ", "human resources", "human resource", "people operations", "people ops", "hrbp",
        "hr executive", "hr generalist", "employee relations", "people partner", "people culture", "talent management"
    ))
    title_is_recruitment = any(_normal_text(term) in title for term in _RECRUITMENT_TITLE_TERMS)
    title_is_hr = any(_normal_text(term) in title for term in _HR_TITLE_TERMS)

    if recruiting_intent and title_is_recruitment:
        return True, f"Related recruitment title variant: '{posting.title}'."
    if hr_intent and title_is_hr:
        return True, f"Related HR title variant: '{posting.title}'."

    if recruiting_intent or hr_intent:
        # Rescue useful mixed titles (e.g. Assistant Manager — Talent Acquisition) where the
        # role family appears in the body but the title uses a generic seniority label.
        title_is_generic_role = any(token in title.split() for token in (
            "manager", "assistant", "associate", "executive", "specialist", "coordinator", "analyst", "partner", "officer"
        ))
        domain_terms = list(_RECRUITMENT_TITLE_TERMS if recruiting_intent else ()) + list(_HR_TITLE_TERMS if hr_intent else ())
        signals = [term for term in domain_terms if _normal_text(term) in description]
        if title_is_generic_role and len(set(signals)) >= 2:
            return True, "Generic job title but description contains multiple relevant recruitment/HR signals: " + ", ".join(signals[:4]) + "."

        # Alias support for short query forms such as TA, HRBP, Sourcer and People Partner.
        title_terms = set(title.split())
        alias_hit = (
            (recruiting_intent and bool(title_terms & {"recruiter", "recruiting", "recruitment", "sourcer", "staffing", "headhunter", "resourcing"}))
            or (hr_intent and bool(title_terms & {"hr", "hrbp", "human", "people"}))
        )
        if alias_hit:
            return True, f"Role title uses a recognized recruitment/HR alias: '{posting.title}'."
        return False, "Title did not match a selected role or its recognized recruitment/HR variants."

    # Generic roles: match a phrase in the title, then in its full text.
    body_phrase = next((phrase for phrase in phrases if phrase and phrase in haystack), None)
    if body_phrase:
        return True, f"Selected keyword found in listing text: '{body_phrase}'."
    if not phrases:
        return True, "No role keywords were provided, so the listing was not filtered by role text."
    return False, "None of the selected role phrases were found in the title or listing text."


def matches_query(posting: NormalizedPosting, phrases: list[str]) -> bool:
    """Compatibility wrapper returning true when a listing matches the role query."""
    if not phrases:
        return True
    return query_match_reason(posting, " ".join(phrases), phrases)[0]


def _posting_quality(posting: NormalizedPosting) -> tuple[int, int, int, int]:
    return (
        int(bool(posting.verified_posting_time and posting.posted_at)),
        int(bool(posting.location and posting.location.lower() not in {"unknown", "location not specified", "not specified"})),
        int(bool(posting.salary_range and posting.salary_range != "Not disclosed")),
        min(len(posting.description or ""), 10000),
    )


def deduplicate_postings(postings: list[NormalizedPosting]) -> tuple[list[NormalizedPosting], list[tuple[NormalizedPosting, NormalizedPosting]]]:
    """Deduplicate by canonical URL and then title/company/location fingerprint.

    Keeps the richer record (verified publisher timestamp, usable location/salary,
    longer description) and returns duplicate/kept pairs for exclusion reporting.
    """
    by_identity: OrderedDict[tuple[str, ...], NormalizedPosting] = OrderedDict()
    duplicates: list[tuple[NormalizedPosting, NormalizedPosting]] = []
    for posting in postings:
        canonical = canonicalize_job_url(posting.source_url)
        if canonical:
            identity = ("url", canonical)
        else:
            identity = ("fingerprint",) + fingerprint(posting)
        current = by_identity.get(identity)
        if current is None:
            by_identity[identity] = posting
            continue
        if _posting_quality(posting) > _posting_quality(current):
            by_identity[identity] = posting
            duplicates.append((current, posting))
        else:
            duplicates.append((posting, current))

    # A second pass collapses duplicate postings whose portals use different tracking
    # URLs but identify the same exact title, employer, and location.
    by_fingerprint: OrderedDict[tuple[str, str, str], NormalizedPosting] = OrderedDict()
    final: list[NormalizedPosting] = []
    url_duplicates: set[int] = set()
    for kept in by_identity.values():
        fp = fingerprint(kept)
        current = by_fingerprint.get(fp)
        if current is None:
            by_fingerprint[fp] = kept
            final.append(kept)
        elif _posting_quality(kept) > _posting_quality(current):
            by_fingerprint[fp] = kept
            duplicates.append((current, kept))
            try:
                final.remove(current)
            except ValueError:
                pass
            final.append(kept)
        else:
            duplicates.append((kept, current))
    return final, duplicates


def filter_and_deduplicate(
    postings: list[NormalizedPosting],
    query: str,
    hours: int = 24,
    now: datetime | None = None,
) -> tuple[list[tuple[NormalizedPosting, float]], list[NormalizedPosting]]:
    """Return (verified-fresh postings with age, timestamp-unknown postings).

    A known old timestamp is excluded, not moved to the unverified list. Unknown
    timestamps are only returned separately and can never be called fresh.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now.astimezone(timezone.utc) - timedelta(hours=hours)
    phrases = query_phrases(query)
    fresh: OrderedDict[tuple, tuple[NormalizedPosting, float]] = OrderedDict()
    unknown: OrderedDict[tuple, NormalizedPosting] = OrderedDict()

    for posting in postings:
        if not posting.title or not posting.source_url or not matches_query(posting, phrases):
            continue
        canonical = canonicalize_job_url(posting.source_url)
        identity = (canonical,) if canonical else fingerprint(posting)
        if posting.verified_posting_time and posting.posted_at:
            posted_at = posting.posted_at
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
            posted_at = posted_at.astimezone(timezone.utc)
            age = (now.astimezone(timezone.utc) - posted_at).total_seconds() / 3600
            if age < 0 or posted_at < cutoff:
                continue
            if identity not in fresh:
                fresh[identity] = (posting, round(age, 2))
        else:
            # A parsed timestamp is not automatically trustworthy. If a connector
            # cannot confirm that the field represents the original publication time,
            # show the listing in the separate unverified bucket when requested.
            if identity not in unknown and identity not in fresh:
                unknown[identity] = posting

    fresh_list = sorted(fresh.values(), key=lambda item: item[1])
    return fresh_list, list(unknown.values())
