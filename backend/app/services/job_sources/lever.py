from datetime import datetime, timezone
from urllib.parse import quote
import httpx

from .base import NormalizedPosting, infer_work_mode


def _parse_created_at(value) -> datetime | None:
    if value is None:
        return None
    try:
        # Lever exposes createdAt as Unix epoch milliseconds.
        return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


async def fetch_lever(client: httpx.AsyncClient, board_id: str, company_name: str) -> list[NormalizedPosting]:
    url = f"https://api.lever.co/v0/postings/{quote(board_id, safe='')}"
    response = await client.get(url, params={"mode": "json", "limit": 100})
    response.raise_for_status()
    payload = response.json()
    postings = payload if isinstance(payload, list) else []
    results: list[NormalizedPosting] = []
    for posting in postings:
        title = str(posting.get("text") or "").strip()
        # Hosted posting page is the best default target; applyUrl is retained
        # by the ATS page itself and may change independently.
        source_url = str(posting.get("hostedUrl") or posting.get("applyUrl") or "").strip()
        if not title or not source_url.startswith("https://"):
            continue
        categories = posting.get("categories") or {}
        location = str(categories.get("location") or ", ".join(categories.get("allLocations") or []) or "Not specified")
        description = str(posting.get("descriptionPlain") or posting.get("descriptionBodyPlain") or posting.get("openingPlain") or "")
        posted_at = _parse_created_at(posting.get("createdAt"))
        work_mode = infer_work_mode(location, description, posting.get("workplaceType"))
        results.append(NormalizedPosting(
            title=title,
            company=company_name,
            location=location,
            work_mode=work_mode,
            source_url=source_url,
            description=description[:20000],
            posted_at=posted_at,
            verified_posting_time=posted_at is not None,
            provider="lever",
            source_company=company_name,
        ))
    return results
