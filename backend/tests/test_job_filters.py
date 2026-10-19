from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import DiscoveryRequest, AgentRunRequest
from app.services.job_filters import (
    classify_employment_type,
    classify_work_mode,
    location_matches_region,
    matches_search_filters,
)
from app.services.job_sources.base import NormalizedPosting
from app.main import _adzuna_countries_for_search


def posting(title="Talent Acquisition Specialist", location="Bengaluru, Karnataka, India", mode="Hybrid", description="Full-time permanent role"):
    return NormalizedPosting(
        title=title,
        company="Example Company",
        location=location,
        work_mode=mode,
        source_url="https://example.com/careers/role-1",
        description=description,
        posted_at=datetime.now(timezone.utc),
        verified_posting_time=True,
        provider="test",
        source_company="Example",
    )


def test_india_region_matches_common_city_and_state_names():
    assert location_matches_region(posting(location="Bengaluru, Karnataka"), "india")
    assert location_matches_region(posting(location="Bhopal, Madhya Pradesh"), "india")
    assert location_matches_region(posting(location="Jalandhar, India"), "india")
    assert not location_matches_region(posting(location="New York, USA", mode="On-site"), "india")
    assert not location_matches_region(posting(location="Remote, US", mode="Remote"), "india")


def test_region_filters_cover_all_requested_regions():
    assert location_matches_region(posting(location="Singapore", mode="On-site"), "asia")
    assert location_matches_region(posting(location="Berlin, Germany", mode="On-site"), "europe")
    assert location_matches_region(posting(location="Toronto, Canada", mode="On-site"), "americas")
    assert location_matches_region(posting(location="Dubai, UAE", mode="On-site"), "middle_east")
    assert location_matches_region(posting(location="Nairobi, Kenya", mode="On-site"), "africa")
    assert location_matches_region(posting(location="Sydney, Australia", mode="On-site"), "oceania")
    assert location_matches_region(posting(location="New York, USA", mode="On-site"), "global")


def test_region_filters_keep_generic_remote_jobs_but_exclude_explicit_other_region():
    assert location_matches_region(posting(location="Remote", mode="Remote", description="Full-time role"), "india")
    assert location_matches_region(posting(location="Remote - India", mode="Remote"), "india")
    assert not location_matches_region(posting(location="Remote - USA", mode="Remote"), "india")
    assert location_matches_region(posting(location="Remote", mode="Remote", description="Available across Europe"), "europe")


def test_custom_location_accepts_one_of_multiple_places_and_remote_eligibility():
    assert location_matches_region(posting(location="Pune, India"), "custom", "Delhi, Pune")
    assert location_matches_region(posting(location="Remote", mode="Remote", description="Eligible candidates in Germany"), "custom", "Germany")
    assert not location_matches_region(posting(location="Mumbai, India"), "custom", "Germany")


def test_work_arrangement_and_employment_type_classification():
    assert classify_work_mode(posting(mode="Remote")) == "remote"
    assert classify_work_mode(posting(mode="Hybrid")) == "hybrid"
    assert classify_work_mode(posting(mode="On-site")) == "onsite"
    assert classify_work_mode(posting(mode="Unknown", location="Remote")) == "remote"
    assert classify_employment_type(posting(description="Part-time recruiting support")) == "part_time"
    assert classify_employment_type(posting(title="Freelance Technical Recruiter", description="Contract role")) == "contract_freelance"
    assert classify_employment_type(posting(title="HR Intern", description="Internship program")) == "internship"
    assert classify_employment_type(posting(description="Temporary seasonal work")) == "temporary"
    assert classify_employment_type(posting(description="Permanent full-time role")) == "full_time"
    assert classify_employment_type(posting(description="Recruitment role, details not given")) == "unknown"


def test_search_filters_apply_region_mode_and_employment_type_together():
    candidate = posting(location="Berlin, Germany", mode="Remote", description="Remote freelance recruiting contract")
    assert matches_search_filters(candidate, region="europe", work_modes=["remote"], employment_types=["contract_freelance"])
    assert not matches_search_filters(candidate, region="india", work_modes=["remote"], employment_types=["contract_freelance"])
    assert not matches_search_filters(candidate, region="europe", work_modes=["onsite"], employment_types=["contract_freelance"])
    assert not matches_search_filters(candidate, region="europe", work_modes=["remote"], employment_types=["full_time"])


def test_custom_location_requires_location_text():
    with pytest.raises(ValidationError):
        DiscoveryRequest(region="custom", custom_location="")
    with pytest.raises(ValidationError):
        AgentRunRequest(region="custom", custom_location="")
    assert DiscoveryRequest(region="india").region == "india"


def test_adzuna_country_endpoints_follow_selected_region():
    assert _adzuna_countries_for_search("india", "", "in") == ["in"]
    assert set(_adzuna_countries_for_search("europe", "", "in")) >= {"gb", "de", "fr"}
    assert set(_adzuna_countries_for_search("americas", "", "in")) == {"us", "ca", "br", "mx"}
    assert _adzuna_countries_for_search("middle_east", "", "in") == []
    assert set(_adzuna_countries_for_search("global", "", "in")) >= {"in", "us", "gb", "au"}
