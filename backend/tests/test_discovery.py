from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.discovery import canonicalize_job_url, deduplicate_postings, filter_and_deduplicate, matches_query, query_match_reason, query_phrases
from app.services.job_sources.base import NormalizedPosting


def _posting(title, company, url, posted_at, verified=True, provider="lever"):
    return NormalizedPosting(
        title=title,
        company=company,
        location="Remote, India",
        work_mode="Remote",
        source_url=url,
        description="Talent acquisition and recruitment role",
        posted_at=posted_at,
        verified_posting_time=verified,
        provider=provider,
        source_company=company,
    )


def test_canonicalize_job_url_removes_tracking_but_preserves_job_id():
    source = "https://www.example.com/job/123/?utm_source=linkedin&gh_jid=123#apply"
    assert canonicalize_job_url(source) == "https://example.com/job/123?gh_jid=123"


def test_filter_separates_fresh_stale_and_unknown_timestamps():
    now = datetime.now(timezone.utc)
    postings = [
        _posting("Talent Acquisition Partner", "FreshCo", "https://jobs.example.com/fresh", now - timedelta(hours=3)),
        _posting("Talent Acquisition Partner", "OldCo", "https://jobs.example.com/old", now - timedelta(hours=48)),
        _posting("Talent Acquisition Specialist", "UnknownCo", "https://jobs.example.com/unknown", None, verified=False, provider="greenhouse"),
        _posting("HR Recruiter", "UntrustedTimestampCo", "https://jobs.example.com/untrusted", now - timedelta(hours=1), verified=False, provider="greenhouse"),
    ]
    fresh, unknown = filter_and_deduplicate(postings, "Talent Acquisition, HR Recruiter", hours=24, now=now)
    assert len(fresh) == 1
    assert fresh[0][0].company == "FreshCo"
    assert fresh[0][1] == 3.0
    assert len(unknown) == 2
    assert {item.company for item in unknown} == {"UnknownCo", "UntrustedTimestampCo"}


def test_source_crud_and_discovery(monkeypatch):
    suffix = uuid4().hex[:10]
    company = f"Test Company {suffix}"
    board_id = f"test-{suffix}"
    now = datetime.now(timezone.utc)

    async def fake_fetch_source(client, source):
        return [
            _posting(
                "Talent Acquisition Specialist",
                source.company_name,
                f"https://jobs.example.com/{source.board_id}?utm_source=test",
                now - timedelta(hours=1),
                provider=source.provider,
            ),
            _posting(
                "Talent Acquisition Specialist",
                f"Unknown {company}",
                f"https://jobs.example.com/{source.board_id}-unknown",
                None,
                verified=False,
                provider="greenhouse",
            ),
        ]

    monkeypatch.setattr("app.main._fetch_source", fake_fetch_source)
    with TestClient(app) as client:
        create = client.post("/api/sources", json={"provider": "lever", "company_name": company, "board_id": board_id})
        assert create.status_code == 201, create.text
        source_id = create.json()["id"]

        duplicate = client.post("/api/sources", json={"provider": "lever", "company_name": company, "board_id": board_id})
        assert duplicate.status_code == 409

        result = client.post("/api/discovery/search", json={"query": "Talent Acquisition", "hours": 24, "include_unverified": True})
        assert result.status_code == 200, result.text
        body = result.json()
        assert any(item["company"] == company for item in body["fresh_jobs"])
        assert any(item["company"] == f"Unknown {company}" for item in body["unverified_jobs"])
        assert body["fresh_count"] >= 1
        assert body["raw_postings_count"] >= 2
        assert body["query_matched_count"] >= 2
        assert body["timestamp_unverified_candidates_count"] >= 1

        saved = client.get("/api/jobs")
        assert any(job["company"] == company for job in saved.json())

        paused = client.patch(f"/api/sources/{source_id}", json={"enabled": False})
        assert paused.status_code == 200
        assert paused.json()["enabled"] is False

        removed = client.delete(f"/api/sources/{source_id}")
        assert removed.status_code == 204



