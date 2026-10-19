import asyncio
import json
from types import SimpleNamespace

from app.models import Application, CandidateProfile
from app.services import ai_provider


def test_ai_provider_uses_profile_context_and_marks_generated_text_as_draft(monkeypatch):
    async def fake_call(prompt):
        assert 'LinkedIn sourcing' in prompt
        return json.dumps({"answers": [{
            "question": "Why are you interested in this role?",
            "answer": "This role fits my recruitment background in sourcing and stakeholder management.",
            "evidence": "Profile summary and skills",
        }]}), "Test model"

    monkeypatch.setattr(ai_provider, "_call_ai", fake_call)
    profile = CandidateProfile(
        id=1, full_name="Test Candidate", years_experience=3,
        resume_headline="IT Recruiter", profile_summary="Three years of recruitment experience.",
        employment_highlights="End-to-end recruitment.", skills="LinkedIn sourcing, stakeholder management",
        resume_text="IT Recruiter resume", verified_facts_json="{}", employment_history_json="[]",
        education_json="[]", it_skills_json="[]", personal_details_json="{}", career_profile_json="{}",
    )
    application = Application(id=1, title="Talent Acquisition Specialist", company="Test Company", answers_json="[]")
    answers = asyncio.run(ai_provider.draft_screening_answers_with_ai(profile, application, ["Why are you interested in this role?"]))
    assert answers[0]["answer"].startswith("This role fits")
    assert answers[0]["status"] == "draft"
    assert "Test model" in answers[0]["source"]


def test_sensitive_questions_are_not_sent_to_ai_provider(monkeypatch):
    calls = []

    async def fake_call(prompt):
        calls.append(prompt)
        return json.dumps({"answers": []}), "Test model"

    monkeypatch.setattr(ai_provider, "_call_ai", fake_call)
    profile = CandidateProfile(
        id=1, full_name="Test Candidate", years_experience=3, resume_headline="Recruiter",
        profile_summary="Recruitment experience.", employment_highlights="Sourcing.", skills="Recruitment",
        resume_text="Recruiter CV", verified_facts_json="{}", employment_history_json="[]",
        education_json="[]", it_skills_json="[]", personal_details_json="{}", career_profile_json="{}",
    )
    application = Application(id=1, title="Recruiter", company="Example", answers_json="[]")
    answers = asyncio.run(ai_provider.draft_screening_answers_with_ai(profile, application, ["Do you require visa sponsorship now or in the future?"]))
    assert calls == []
    assert answers[0]["status"] == "needs_review"
    assert answers[0]["answer"] == ""
