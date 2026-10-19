import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx

from app.services.web_research import (
    _parse_page, _assert_public_http_url, build_search_plan, fetch_brave_web_research,
    freshness_code, portal_label_for_url,
)
from app.services.job_sources.base import NormalizedPosting
from app.services.research_scoring import score_posting


def test_freshness_and_region_search_plan():
    assert freshness_code(24) == "pd"
    assert freshness_code(168) == "pw"
    assert freshness_code(720) == "pm"
    plan = build_search_plan("Talent Acquisition Specialist, IT Recruiter, HR Recruiter", "india", "", 168)
    assert 18 <= len(plan) <= 20
    assert all(country == "IN" for _, country in plan)
    planned_query_text = " ".join(query for query, _ in plan)
    for domain in ("linkedin.com", "naukri.com", "indeed.com", "foundit.in", "shine.com", "iimjobs.com", "instahyre.com", "cutshort.io", "wellfound.com", "greenhouse.io"):
        assert domain in planned_query_text
    global_plan = build_search_plan("Talent Acquisition Specialist, IT Recruiter", "global", "", 168)
    assert 15 <= len(global_plan) <= 20
    assert any(country == "AE" for _, country in global_plan)
    assert any("greenhouse.io" in query for query, _ in global_plan)


def test_parse_job_posting_schema_extracts_date_company_salary_and_skills():
    posted = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    html = f'''<!doctype html><html><head><title>Role page</title>
    <script type="application/ld+json">{{"@context":"https://schema.org","@type":"JobPosting","title":"Talent Acquisition Specialist","datePosted":"{posted}","hiringOrganization":{{"@type":"Organization","name":"Example People Ltd"}},"jobLocation":{{"address":{{"addressLocality":"Bengaluru","addressRegion":"Karnataka","addressCountry":"India"}}}},"employmentType":"FULL_TIME","experienceRequirements":"3-5 years experience","skills":["Boolean Search","Stakeholder Management"],"baseSalary":{{"currency":"INR","value":{{"minValue":1200000,"maxValue":1800000,"unitText":"YEAR"}}}},"description":"Handle full-cycle recruitment and talent sourcing."}}</script></head><body>Recruitment</body></html>'''
    parsed = _parse_page(html, "https://jobs.example.com/talent-acquisition", "job listing snippet", "Search title", "IN")
    assert parsed["title"] == "Talent Acquisition Specialist"
    assert parsed["company"] == "Example People Ltd"
    assert parsed["verified"] is True
    assert parsed["posted_at"] is not None
    assert "Bengaluru" in parsed["location"]
    assert "Boolean Search" in parsed["skills"]
    assert "INR" in parsed["salary"]


def test_research_match_report_is_explainable_and_flags_concerns():
    posting = NormalizedPosting(
        title="Senior IT Recruiter", company="Example Co", location="Location not specified", work_mode="Unknown",
        source_url="https://jobs.example.com/recruiter", description="IT recruitment, Boolean Search, LinkedIn Recruiter, stakeholder management. Requires 5-7 years experience.",
        posted_at=None, verified_posting_time=False, provider="brave_web_search", source_company="Brave Web Search (IN)",
        posting_time_evidence="Original publication time not found", search_region_hint="IN",
    )
    profile = SimpleNamespace(
        target_titles="IT Recruiter, Talent Acquisition Specialist", resume_headline="IT & Non-IT Recruiter",
        employment_highlights="End-to-end recruitment", profile_summary="3+ years recruitment experience",
        skills="IT Recruitment, Boolean Search, LinkedIn Recruiter, stakeholder management", resume_text="Talent Acquisition",
        preferred_locations="India, Remote", preferred_work_modes="Remote, Hybrid", years_experience=3,
    )
    result = score_posting(posting, profile, "IT Recruiter")
    assert 0 <= result["match_score"] <= 100
    assert result["match_reasons"]
    assert any("experience gap" in c.lower() for c in result["concerns"])
    assert any("publication time" in c.lower() for c in result["concerns"])
    assert result["salary_range"] == "Not disclosed"


def test_private_urls_are_rejected_for_page_verification():
    for url in ("http://127.0.0.1/admin", "http://localhost/test", "http://192.168.1.10/", "file:///etc/passwd"):
        try:
            _assert_public_http_url(url)
            assert False, f"Expected URL to be rejected: {url}"
        except ValueError:
            pass


