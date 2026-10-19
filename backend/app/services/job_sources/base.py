from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class NormalizedPosting:
    title: str
    company: str
    location: str
    work_mode: str
    source_url: str
    description: str
    posted_at: datetime | None
    verified_posting_time: bool
    provider: str
    source_company: str
    posting_time_evidence: str = ""
    salary_range: str = "Not disclosed"
    experience_required: str = "Not disclosed"
    required_skills: list[str] = field(default_factory=list)
    search_region_hint: str = ""


def infer_work_mode(location: str, description: str = "", explicit: str | None = None) -> str:
    if explicit:
        value = explicit.strip().lower()
        if value in {"remote", "hybrid", "on-site", "onsite"}:
            return "On-site" if value == "onsite" else value.title() if value != "on-site" else "On-site"
    text = f"{location} {description}".lower()
    if "remote" in text or "work from home" in text or "work-from-home" in text:
        return "Remote"
    if "hybrid" in text:
        return "Hybrid"
    if "on-site" in text or "onsite" in text or "in office" in text:
        return "On-site"
    return "Unknown"