def test_successful_source_with_zero_postings_is_reported_as_empty(monkeypatch):
    suffix = uuid4().hex[:10]
    company = f"Empty Feed {suffix}"

    async def empty_fetch(client, source):
        return []

    monkeypatch.setattr("app.main._fetch_source", empty_fetch)
    with TestClient(app) as client:
        created = client.post("/api/sources", json={
            "provider": "lever", "company_name": company, "board_id": f"empty-{suffix}"
        })
        assert created.status_code == 201, created.text
        result = client.post("/api/discovery/search", json={
            "query": "IT Recruiter", "hours": 168, "region": "global"
        })
        assert result.status_code == 200, result.text
        status = next((s for s in result.json()["source_statuses"] if s["source_id"] == created.json()["id"]), None)
        assert status is not None
        assert status["status"] == "empty"
        assert status["fetched_count"] == 0
        assert "returned 0 postings" in status["message"]
        client.delete(f"/api/sources/{created.json()['id']}")

def test_greenhouse_updated_at_is_not_mistaken_for_posted_time():
    import asyncio
    import httpx
    from app.services.job_sources.greenhouse import fetch_greenhouse

    payload = {
        "jobs": [{
            "id": 123,
            "title": "Talent Acquisition Specialist",
            "absolute_url": "https://boards.greenhouse.io/example/jobs/123",
            "updated_at": "2026-10-18T09:00:00Z",
            "location": {"name": "Remote"},
            "content": "<p>Recruitment role</p>",
        }]
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetch_greenhouse(client, "example", "Example Co")

    results = asyncio.run(run())
    assert len(results) == 1
    assert results[0].posted_at is None
    assert results[0].verified_posting_time is False


def test_lever_created_at_is_parsed_as_utc_timestamp():
    import asyncio
    import httpx
    from app.services.job_sources.lever import fetch_lever

    created_at = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp() * 1000)
    payload = [{
        "id": "job-1",
        "text": "IT Recruiter",
        "hostedUrl": "https://jobs.lever.co/example/job-1",
        "applyUrl": "https://jobs.lever.co/example/job-1/apply",
        "createdAt": created_at,
        "categories": {"location": "India"},
        "descriptionPlain": "IT recruitment role",
        "workplaceType": "remote",
    }]
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetch_lever(client, "example", "Example Co")

    results = asyncio.run(run())
    assert len(results) == 1
    assert results[0].verified_posting_time is True
    assert abs((datetime.now(timezone.utc) - results[0].posted_at).total_seconds() / 3600 - 2) < 0.1
    assert results[0].work_mode == "Remote"


def test_posting_windows_accept_month_range_and_reject_more_than_month():
    from pydantic import ValidationError
    from app.schemas import DiscoveryRequest, AgentRunRequest

    assert DiscoveryRequest(hours=24).hours == 24
    assert DiscoveryRequest(hours=168).hours == 168
    assert DiscoveryRequest(hours=720).hours == 720
    assert AgentRunRequest(hours=720).hours == 720
    try:
        DiscoveryRequest(hours=721)
        assert False, "Expected validation error for a window longer than 30 days"
    except ValidationError:
        pass
    try:
        AgentRunRequest(hours=721)
        assert False, "Expected validation error for a window longer than 30 days"
    except ValidationError:
        pass


def test_one_month_window_includes_older_than_week_but_not_older_than_month():
    now = datetime.now(timezone.utc)
    postings = [
        _posting("HR Recruiter", "ThreeWeeksOld", "https://jobs.example.com/three-weeks", now - timedelta(days=21)),
        _posting("HR Recruiter", "TooOld", "https://jobs.example.com/too-old", now - timedelta(days=35)),
    ]
    month_fresh, _ = filter_and_deduplicate(postings, "HR Recruiter", hours=720, now=now)
    week_fresh, _ = filter_and_deduplicate(postings, "HR Recruiter", hours=168, now=now)
    assert [item[0].company for item in month_fresh] == ["ThreeWeeksOld"]
    assert week_fresh == []


def test_query_phrases_extract_titles_from_natural_language_instruction():
    from app.services.discovery import query_phrases

    query = ("Search for IT Recruiter, Talent Acquisition Specialist, Technical Recruiter, "
             "HR Recruiter, Recruitment Consultant, and HR Executive jobs across India and international markets. "
             "Prioritize remote jobs and opportunities in Delhi NCR.")
    phrases = query_phrases(query)
    assert "it recruiter" in phrases
    assert "talent acquisition specialist" in phrases
    assert "technical recruiter" in phrases
    assert "hr recruiter" in phrases
    assert "recruitment consultant" in phrases
    assert "hr executive" in phrases
    assert not any("prioritize" in phrase or "international markets" in phrase for phrase in phrases)


