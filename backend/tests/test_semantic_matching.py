"""Tests for optional local embedding reranking and safe fallback."""
import asyncio
from types import SimpleNamespace

from app.services import semantic_matching as sm


def _profile():
    return SimpleNamespace(
        target_titles="Talent Acquisition Specialist, IT Recruiter",
        resume_headline="IT and Non-IT Recruiter",
        profile_summary="Recruitment professional with sourcing and stakeholder management experience.",
        years_experience=3,
        skills="IT recruitment, candidate sourcing, Boolean search, stakeholder management",
        employment_highlights="End-to-end hiring across India",
        employment_history_json="[]",
        it_skills_json="[]",
        certifications_json="[]",
        resume_text="Experienced recruiter using Boolean search, candidate sourcing, interview coordination and talent mapping.",
    )


def _job(title="Talent Acquisition Specialist"):
    return SimpleNamespace(
        title=title,
        company="Example Company",
        location="Remote, India",
        work_mode="Remote",
        description="Manage end-to-end recruiting, candidate sourcing and stakeholder management.",
    )


def test_cosine_similarity_handles_valid_and_invalid_vectors():
    assert sm.cosine_similarity([1, 0], [0, 1]) == 0
    assert sm.cosine_similarity([1, 0], [1, 1]) > 0.70
    assert sm.cosine_similarity([1], [1, 2]) is None
    assert sm.cosine_similarity([0, 0], [1, 0]) is None


def test_calibration_and_blend_are_bounded_and_rule_weighted():
    assert sm.calibrated_semantic_fit(-0.2) == 0
    assert sm.calibrated_semantic_fit(0.70) == 100
    assert sm.calibrated_semantic_fit(0.45) == 50
    assert sm.blend_match_scores(80, 20) == 62
    assert sm.blend_match_scores(120, -5) == 70


def test_semantic_scoring_returns_hybrid_score_when_embeddings_available(monkeypatch):
    async def fake_embeddings(texts):
        assert texts[0].startswith("search_query: ")
        assert texts[1].startswith("search_document: ")
        return [[1.0, 0.0], [0.8, 0.6]]

    monkeypatch.setattr(sm, "_fetch_embeddings", fake_embeddings)
    monkeypatch.setattr(sm.settings, "semantic_matching_enabled", True)
    result = asyncio.run(sm.semantic_scores_for_jobs(_profile(), [_job()], [60]))[0]
    assert result["match_method"] == "hybrid_semantic"
    assert result["semantic_similarity"] == 0.8
    assert result["semantic_fit_score"] == 100
    assert result["match_score"] == 72
    assert result["rule_based_score"] == 60
    assert "not a hiring probability" in result["matching_note"]


def test_semantic_provider_failure_falls_back_without_losing_jobs(monkeypatch):
    async def no_embeddings(texts):
        return None

    monkeypatch.setattr(sm, "_fetch_embeddings", no_embeddings)
    monkeypatch.setattr(sm.settings, "semantic_matching_enabled", True)
    results = asyncio.run(sm.semantic_scores_for_jobs(_profile(), [_job(), _job("Recruiter")], [55, 42]))
    assert [item["match_score"] for item in results] == [55, 42]
    assert all(item["match_method"] == "rule_based" for item in results)
    assert all("ollama pull" in item["matching_note"] for item in results)


def test_semantic_matching_can_be_disabled(monkeypatch):
    async def unexpected_fetch(_):
        raise AssertionError("Embedding provider should not be called when disabled")

    monkeypatch.setattr(sm, "_fetch_embeddings", unexpected_fetch)
    monkeypatch.setattr(sm.settings, "semantic_matching_enabled", False)
    result = asyncio.run(sm.semantic_scores_for_jobs(_profile(), [_job()], [47]))[0]
    assert result["match_score"] == 47
    assert result["match_method"] == "rule_based"
    assert "disabled" in result["matching_note"].lower()
