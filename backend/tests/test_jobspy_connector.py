import asyncio
import sys
from datetime import datetime, timedelta, timezone
from types import ModuleType

from app.services.job_sources.jobspy import (
    _make_search_plan,
    _parse_posted_value,
    _sites_for_location,
    fetch_jobspy_postings,
)


class FakeRow(dict):
    def to_dict(self):
        return dict(self)


class FakeFrame:
    def __init__(self, rows, attrs=None):
        self._rows = [FakeRow(row) for row in rows]
        self.attrs = attrs or {}
        self.empty = not self._rows

    def iterrows(self):
        for idx, row in enumerate(self._rows):
            yield idx, row


def test_jobspy_search_plan_is_bounded_and_covers_multiple_locations():
    plan = _make_search_plan(
        "IT Recruiter, Talent Acquisition Specialist, Technical Recruiter",
        "global", "", 6,
    )
    assert len(plan) == 6
    assert len({location for _, location in plan}) >= 3
    assert {role for role, _ in plan}.issubset({
        "it recruiter", "talent acquisition specialist", "technical recruiter"
    })


def test_jobspy_sites_are_limited_by_location_market():
    configured = ["linkedin", "indeed", "naukri", "glassdoor", "zip_recruiter", "bayt", "bdjobs", "hellowork"]
    india = _sites_for_location(configured, "India", "India")
    united_states = _sites_for_location(configured, "United States", "USA")
    france = _sites_for_location(configured, "France", "France")
    assert "naukri" in india
    assert "naukri" not in united_states
    assert "zip_recruiter" in united_states
    assert "hellowork" in france
    assert "hellowork" not in india


def test_jobspy_full_timestamp_is_preserved_and_normalized(monkeypatch):
    now = datetime.now(timezone.utc)
    captured = []

    def fake_scrape_jobs(**kwargs):
        captured.append(kwargs)
        return FakeFrame([{
            "title": "IT Recruiter",
            "company": "Example Staffing",
            "location": "Remote, India",
            "job_url": "https://www.linkedin.com/jobs/view/123/?trk=tracking",
            "job_url_direct": "https://example.com/apply/123",
            "date_posted": now - timedelta(hours=2),
            "description": "Own end-to-end recruitment and candidate sourcing.",
            "is_remote": True,
            "job_type": "fulltime",
            "min_amount": 1200000,
            "max_amount": 1500000,
            "currency": "INR",
            "interval": "yearly",
            "experience_range": "3-5 years",
            "skills": ["Boolean search", "Candidate sourcing"],
            "site": "linkedin",
        }])

    fake_module = ModuleType("jobspy")
    fake_module.scrape_jobs = fake_scrape_jobs
    monkeypatch.setitem(sys.modules, "jobspy", fake_module)

    postings, diagnostics = asyncio.run(fetch_jobspy_postings(
        query="IT Recruiter", region="india", custom_location="", hours=24,
        sites=["linkedin", "indeed", "naukri", "glassdoor"], max_searches=1, results_wanted=5,
    ))
    assert len(postings) == 1
    posting = postings[0]
    assert posting.title == "IT Recruiter"
    assert posting.provider == "jobspy"
    assert posting.source_company == "JobSpy · Linkedin"
    assert posting.verified_posting_time is True
    assert posting.posted_at is not None and posting.posted_at.tzinfo == timezone.utc
    assert posting.work_mode == "Remote"
    assert posting.salary_range == "INR 1,200,000–1,500,000/year"
    assert posting.experience_required == "3-5 years"
    assert posting.required_skills == ["Boolean search", "Candidate sourcing"]
    assert "date_posted" in posting.posting_time_evidence
    assert diagnostics["searches_attempted"] == 1
    assert captured[0]["hours_old"] == 24
    assert captured[0]["fetch_description"] is False
    assert "proxies" not in captured[0]
    assert "google" not in captured[0]["site_name"]


def test_jobspy_date_only_value_stays_unverified():
    posted_at, verified, evidence = _parse_posted_value("2026-10-19")
    assert posted_at is None
    assert verified is False
    assert "date-only" in evidence


def test_jobspy_midnight_without_timezone_stays_unverified():
    posted_at, verified, evidence = _parse_posted_value(datetime(2026, 10, 19, 0, 0, 0))
    assert posted_at is None
    assert verified is False
    assert "ambiguous precision" in evidence
