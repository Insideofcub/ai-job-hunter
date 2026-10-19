"""Optional local embedding-based job matching with transparent fallback.

The embedding similarity is a ranking signal, not a probability of being hired.
Rule-based evidence remains the majority contributor to the final score.
"""
from __future__ import annotations

import json
import math
from typing import Any, Sequence

import httpx

from ..config import settings
from ..models import CandidateProfile, Job

# Similarities are model-dependent. These bounds are an intentionally rough
# ranking calibration for nomic-embed-text, not a universal probability scale.
_SIMILARITY_FLOOR = 0.20
_SIMILARITY_CEILING = 0.70
_RULE_WEIGHT = 0.70
_SEMANTIC_WEIGHT = 0.30


def _json_list(value: str | None, limit: int = 20) -> list[Any]:
    try:
        parsed = json.loads(value or "[]")
        return parsed[:limit] if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


def profile_embedding_text(profile: CandidateProfile) -> str:
    """Build role-focused profile context; do not include sensitive personal fields."""
    parts = [
        f"Target roles: {profile.target_titles or ''}",
        f"Resume headline: {profile.resume_headline or ''}",
        f"Professional summary: {profile.profile_summary or ''}",
        f"Years of relevant experience: {profile.years_experience or 0}",
        f"Skills: {profile.skills or ''}",
        f"Employment highlights: {profile.employment_highlights or ''}",
        f"Employment history: {json.dumps(_json_list(profile.employment_history_json, 8), ensure_ascii=False)}",
        f"IT skills: {json.dumps(_json_list(profile.it_skills_json, 35), ensure_ascii=False)}",
        f"Certifications: {json.dumps(_json_list(profile.certifications_json, 15), ensure_ascii=False)}",
        f"Resume text: {(profile.resume_text or '')[:6500]}",
    ]
    return "\n".join(part for part in parts if part.strip())[:10000]


def job_embedding_text(job: Any) -> str:
    return "\n".join([
        f"Job title: {getattr(job, 'title', '') or ''}",
        f"Company: {getattr(job, 'company', '') or ''}",
        f"Location: {getattr(job, 'location', '') or ''}",
        f"Work mode: {getattr(job, 'work_mode', '') or ''}",
        f"Job description and requirements: {(getattr(job, 'description', '') or '')[:4000]}",
    ])[:5000]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float | None:
    if not left or not right or len(left) != len(right):
        return None
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(a) ** 2 for a in left))
    right_norm = math.sqrt(sum(float(b) ** 2 for b in right))
    if left_norm == 0 or right_norm == 0:
        return None
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def calibrated_semantic_fit(similarity: float) -> int:
    """Map cosine similarity to a ranking signal, not a hiring probability."""
    scale = (similarity - _SIMILARITY_FLOOR) / (_SIMILARITY_CEILING - _SIMILARITY_FLOOR)
    return round(100 * max(0.0, min(1.0, scale)))


def blend_match_scores(rule_score: int, semantic_fit_score: int) -> int:
    rule = max(0, min(100, int(rule_score)))
    semantic = max(0, min(100, int(semantic_fit_score)))
    return max(0, min(100, round(_RULE_WEIGHT * rule + _SEMANTIC_WEIGHT * semantic)))


async def _fetch_embeddings(texts: list[str]) -> list[list[float]] | None:
    if not settings.semantic_matching_enabled or not texts:
        return None
    url = settings.ollama_base_url.rstrip("/") + "/api/embed"
    timeout = httpx.Timeout(18.0, connect=2.5)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json={
                "model": settings.ollama_embedding_model,
                "input": texts,
                "truncate": True,
            })
            response.raise_for_status()
            payload = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            return None
        vectors: list[list[float]] = []
        for vector in embeddings:
            if not isinstance(vector, list) or not vector:
                return None
            parsed = [float(value) for value in vector]
            if any(not math.isfinite(value) for value in parsed):
                return None
            vectors.append(parsed)
        if len({len(vector) for vector in vectors}) != 1:
            return None
        return vectors
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        # Ollama may be off or the embedding model may not be pulled. Keep search
        # available with the rule-based score; the UI exposes which method ran.
        return None


async def semantic_scores_for_jobs(
    profile: CandidateProfile,
    jobs: list[Any],
    rule_scores: list[int],
) -> list[dict[str, Any]]:
    """Return one score record per job; embedding failures degrade to rule baseline.

    The candidate profile and each job are embedded in one batch. This is intended
    for normal local searches (up to 80 jobs per request), not large-corpus indexing.
    """
    if len(jobs) != len(rule_scores):
        raise ValueError("jobs and rule_scores must have the same length")

    def fallback(index: int, note: str) -> dict[str, Any]:
        score = max(0, min(100, int(rule_scores[index])))
        return {
            "rule_based_score": score,
            "semantic_similarity": None,
            "semantic_fit_score": None,
            "match_score": score,
            "match_method": "rule_based",
            "matching_note": note,
        }

    if not jobs:
        return []
    if not settings.semantic_matching_enabled:
        return [fallback(i, "Semantic embeddings are disabled in backend/.env; using the explainable rule-based score.") for i in range(len(jobs))]

    profile_text = profile_embedding_text(profile)
    if len(profile_text.strip()) < 20:
        return [fallback(i, "Add resume text or profile details to enable semantic matching.") for i in range(len(jobs))]

    # A small cap protects local machines from large payloads; remaining rows use
    # the rule-based score and are explicitly labelled accordingly.
    max_semantic_jobs = 80
    docs = [job_embedding_text(job) for job in jobs[:max_semantic_jobs]]
    vectors = await _fetch_embeddings(["search_query: " + profile_text, *["search_document: " + doc for doc in docs]])
    if not vectors:
        return [fallback(i, f"Local embedding model '{settings.ollama_embedding_model}' is unavailable; using rule-based scoring. Run `ollama pull {settings.ollama_embedding_model}` and restart the backend to enable semantic ranking.") for i in range(len(jobs))]

    results = [fallback(i, "Semantic batch cap reached; using the rule-based score for this item.") for i in range(len(jobs))]
    profile_vector = vectors[0]
    for index, job_vector in enumerate(vectors[1:]):
        similarity = cosine_similarity(profile_vector, job_vector)
        if similarity is None:
            continue
        semantic_fit = calibrated_semantic_fit(similarity)
        rule_score = max(0, min(100, int(rule_scores[index])))
        results[index] = {
            "rule_based_score": rule_score,
            "semantic_similarity": round(similarity, 4),
            "semantic_fit_score": semantic_fit,
            "match_score": blend_match_scores(rule_score, semantic_fit),
            "match_method": "hybrid_semantic",
            "matching_note": "Hybrid estimate: 70% explainable rule-based evidence + 30% local embedding similarity. The score is a ranking aid, not a hiring probability.",
        }
    return results
