from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["version"] == "0.6.3"


def test_profile_read_and_update():
    with TestClient(app) as client:
        response = client.get("/api/profile")
        assert response.status_code == 200
        payload = response.json()
        payload["full_name"] = "Test Candidate"
        payload["years_experience"] = 3
        response = client.put("/api/profile", json=payload)
        assert response.status_code == 200
        assert response.json()["full_name"] == "Test Candidate"


def test_profile_supports_extended_naukri_style_sections():
    with TestClient(app) as client:
        response = client.get("/api/profile")
        assert response.status_code == 200
        profile = response.json()
        profile["resume_headline"] = "IT & Non-IT Recruiter"
        profile["profile_summary"] = "3+ years in end-to-end recruitment"
        profile["employment_history_json"] = '[{"title":"Recruiter","company":"Example Co"}]'
        profile["certifications_json"] = '[{"name":"HR Management"}]'
        profile["career_profile_json"] = '{"preferred_shift":"Flexible"}'
        update = client.put("/api/profile", json=profile)
        assert update.status_code == 200, update.text
        saved = update.json()
        assert saved["resume_headline"] == "IT & Non-IT Recruiter"
        assert "Example Co" in saved["employment_history_json"]
        assert __import__("json").loads(saved["career_profile_json"]) == {"preferred_shift": "Flexible"}


