"""Explainable job/profile scoring and research notes for discovery results.

These are heuristic estimates based on visible listing text and user-supplied profile data,
not employer assessments and not claims that the source itself scored the candidate.
"""
from __future__ import annotations
import json
import re
import unicodedata
from .job_sources.base import NormalizedPosting


def _norm(s: str | None) -> str:
    value = unicodedata.normalize("NFKD", s or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).lower()
    return " ".join(re.sub(r"[^a-z0-9+#.]+", " ", value).split())


def _loads(s: str | None, default):
    try:
        val = json.loads(s or "")
        return val
    except (ValueError, TypeError):
        return default


def _salary(posting: NormalizedPosting) -> str:
    if posting.salary_range and posting.salary_range != "Not disclosed":
        return posting.salary_range[:180]
    text = posting.description or ""
    patterns = [
        r"(?:₹|INR|Rs\.?|USD|\$|GBP|£|EUR|€)\s?[\d,]+(?:\s?[-–to]+\s?(?:₹|INR|Rs\.?|USD|\$|GBP|£|EUR|€)?\s?[\d,]+)?(?:\s?(?:LPA|per year|/year|monthly|/month|per hour))?",
        r"\b\d+(?:\.\d+)?\s*(?:LPA|lakhs? per annum)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return " ".join(m.group(0).split())[:180]
    return "Not disclosed"


def _experience_text(posting: NormalizedPosting) -> str:
    if posting.experience_required and posting.experience_required != "Not disclosed":
        return posting.experience_required[:250]
    text = (posting.title or "") + " " + (posting.description or "")
    patterns = [
        r"\b(\d+\s*(?:-|to)\s*\d+\s*years?\s+(?:of\s+)?experience)\b",
        r"\b(\d+\+?\s+years?\s+(?:of\s+)?experience)\b",
        r"\b(\d+\s*[-–]\s*\d+\s*years?)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1)
    return "Not disclosed"


def _skills(posting: NormalizedPosting) -> list[str]:
    if posting.required_skills:
        return list(dict.fromkeys(x.strip() for x in posting.required_skills if x.strip()))[:12]
    terms = (
        "end-to-end recruitment", "it recruitment", "non-it recruitment", "talent acquisition", "technical recruitment",
        "candidate sourcing", "boolean search", "linkedin recruiter", "stakeholder management", "talent mapping",
        "interview coordination", "executive search", "leadership hiring", "recruitment analytics", "ats", "workday",
        "naukri", "indeed", "excel", "python", "sql", "power bi", "sap", "salesforce", "machine learning", "data science",
    )
    description = _norm(posting.title + " " + posting.description)
    return [term for term in terms if _norm(term) in description][:10]


def _required_year_bounds(value: str) -> tuple[float | None, float | None]:
    value = value.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:\+\s*)?years?", value)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", value)
    if m:
        years = float(m.group(1))
        return years, None
    return None, None