def test_discovery_accepts_natural_instruction_longer_than_500_characters():
    from app.schemas import DiscoveryRequest, AgentRunRequest

    query = "Search for IT Recruiter, Talent Acquisition Specialist, HR Recruiter. " + "Prioritize remote roles and verified postings. " * 20
    assert len(query) > 500
    assert DiscoveryRequest(query=query, hours=168).hours == 168
    assert AgentRunRequest(query=query, hours=168).hours == 168


def test_unexpected_source_error_is_reported_without_failing_search(monkeypatch):
    suffix = uuid4().hex[:10]
    company = f"Broken Source {suffix}"
    board_id = f"broken-{suffix}"

    async def broken_fetch(client, source):
        raise RuntimeError("mock connector parsing issue")

    monkeypatch.setattr("app.main._fetch_source", broken_fetch)
    with TestClient(app) as client:
        created = client.post("/api/sources", json={"provider": "lever", "company_name": company, "board_id": board_id})
        assert created.status_code == 201, created.text
        result = client.post("/api/discovery/search", json={"query": "Talent Acquisition", "hours": 168})
        assert result.status_code == 200, result.text
        statuses = [item for item in result.json()["source_statuses"] if item["company_name"] == company]
        assert len(statuses) == 1
        assert statuses[0]["status"] == "error"
        assert "RuntimeError" in statuses[0]["message"]
        client.delete(f"/api/sources/{created.json()['id']}")


def test_recommended_public_feeds_are_seeded_on_first_run():
    with TestClient(app) as client:
        response = client.get("/api/sources")
        assert response.status_code == 200
        providers = {source["provider"] for source in response.json()}
        assert "arbeitnow" in providers
        assert "remoteok" in providers
        assert "jobicy" in providers
        assert "himalayas" in providers


def test_recruiting_query_matches_common_title_variants():
    from app.services.discovery import matches_query, query_phrases

    phrases = query_phrases("Search for IT Recruiter, Talent Acquisition Specialist, Technical Recruiter, HR Recruiter, Recruitment Consultant, and HR Executive jobs across India and international markets.")
    senior_recruiter = _posting("Senior Recruiter", "Example Co", "https://jobs.example.com/senior-recruiter", datetime.now(timezone.utc))
    talent_partner = _posting("Talent Partner", "Example Co", "https://jobs.example.com/talent-partner", datetime.now(timezone.utc))
    unrelated = _posting("Software Engineer", "Example Co", "https://jobs.example.com/engineer", datetime.now(timezone.utc))
    assert matches_query(senior_recruiter, phrases)
    assert matches_query(talent_partner, phrases)
    assert not matches_query(unrelated, phrases)


def test_jobicy_public_api_adapter_normalizes_listing():
    import asyncio
    import httpx
    from app.services.job_sources.aggregators import fetch_jobicy

    payload = {"jobs": [{
        "jobTitle": "Talent Acquisition Specialist",
        "companyName": "Example Remote Co",
        "url": "https://jobicy.com/jobs/example-talent-acquisition",
        "jobGeo": "Anywhere",
        "jobDescription": "<p>Recruitment and sourcing role</p>",
        "pubDate": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "jobType": ["Full-Time"],
        "salaryMin": 40000,
        "salaryMax": 50000,
        "salaryCurrency": "USD",
        "salaryPeriod": "yearly",
    }]}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetch_jobicy(client, "default", "Jobicy")

    results = asyncio.run(run())
    assert len(results) == 1  # Duplicate listing from the two geographic passes is collapsed.
    assert results[0].provider == "jobicy"
    assert results[0].company == "Example Remote Co"
    assert results[0].verified_posting_time is True
    assert "Salary:" in results[0].description