def test_resume_upload_download_and_delete(tmp_path, monkeypatch):
    from io import BytesIO
    from pypdf import PdfWriter
    import app.main as main_module

    # Isolate personal files from the developer's normal local data.
    monkeypatch.setattr(main_module, "RESUME_DIR", tmp_path / "resumes")
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buffer)
    pdf_bytes = buffer.getvalue()

    with TestClient(app) as client:
        response = client.post(
            "/api/profile/resume",
            files={"file": ("candidate.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200, response.text
        upload = response.json()
        assert upload["filename"] == "candidate.pdf"
        assert upload["parse_status"] == "uploaded_no_selectable_text"

        profile = client.get("/api/profile").json()
        assert profile["resume_original_filename"] == "candidate.pdf"
        assert profile["resume_size_bytes"] == len(pdf_bytes)

        downloaded = client.get("/api/profile/resume/download")
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF-")

        deleted = client.delete("/api/profile/resume")
        assert deleted.status_code == 204
        assert client.get("/api/profile/resume/download").status_code == 404


def test_resume_upload_rejects_oversized_and_wrong_extension():
    with TestClient(app) as client:
        oversized = client.post(
            "/api/profile/resume",
            files={"file": ("resume.pdf", b"%PDF-" + b"x" * (2 * 1024 * 1024), "application/pdf")},
        )
        assert oversized.status_code == 413

        wrong_type = client.post(
            "/api/profile/resume",
            files={"file": ("resume.exe", b"MZ", "application/octet-stream")},
        )
        assert wrong_type.status_code == 415


def test_job_matches_returns_explainable_scores():
    from uuid import uuid4

    suffix = uuid4().hex
    with TestClient(app) as client:
        profile_response = client.get("/api/profile")
        profile = profile_response.json()
        profile["full_name"] = "Match Test"
        profile["target_titles"] = "IT Recruiter, Talent Acquisition Specialist"
        profile["skills"] = "Boolean search, sourcing, stakeholder management"
        profile["preferred_locations"] = "Remote, India"
        assert client.put("/api/profile", json=profile).status_code == 200

        created = client.post("/api/jobs", json={
            "title": "IT Recruiter",
            "company": f"Match Company {suffix}",
            "location": "Remote, India",
            "work_mode": "Remote",
            "source_url": f"https://example.com/jobs/{suffix}",
            "description": "Source candidates using Boolean search and stakeholder management.",
            "verified_posting_time": False,
        })
        assert created.status_code == 201, created.text
        matches = client.get("/api/jobs/matches")
        assert matches.status_code == 200, matches.text
        found = next(item for item in matches.json() if item["job"]["id"] == created.json()["id"])
        assert found["match_score"] > 0
        assert "boolean search" in found["matched_keywords"]
        assert found["reasons"]


def test_profile_photo_upload_download_delete(tmp_path, monkeypatch):
    from io import BytesIO
    from PIL import Image
    import app.main as main_module

    monkeypatch.setattr(main_module, "RESUME_DIR", tmp_path / "resumes")
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (80, 100, 200)).save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    with TestClient(app) as client:
        upload = client.post("/api/profile/photo", files={"file": ("avatar.png", image_bytes, "image/png")})
        assert upload.status_code == 200, upload.text
        assert upload.json()["filename"] == "avatar.png"
        profile = client.get("/api/profile").json()
        assert profile["photo_original_filename"] == "avatar.png"
        downloaded = client.get("/api/profile/photo")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith("image/png")
        assert downloaded.content == image_bytes
        assert client.delete("/api/profile/photo").status_code == 204
        assert client.get("/api/profile/photo").status_code == 404


def test_profile_update_rejects_invalid_json_fields():
    with TestClient(app) as client:
        profile = client.get("/api/profile").json()
        profile["employment_history_json"] = "not-json"
        response = client.put("/api/profile", json=profile)
        assert response.status_code == 422


def test_resume_suggestions_are_editable_and_not_auto_saved():
    from app.database import SessionLocal
    from app.models import CandidateProfile

    sample = (
        "Rinkoo Lodhi\nIT & Non-IT Recruiter | Talent Acquisition Specialist\n\n"
        "Professional Summary\nI am a recruitment professional with over 3 years of experience in end-to-end recruitment.\n\n"
        "Skills\nBoolean Search, LinkedIn Recruiter, Python, SQL, Data Science"
    )
    with TestClient(app) as client:
        with SessionLocal() as db:
            profile = db.get(CandidateProfile, 1)
            old_text = profile.resume_text
            old_headline = profile.resume_headline
            profile.resume_text = sample
            db.commit()
        try:
            response = client.post("/api/profile/resume/suggestions")
            assert response.status_code == 200, response.text
            data = response.json()
            assert "Recruiter" in data["headline"]
            assert "3 years" in data["profile_summary"]
            assert "Boolean Search" in data["skills"]
            assert "no profile changes have been made" in data["note"]
            with SessionLocal() as db:
                profile = db.get(CandidateProfile, 1)
                assert profile.resume_headline == old_headline
        finally:
            with SessionLocal() as db:
                profile = db.get(CandidateProfile, 1)
                profile.resume_text = old_text
                db.commit()


def test_jobspy_source_is_seeded_paused_and_requires_explicit_opt_in(monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(main_module.settings, "jobspy_enabled", False)
    with TestClient(app) as client:
        sources = client.get("/api/sources")
        assert sources.status_code == 200
        jobspy_source = next((item for item in sources.json() if item["provider"] == "jobspy"), None)
        assert jobspy_source is not None, sources.text
        assert jobspy_source["enabled"] is False

        enabled = client.patch(f"/api/sources/{jobspy_source['id']}", json={"enabled": True})
        assert enabled.status_code == 200, enabled.text
        response = client.post("/api/discovery/search", json={"query": "IT Recruiter", "hours": 168})
        assert response.status_code == 200, response.text
        status = next((item for item in response.json()["source_statuses"] if item["provider"] == "jobspy"), None)
        assert status is not None
        assert status["status"] == "skipped"
        assert "JOBSPY_ENABLED=true" in status["message"]

        paused = client.patch(f"/api/sources/{jobspy_source['id']}", json={"enabled": False})
        assert paused.status_code == 200


def test_jobspy_source_api_reports_effective_disabled_state_when_config_off(monkeypatch):
    import app.main as main_module
    from app.database import SessionLocal
    from app.models import JobSource

    monkeypatch.setattr(main_module.settings, "jobspy_enabled", False)
    with TestClient(app) as client:
        with SessionLocal() as db:
            source = db.query(JobSource).filter_by(provider="jobspy", board_id="default").first()
            assert source is not None
            # Simulate a persisted toggle enabled from a previous local session.
            source.enabled = True
            db.commit()
            source_id = source.id

        response = client.get("/api/sources")
        assert response.status_code == 200
        jobspy_source = next(item for item in response.json() if item["id"] == source_id)
        assert jobspy_source["enabled"] is False

        toggle = client.patch(f"/api/sources/{source_id}", json={"enabled": True})
        assert toggle.status_code == 200
        assert toggle.json()["enabled"] is False


def test_jobspy_source_schema_requires_default_board_token():
    from pydantic import ValidationError
    from app.schemas import JobSourceCreate

    valid = JobSourceCreate(provider="jobspy", company_name="JobSpy Schema Test", board_id="default")
    assert valid.board_id == "default"
    try:
        JobSourceCreate(provider="jobspy", company_name="Bad JobSpy Source", board_id="linkedin")
        assert False, "Expected non-default JobSpy board ID to be rejected"
    except ValidationError as exc:
        assert "use `default`" in str(exc).lower()


def test_version_and_system_readiness_do_not_expose_secrets():
    with TestClient(app) as client:
        version = client.get("/api/version")
        assert version.status_code == 200
        assert version.json()["version"] == "0.6.3"

        readiness = client.get("/api/system/readiness")
        assert readiness.status_code == 200
        payload = readiness.json()
        assert payload["status"] in {"ok", "degraded"}
        assert payload["version"] == "0.6.3"
        serialized = __import__("json").dumps(payload).lower()
        assert "openai_api_key" not in serialized
        assert "brave_search_api_key" not in serialized
        assert "adzuna_app_key" not in serialized
        assert all({"name", "status", "message"}.issubset(item) for item in payload["checks"])
