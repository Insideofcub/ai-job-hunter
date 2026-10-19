from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote
import httpx

from .base import NormalizedPosting, infer_work_mode


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)


def html_to_text(value: str | None) -> str:
    if not value:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(value)
        return unescape(" ".join(parser.parts))
    except Exception:
        return unescape(value)


def _parse_posted_at(job: dict) -> datetime | None:
    # updated_at is deliberately excluded: a modification time is not proof
    # of the original publication time.
    for field in ("first_published_at", "published_at", "created_at", "date_posted"):
        value = job.get(field)
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
    return None


async def fetch_greenhouse(client: httpx.AsyncClient, board_id: str, company_name: str) -> list[NormalizedPosting]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{quote(board_id, safe='')}/jobs"
    response = await client.get(url, params={"content": "true"})
    response.raise_for_status()
    payload = response.json()
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    results: list[NormalizedPosting] = []
    for job in jobs:
        title = str(job.get("title") or "").strip()
        source_url = str(job.get("absolute_url") or "").strip()
        if not title or not source_url.startswith("https://"):
            continue
        location_data = job.get("location") or {}
        location = location_data.get("name") if isinstance(location_data, dict) else str(location_data)
        description = html_to_text(job.get("content"))
        posted_at = _parse_posted_at(job)
        results.append(NormalizedPosting(
            title=title,
            company=company_name,
            location=location or "Not specified",
            work_mode=infer_work_mode(location or "", description),
            source_url=source_url,
            description=description[:20000],
            posted_at=posted_at,
            verified_posting_time=posted_at is not None,
            provider="greenhouse",
            source_company=company_name,
        ))
    return results