def test_discovery_applies_region_work_arrangement_and_employment_filters(monkeypatch):
    suffix = uuid4().hex[:10]
    now = datetime.now(timezone.utc)
    candidates = [
        _posting("Talent Acquisition Specialist", "IndiaCo", f"https://jobs.example.com/{suffix}-india", now - timedelta(hours=1)),
        _posting("IT Recruiter", "EuropeCo", f"https://jobs.example.com/{suffix}-europe", now - timedelta(hours=2)),
        _posting("Recruiter", "USCo", f"https://jobs.example.com/{suffix}-us", now - timedelta(hours=1)),
        _posting("Freelance Recruiter", "RemoteCo", f"https://jobs.example.com/{suffix}-remote", now - timedelta(hours=1)),
    ]
    candidates[0].location = "Bengaluru, India"
    candidates[0].work_mode = "Hybrid"
    candidates[0].description = "Full-time permanent Talent Acquisition role"
    candidates[1].location = "Berlin, Germany"
    candidates[1].work_mode = "On-site"
    candidates[1].description = "Contract recruiter role"
    candidates[2].location = "Remote, USA"
    candidates[2].work_mode = "Remote"
    candidates[2].description = "Full-time IT recruiter role"
    candidates[3].location = "Remote"
    candidates[3].work_mode = "Remote"
    candidates[3].description = "Freelance recruiting opportunity available worldwide"

    async def fake_fetch_source(client, source):
        return candidates

    async def fake_fetch_adzuna(client, country_code, query, company_name):
        return candidates

    monkeypatch.setattr("app.main._fetch_source", fake_fetch_source)
    monkeypatch.setattr("app.main.fetch_adzuna", fake_fetch_adzuna)
    with TestClient(app) as client:
        response = client.post("/api/discovery/search", json={
            "query": "Recruiter, Talent Acquisition",
            "hours": 24,
            "region": "india",
            "work_modes": ["hybrid"],
            "employment_types": ["full_time"],
            "include_unverified": False,
        })
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["region"] == "india"
        assert result["work_modes"] == ["hybrid"]
        assert result["employment_types"] == ["full_time"]
        assert result["fresh_count"] == 1
        assert result["fresh_jobs"][0]["company"] == "IndiaCo"
        assert result["location_filtered_out_count"] >= 1
        assert result["work_mode_filtered_out_count"] >= 1
        assert result["employment_type_filtered_out_count"] >= 0



def test_recruitment_role_variants_match_broad_query_and_unrelated_roles_do_not():
    query = "Talent Acquisition Specialist, IT Recruiter, HR Recruiter, HR Executive"
    phrases = query_phrases(query)
    variants = [
        "Senior Recruiter", "Recruiting Coordinator", "Talent Acquisition Manager",
        "Talent Acquisition Partner", "Technical Sourcer", "HRBP", "HR Operations Specialist",
        "Human Resources Business Partner", "People Operations Manager", "Executive Search Consultant",
    ]
    for index, title in enumerate(variants):
        candidate = _posting(title, "Example Co", f"https://jobs.example.com/variant-{index}", datetime.now(timezone.utc))
        assert matches_query(candidate, phrases), title
    unrelated = _posting("Software Engineer", "Example Co", "https://jobs.example.com/unrelated", datetime.now(timezone.utc))
    assert not matches_query(unrelated, phrases)
    ok, reason = query_match_reason(_posting("Recruiting Coordinator", "Example Co", "https://jobs.example.com/recruit-coord", datetime.now(timezone.utc)), query, phrases)
    assert ok and "variant" in reason.lower()


def test_deduplicate_postings_prefers_verified_and_richer_copy():
    now = datetime.now(timezone.utc)
    unknown = _posting("Talent Acquisition Partner", "Example Co", "https://www.example.com/job/7?utm_source=x", None, verified=False, provider="brave_web_search")
    unknown.description = "Recruiter"
    verified = _posting("Talent Acquisition Partner", "Example Co", "https://example.com/job/7", now - timedelta(hours=1), verified=True, provider="lever")
    verified.description = "Talent acquisition partner with full-cycle recruitment and sourcing responsibilities." * 3
    unique, duplicates = deduplicate_postings([unknown, verified])
    assert len(unique) == 1
    assert unique[0].provider == "lever"
    assert len(duplicates) == 1