def score_posting(posting: NormalizedPosting, profile, query: str = "") -> dict:
    title = _norm(posting.title)
    description = _norm(posting.description)
    role_fields = " ".join([
        getattr(profile, "target_titles", "") or "", getattr(profile, "resume_headline", "") or "",
        getattr(profile, "employment_highlights", "") or "", getattr(profile, "profile_summary", "") or "",
    ])
    profile_text = _norm(" ".join([
        role_fields, getattr(profile, "skills", "") or "", getattr(profile, "resume_text", "") or "",
        getattr(profile, "preferred_locations", "") or "", getattr(profile, "preferred_work_modes", "") or "",
    ]))
    profile_roles = [_norm(x) for x in re.split(r"[,;\n|]+", (getattr(profile, "target_titles", "") or "") + "," + (getattr(profile, "resume_headline", "") or "")) if len(_norm(x)) > 2]
    exact_role_match = any(role and (role in title or title in role) for role in profile_roles)
    recruiter_role = any(t in title for t in ("recruiter", "recruitment", "talent acquisition", "talent partner", "human resources", "hr " , " hr"))
    title_score = 30 if exact_role_match else (23 if recruiter_role else 8 if any(tok in title and tok in profile_text for tok in title.split() if len(tok) > 3) else 0)

    required = _skills(posting)
    matched = [skill for skill in required if _norm(skill) in profile_text]
    if required:
        skills_score = round(35 * len(matched) / len(required))
    else:
        job_tokens = set(re.findall(r"[a-z][a-z0-9+#.]{2,}", description))
        profile_tokens = set(re.findall(r"[a-z][a-z0-9+#.]{2,}", profile_text))
        meaningful = job_tokens & profile_tokens - {"the", "and", "with", "for", "role", "job", "candidate", "experience", "skills", "team"}
        skills_score = min(25, len(meaningful) * 3)

    candidate_years = float(getattr(profile, "years_experience", 0) or 0)
    low, high = _required_year_bounds(_experience_text(posting))
    if low is None:
        experience_score = 10 if candidate_years > 0 else 5
    elif candidate_years >= low and (high is None or candidate_years <= high + 2):
        experience_score = 20
    elif candidate_years >= max(0, low - 1):
        experience_score = 13
    else:
        experience_score = 4

    location = _norm(posting.location)
    preferences = _norm((getattr(profile, "preferred_locations", "") or "") + " " + (getattr(profile, "preferred_work_modes", "") or ""))
    mode = _norm(posting.work_mode)
    if any(term in location for term in ("remote", "worldwide", "anywhere")) and any(term in preferences for term in ("remote", "wfh", "work from home")):
        context_score = 15
    elif location != "location not specified" and any(tok in preferences for tok in location.split() if len(tok) > 3):
        context_score = 13
    elif mode in preferences and mode not in {"unknown", ""}:
        context_score = 13
    elif location != "location not specified":
        context_score = 8
    else:
        context_score = 5

    score = min(100, max(0, title_score + skills_score + experience_score + context_score))
    reasons = []
    if exact_role_match:
        reasons.append("Job title aligns with a target role or resume headline.")
    elif recruiter_role:
        reasons.append("Job falls within the recruitment / talent-acquisition domain.")
    if matched:
        reasons.append("Matching profile skills: " + ", ".join(matched[:6]) + ".")
    if low is not None:
        if candidate_years >= low and (high is None or candidate_years <= high + 2):
            reasons.append(f"Saved profile experience ({candidate_years:g} years) is broadly compatible with the posted requirement.")
        else:
            reasons.append(f"Experience comparison: profile {candidate_years:g} years; vacancy says {_experience_text(posting)}.")
    if posting.location and posting.location != "Location not specified":
        reasons.append("Listing includes a location: " + posting.location + ".")
    if not reasons:
        reasons.append("Preliminary keyword-based comparison only; review the original listing and profile evidence.")

    concerns = []
    if low is not None and candidate_years < low:
        concerns.append(f"Potential experience gap: listing asks for {_experience_text(posting)}; saved profile says {candidate_years:g} years.")
    if _salary(posting) == "Not disclosed":
        concerns.append("Salary is not disclosed in the captured listing content.")
    if not posting.location or posting.location == "Location not specified":
        region = posting.search_region_hint
        concerns.append("Exact job location was not found on the original page" + (f" (search was targeted to {region})" if region else "") + "; confirm location and eligibility.")
    if not posting.verified_posting_time or not posting.posted_at:
        concerns.append("Original publication time could not be verified from the listing page.")
    if posting.provider == "brave_web_search" and not posting.description.strip():
        concerns.append("Only web-search metadata was available; review the employer's original page.")

    score_breakdown = {
        "role_relevance": {"score": title_score, "max": 30, "percent": round(title_score / 30 * 100)},
        "skill_alignment": {"score": skills_score, "max": 35, "percent": round(skills_score / 35 * 100)},
        "experience_fit": {"score": experience_score, "max": 20, "percent": round(experience_score / 20 * 100)},
        "location_work_fit": {"score": context_score, "max": 15, "percent": round(context_score / 15 * 100)},
    }
    return {
        "match_score": score,
        "match_reasons": reasons[:6],
        "concerns": concerns[:6],
        "required_skills": required,
        "matched_skills": matched[:12],
        "score_breakdown": score_breakdown,
        "match_method": "rule_based",
        "salary_range": _salary(posting),
        "experience_required": _experience_text(posting),
        "posting_time_evidence": posting.posting_time_evidence or ("Source exposes a publication timestamp." if posting.verified_posting_time else "No trustworthy original posting timestamp available."),
        "verification_status": "verified" if posting.verified_posting_time and posting.posted_at else "unverified",
    }
