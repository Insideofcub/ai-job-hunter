import json
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app


def _create_job(client, token=None):
    suffix = token or uuid4().hex
    response = client.post('/api/jobs', json={
        'title': 'Talent Acquisition Specialist',
        'company': f'Analysis Test {suffix}',
        'location': 'Remote, India',
        'work_mode': 'Remote',
        'source_url': f'https://jobs.example.com/analysis/{suffix}',
        'description': (
            'Own end-to-end IT and Non-IT recruitment, candidate sourcing, Boolean search, '
            'LinkedIn Recruiter, stakeholder management, interview coordination and talent mapping. '
            'The role requests 3+ years of recruitment experience.'
        ),
        'verified_posting_time': False,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_job_analysis_endpoint_returns_grounded_fallback(monkeypatch):
    from app.database import SessionLocal
    from app.models import CandidateProfile

    async def no_ai(*args, **kwargs):
        return None

    monkeypatch.setattr('app.services.job_analysis._call_ai', no_ai)
    with TestClient(app) as client:
        profile_response = client.get('/api/profile')
        profile = profile_response.json()
        profile['full_name'] = 'Analysis Candidate'
        profile['years_experience'] = 3
        profile['resume_headline'] = 'IT & Non-IT Recruiter | Talent Acquisition Specialist'
        profile['profile_summary'] = '3+ years of end-to-end IT and Non-IT recruitment.'
        profile['skills'] = 'End-to-end recruitment, candidate sourcing, Boolean search, stakeholder management'
        assert client.put('/api/profile', json=profile).status_code == 200

        # Set selectable resume text for a more realistic profile-evidence test.
        with SessionLocal() as db:
            current = db.get(CandidateProfile, 1)
            previous = current.resume_text
            current.resume_text = 'IT recruiter with experience in Boolean search, candidate sourcing and stakeholder management.'
            db.commit()
        try:
            job = _create_job(client)
            response = client.post(f"/api/jobs/{job['id']}/analysis")
            assert response.status_code == 200, response.text
            data = response.json()
            assert data['job_id'] == job['id']
            assert 0 <= data['match_score'] <= 100
            assert data['match_method'] in {'rule_based', 'hybrid_semantic'}
            assert 0 <= data['rule_based_score'] <= 100
            assert data['score_breakdown']
            assert data['analysis_provider'] == 'Rule-based fallback'
            assert data['ai_assisted'] is False
            assert data['fit_summary']
            assert data['suggested_screening_questions']
            assert 'boolean search' in [s.lower() for s in data['skills_evidenced_by_profile']]
            assert data['verification_note']
        finally:
            with SessionLocal() as db:
                current = db.get(CandidateProfile, 1)
                current.resume_text = previous
                db.commit()


def test_job_analysis_uses_ai_advisory_fields_when_configured(monkeypatch):
    async def fake_ai(prompt, system_prompt=None):
        return json.dumps({
            'fit_summary': 'Your saved recruiter experience is relevant to this vacancy.',
            'matching_evidence': ['The saved profile describes end-to-end recruitment.'],
            'resume_points_to_emphasize': ['Candidate sourcing', 'Stakeholder management'],
            'suggested_screening_questions': ['Describe your candidate-sourcing approach.'],
            'additional_concerns': ['Salary is not visible in the captured listing.'],
        }), 'Test AI provider'

    monkeypatch.setattr('app.services.job_analysis._call_ai', fake_ai)
    with TestClient(app) as client:
        job = _create_job(client)
        response = client.post(f"/api/jobs/{job['id']}/analysis")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data['ai_assisted'] is True
        assert data['analysis_provider'] == 'Test AI provider'
        assert data['fit_summary'] == 'Your saved recruiter experience is relevant to this vacancy.'
        assert data['suggested_screening_questions'] == ['Describe your candidate-sourcing approach.']
        assert any('salary' in concern.lower() for concern in data['concerns'])


def test_job_analysis_returns_404_for_missing_job():
    with TestClient(app) as client:
        response = client.post('/api/jobs/999999999/analysis')
        assert response.status_code == 404
        assert 'Saved job not found' in response.json()['detail']