def test_brave_search_normalizes_result_and_verifies_original_page(monkeypatch):
    posted = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    html = f'''<!doctype html><html><head><title>TA role</title><script type="application/ld+json">{{"@type":"JobPosting","title":"Talent Acquisition Specialist","datePosted":"{posted}","hiringOrganization":{{"name":"Example Co"}},"jobLocation":{{"address":{{"addressLocality":"Delhi","addressCountry":"India"}}}},"description":"Recruitment and Boolean Search role. 3-5 years experience."}}</script></head><body>Job</body></html>'''

    async def fake_page(url, timeout):
        return html, url

    monkeypatch.setattr("app.services.web_research._fetch_html_safely", fake_page)

    def handler(request):
        return httpx.Response(200, json={"web": {"results": [{
            "title": "Talent Acquisition Specialist - Example Co",
            "url": "https://jobs.example.com/ta-role",
            "description": "Recruitment opening",
            "page_age": "2 hours ago",
        }]}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_brave_web_research(client, "test-key", "Talent Acquisition Specialist, IT Recruiter", "india", "", 24)

    postings, diagnostics = asyncio.run(run())
    assert len(postings) == 1
    assert postings[0].provider == "brave_web_search"
    assert postings[0].company == "Example Co"
    assert postings[0].verified_posting_time is True
    assert diagnostics["queries_succeeded"] >= 1
    assert diagnostics["original_pages_verified"] == 1
    assert diagnostics["portal_breakdown"]
    assert diagnostics["query_breakdown"]


def test_discovery_includes_optional_brave_search_and_match_details(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main_module
    now = datetime.now(timezone.utc)
    posting = NormalizedPosting(
        title="Talent Acquisition Specialist", company="Example Web Employer", location="Bengaluru, India",
        work_mode="Hybrid", source_url="https://jobs.example.com/ta-role", description="Full-time Talent Acquisition role. Requires 3-5 years experience. Boolean Search and stakeholder management.",
        posted_at=now - timedelta(hours=2), verified_posting_time=True, provider="brave_web_search",
        source_company="Brave Web Search (IN)", posting_time_evidence="JobPosting structured data datePosted",
        experience_required="3-5 years experience", required_skills=["Boolean Search", "Stakeholder Management"],
    )

    async def fake_feed(client, source, query=""):
        return []

    async def fake_brave(**kwargs):
        return [posting], {
            "queries_planned": 3, "queries_succeeded": 3, "search_results_seen": 5,
            "unique_candidates_checked": 1, "original_pages_verified": 1, "errors": [],
            "portal_breakdown": [{"portal": "LinkedIn Jobs", "results_seen": 1}],
            "query_breakdown": [{"scope": "LinkedIn Jobs", "planned": 1, "succeeded": 1, "results_seen": 2}],
        }

    monkeypatch.setattr(main_module, "_fetch_source", fake_feed)
    monkeypatch.setattr(main_module, "fetch_brave_web_research", fake_brave)
    monkeypatch.setattr(main_module.settings, "brave_search_api_key", "test-key")

    with TestClient(main_module.app) as client:
        # Make profile facts sufficiently specific for a meaningful match explanation.
        profile_response = client.get("/api/profile")
        profile = profile_response.json()
        profile.update({
            "target_titles": "Talent Acquisition Specialist, IT Recruiter",
            "skills": "Boolean Search, Stakeholder Management, IT Recruitment",
            "years_experience": 3,
            "preferred_locations": "India, Remote",
            "preferred_work_modes": "Remote, Hybrid",
        })
        assert client.put("/api/profile", json=profile).status_code == 200
        response = client.post("/api/discovery/search", json={
            "query": "Talent Acquisition Specialist, IT Recruiter", "hours": 24,
            "region": "india", "work_modes": ["hybrid", "unknown", "remote"],
            "employment_types": ["full_time", "unknown", "contract_freelance", "part_time", "internship", "temporary"],
            "include_unverified": True,
        })
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["web_search_configured"] is True
        assert data["web_search_queries"] == 3
        assert data["fresh_count"] >= 1
        found = next(job for job in data["fresh_jobs"] if job["provider"] == "brave_web_search")
        assert found["match_score"] > 0
        assert found["match_reasons"]
        assert found["posting_time_evidence"] == "JobPosting structured data datePosted"
        assert any("LinkedIn Jobs" in note for note in data["web_search_notes"])


def test_portal_label_for_indexed_job_urls():
    assert portal_label_for_url("https://www.linkedin.com/jobs/view/123") == "LinkedIn Jobs"
    assert portal_label_for_url("https://www.naukri.com/job-listings/example") == "Naukri"
    assert portal_label_for_url("https://jobs.lever.co/acme/123") == "Lever company board"
    assert portal_label_for_url("https://example.org/jobs/1") == "example.org"



def test_search_plan_expands_role_variants_and_india_city_queries():
    plan = build_search_plan("Talent Acquisition Specialist, IT Recruiter, HR Recruiter", "india", "", 168)
    queries = "\n".join(query for query, _ in plan).lower()
    assert len(plan) == 20
    for term in ("delhi ncr", "bengaluru", "mumbai", "hyderabad", "pune"):
        assert term in queries
    assert "hr generalist" in queries
    assert "recruitment coordinator" in queries
