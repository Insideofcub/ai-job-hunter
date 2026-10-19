"""Keep integration tests deterministic and isolated from the user's local data.

The test process always gets its own temporary SQLite database before app modules are
imported. Tests must never read or mutate the developer's configured .env database.
Tests that need connector behavior monkeypatch functions explicitly or use MockTransport.
"""

import os
import tempfile
from pathlib import Path

import pytest

# conftest is imported before test modules, including ``from app.main import app``.
# Environment variables override pydantic-settings' .env values, so this prevents the
# test suite from mutating backend/ai_job_hunter.db or any user-configured database.
_test_db_dir = Path(tempfile.mkdtemp(prefix="ai-job-hunter-tests-"))
_test_db_path = (_test_db_dir / "test.sqlite3").as_posix()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["APP_ENV"] = "test"


@pytest.fixture(autouse=True)
def disable_live_job_source_calls(monkeypatch):
    from app import main

    async def empty_fetch_source(client, source):
        return []

    async def empty_himalayas(client, board_id, query, company_name="Himalayas"):
        return []

    async def empty_adzuna(client, country_code, query, company_name="Adzuna"):
        return []

    async def empty_brave(**kwargs):
        return [], {
            "queries_planned": 0,
            "queries_succeeded": 0,
            "unique_candidates_checked": 0,
            "original_pages_verified": 0,
            "errors": [],
            "portal_breakdown": [],
        }

    monkeypatch.setattr(main, "_fetch_source", empty_fetch_source)
    monkeypatch.setattr(main, "fetch_himalayas", empty_himalayas)
    monkeypatch.setattr(main, "fetch_adzuna", empty_adzuna)
    monkeypatch.setattr(main, "fetch_brave_web_research", empty_brave)