def test_discovery_returns_filter_funnel_and_exclusion_reasons(monkeypatch):
    suffix = uuid4().hex[:10]
    now = datetime.now(timezone.utc)
    candidates = [
        _posting("Senior Recruiter", f"Fresh {suffix}", f"https://jobs.example.com/fresh-{suffix}", now - timedelta(hours=2)),
        _posting("Software Engineer", f"Irrelevant {suffix}", f"https://jobs.example.com/irrelevant-{suffix}", now - timedelta(hours=2)),
        _posting("Talent Acquisition Specialist", f"Old {suffix}", f"https://jobs.example.com/old-{suffix}", now - timedelta(days=10)),
        _posting("Recruiting Coordinator", f"Unknown {suffix}", f"https://jobs.example.com/unknown-{suffix}", None, verified=False),
    ]
    async def fake_fetch(client, source):
        return candidates if source.provider == "lever" and source.board_id == f"coverage-{suffix}" else []
    monkeypatch.setattr("app.main._fetch_source", fake_fetch)
    with TestClient(app) as client:
        created = client.post("/api/sources", json={"provider": "lever", "company_name": f"Coverage {suffix}", "board_id": f"coverage-{suffix}"})
        assert created.status_code == 201
        response = client.post("/api/discovery/search", json={
            "query": "Talent Acquisition Specialist, IT Recruiter, HR Recruiter, HR Executive",
            "hours": 168, "include_unverified": True,
            "work_modes": ["remote", "hybrid", "onsite", "unknown"],
            "employment_types": ["full_time", "part_time", "contract_freelance", "internship", "temporary", "unknown"],
        })
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["raw_postings_count"] >= 4
        assert data["unique_postings_count"] <= data["raw_postings_count"]
        assert data["filter_funnel"]
        assert any(stage["stage"] == "Role relevance" for stage in data["filter_funnel"])
        reason_codes = {item["reason_code"] for item in data["excluded_listings"]}
        assert "role_keyword_mismatch" in reason_codes
        assert "outside_posting_window" in reason_codes
        assert "posting_time_unverified" in reason_codes
        assert data["exclusion_reason_counts"]["role_keyword_mismatch"] >= 1
        client.delete(f"/api/sources/{created.json()['id']}")


def test_himalayas_source_identifier_is_validated():
    with TestClient(app) as client:
        existing = next((s for s in client.get("/api/sources").json() if s["provider"] == "himalayas" and s["board_id"] == "default"), None)
        if existing:
            assert existing["company_name"].startswith("Himalayas")
        else:
            response = client.post("/api/sources", json={"provider": "himalayas", "company_name": "Himalayas Remote Jobs", "board_id": "default"})
            assert response.status_code == 201, response.text
            assert response.json()["provider"] == "himalayas"
            client.delete(f"/api/sources/{response.json()['id']}")


def test_himalayas_adapter_preserves_required_apply_link_and_attribution():
    import asyncio
    import httpx
    from app.services.job_sources.aggregators import fetch_himalayas

    payload = {"jobs": [{
        "title": "Talent Acquisition Specialist",
        "companyName": "Remote Example",
        "applicationLink": "https://himalayas.app/jobs/example-ta",
        "pubDate": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        "employmentType": "Full Time",
        "locationRestrictions": ["India"],
        "description": "Recruitment, sourcing, and stakeholder management.",
        "minSalary": 1200000,
        "maxSalary": 1600000,
        "currency": "INR",
        "salaryPeriod": "annual",
        "categories": ["Human Resources"],
    }]}
    def handler(request):
        return httpx.Response(200, json=payload)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_himalayas(client, "default", "Talent Acquisition Specialist, IT Recruiter")
    results = asyncio.run(run())
    assert len(results) == 1
    assert results[0].source_url == "https://himalayas.app/jobs/example-ta"
    assert results[0].provider == "himalayas"
    assert "attribution required" in results[0].source_company.lower()
    assert results[0].verified_posting_time is True
    assert "Full Time" in results[0].description


def test_unverified_jobs_are_included_by_default_for_review():
    """Unknown-date leads should be reviewable by default but never treated as fresh."""
    from app.schemas import DiscoveryRequest

    request = DiscoveryRequest(query="IT Recruiter", hours=24)
    assert request.include_unverified is True
