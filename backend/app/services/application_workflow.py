import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException
from ..config import settings
from ..models import Application, CandidateProfile

SUPPORTED_APPLICATION_HOSTS = [
    "boards.greenhouse.io", "job-boards.greenhouse.io", "boards.eu.greenhouse.io",
    "job-boards.eu.greenhouse.io", "jobs.lever.co", "jobs.eu.lever.co",
]


def parse_json(value: str | None, expected_type, default):
    try:
        parsed = json.loads(value or "")
        return parsed if isinstance(parsed, expected_type) else default
    except (ValueError, TypeError):
        return default


def profile_source_text(profile: CandidateProfile) -> str:
    chunks = [
        profile.full_name, profile.resume_headline, profile.profile_summary,
        profile.employment_highlights, profile.skills, profile.resume_text,
    ]
    for field in ("employment_history_json", "education_json", "it_skills_json", "projects_json", "certifications_json"):
        parsed = parse_json(getattr(profile, field, ""), list, [])
        chunks.extend(str(value) for row in parsed for value in row.values())
    return "\n".join(str(x).strip() for x in chunks if x).strip()


def platform_from_url(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("greenhouse.io"):
        return "greenhouse"
    if host.endswith("lever.co"):
        return "lever"
    return host or "unknown"


def host_is_supported(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == allowed or host.endswith("." + allowed) for allowed in SUPPORTED_APPLICATION_HOSTS)


def _verified_fact_map(profile: CandidateProfile) -> dict[str, str]:
    facts = parse_json(profile.verified_facts_json, dict, {})
    personal = parse_json(profile.personal_details_json, dict, {})
    career = parse_json(profile.career_profile_json, dict, {})
    # Explicitly marked fields are the only allowed source for sensitive or legal answers.
    merged = {}
    for source in (career, personal, facts):
        for key, value in source.items():
            if value is not None and str(value).strip():
                merged[str(key).lower().replace(" ", "_")] = str(value).strip()
    return merged


def _fact_for_question(question: str, facts: dict[str, str]) -> tuple[str, str] | None:
    q = question.lower()
    mappings = [
        (("notice period", "how soon can you join", "when can you join", "availability to start"), ("notice_period", "availability_to_start")),
        (("expected salary", "desired salary", "salary expectation", "compensation expectation", "expected ctc"), ("expected_salary", "preferred_annual_salary", "desired_salary")),
        (("current salary", "current ctc", "current compensation"), ("current_salary", "current_ctc")),
        (("work authorization", "authorized to work", "legally authorized", "work permit", "visa status"), ("work_authorization", "work_permit", "visa_status")),
        (("visa sponsorship", "require sponsorship", "sponsorship now", "sponsorship in the future"), ("visa_sponsorship", "requires_sponsorship")),
        (("non-compete", "non compete", "restrictive covenant", "conflict of interest"), ("non_compete", "restrictive_covenant", "conflict_of_interest")),
        (("willing to relocate", "relocation", "open to relocation"), ("willing_to_relocate", "relocation_preference")),
        (("gender",), ("gender",)),
        (("disability",), ("disability_status", "diversity_disability_status")),
        (("engage with mastercard employees", "negotiate or influence", "sign commercial contracts", "influence and/or sign commercial contracts", "negotiate commercial contracts"), ("mastercard_contract_engagement", "engage_mastercard_contracts")),
        (("related to anyone who has the authority", "related to someone who has the authority", "related to anyone with authority", "related to a person who can influence"), ("related_to_mastercard_contract_authority",)),
        (("government office or agency", "agency that has oversight over mastercard", "oversight over mastercard"), ("government_oversight_employment",)),
        (("related to someone who is an employee of a government", "related to a government employee", "related to someone employed by a government"), ("related_to_government_oversight_employee",)),
        (("close personal relationship with a current mastercard employee", "personal relationship with a mastercard employee"), ("mastercard_employee_relationship",)),
        (("worked for mastercard", "previously worked for this company", "previous employment at"), ("previous_employment", "worked_for_company")),
    ]
    for triggers, keys in mappings:
        if any(trigger in q for trigger in triggers):
            for key in keys:
                if facts.get(key):
                    return facts[key], f"Verified profile field: {key}"
            return "", "This needs your confirmation; the profile has no verified answer for this legal or personal declaration."
    return None


def draft_screening_answers(profile: CandidateProfile, application: Application, questions: list[str]) -> list[dict]:
    """Create transparent, resume-grounded drafts; do not guess legal or unknown facts."""
    facts = _verified_fact_map(profile)
    skills = [x.strip() for x in re.split(r"[,;\n]", profile.skills or "") if x.strip()]
    skills_json = parse_json(profile.it_skills_json, list, [])
    for row in skills_json:
        if isinstance(row, dict):
            val = row.get("skill") or row.get("name") or row.get("title")
            if val and val not in skills:
                skills.append(str(val))
    skills = skills[:20]
    summary = (profile.profile_summary or "").strip()
    employment = (profile.employment_highlights or "").strip()
    resume = (profile.resume_text or "").strip()
    experience = float(profile.years_experience or 0)
    headline = (profile.resume_headline or profile.target_titles or "").strip()
    answers = []

    for question in questions:
        q = question.lower()
        answer = ""
        source = ""
        status = "draft"
        confidence = "medium"
        verified = _fact_for_question(question, facts)
        if verified is not None:
            answer, source = verified
            status = "verified" if answer else "needs_review"
            confidence = "high" if answer else "low"
        elif any(term in q for term in ("tell us about yourself", "introduce yourself", "professional summary", "tell me about yourself")):
            answer = summary or " ".join(part for part in (headline, employment) if part)
            source = "Profile summary/headline and employment highlights"
            confidence = "high" if summary else "medium"
            if not answer:
                answer = ""
                status = "needs_review"
        elif any(term in q for term in ("how many years", "years of experience", "total experience", "relevant experience")):
            if experience > 0:
                answer = f"{experience:g} years"
                source = "Candidate profile: years_experience"
                confidence = "high"
            elif summary:
                answer = summary[:700]
                source = "Profile summary"
                status = "draft"
            else:
                status = "needs_review"
                source = "No experience duration is saved in the profile."
        elif any(term in q for term in ("key skills", "technical skills", "skills do you have", "list your skills", "relevant skills")):
            if skills:
                answer = ", ".join(skills)
                source = "Saved profile skills and IT skills"
                confidence = "high"
            elif resume:
                answer = resume[:700]
                source = "Extracted resume text; review and shorten before submission"
                confidence = "low"
            else:
                status = "needs_review"
                source = "No skills are saved in the profile."
        elif any(term in q for term in ("why are you interested", "why do you want", "why this role", "why this position", "why join")):
            if headline or summary or skills:
                skill_line = ", ".join(skills[:5])
                answer = f"I’m interested in the {application.title} opportunity at {application.company} because it aligns with my background in {headline or 'the relevant field'}. "
                if skill_line:
                    answer += f"My profile highlights experience and skills including {skill_line}. "
                if summary:
                    answer += summary[:450]
                else:
                    answer += "I would welcome the opportunity to learn more about the team’s needs and how my experience could contribute."
                source = "Generated only from job title/company and saved profile fields"
                confidence = "medium"
            else:
                status = "needs_review"
                source = "Add a profile summary/headline before drafting this answer."
        elif any(term in q for term in ("describe your experience", "tell us about your experience", "experience relevant to", "experience with", "tell us about your background", "what makes you a good fit", "why should we hire")):
            parts = [x for x in (summary, employment, headline) if x]
            if parts:
                answer = "\n\n".join(parts)[:1400]
                source = "Profile summary, headline, employment highlights"
                confidence = "medium"
            else:
                status = "needs_review"
                source = "No relevant background text is saved."
        elif "linkedin" in q or "professional profile url" in q:
            profiles = parse_json(profile.online_profiles_json, list, [])
            candidate = next((row for row in profiles if isinstance(row, dict) and "linkedin" in str(row.get("url", "") + row.get("name", "")).lower()), None)
            if candidate:
                answer = str(candidate.get("url") or "")
                source = "Saved online profile link"
                confidence = "high"
            else:
                status = "needs_review"
                source = "No LinkedIn/profile URL is saved."
        elif any(term in q for term in ("cover letter", "message to the hiring manager", "additional information")):
            if summary or headline or skills:
                answer = f"Dear Hiring Team,\n\nI am interested in the {application.title} position at {application.company}. My profile describes me as {headline or 'a candidate with relevant experience'}. "
                if summary:
                    answer += summary[:600] + " "
                if skills:
                    answer += f"Relevant skills in my profile include {', '.join(skills[:6])}. "
                answer += "I would appreciate the opportunity to discuss how my experience matches the role.\n\nBest regards"
                source = "Draft from job metadata and saved profile; review before sending"
                confidence = "medium"
            else:
                status = "needs_review"
                source = "Profile details are insufficient for a grounded draft."
        else:
            status = "needs_review"
            source = "No safe matching rule; answer manually or add a verified fact."

        answers.append({
            "question": question,
            "answer": answer,
            "source": source,
            "status": status,
            "confidence": confidence,
        })
    return answers


def safe_resume_path(profile: CandidateProfile, resume_dir: Path) -> Path | None:
    key = profile.resume_storage_key
    if not key or not re.fullmatch(r"[a-f0-9]{32}\.(pdf|doc|docx|rtf)", key):
        return None
    path = (resume_dir / key).resolve()
    if path.parent != resume_dir.resolve() or not path.is_file():
        return None
    return path


def detect_email_phone(text: str, facts: dict[str, str]) -> tuple[str, str]:
    email = next((facts[k] for k in ("email", "email_address") if facts.get(k)), "")
    phone = next((facts[k] for k in ("phone", "phone_number", "mobile") if facts.get(k)), "")
    if not email:
        match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
        email = match.group(0) if match else ""
    if not phone:
        match = re.search(r"(?:\+?\d[\d ()-]{7,}\d)", text)
        phone = match.group(0).strip() if match else ""
    return email, phone


def automation_disabled_message() -> str:
    return "Browser automation is disabled unless AUTO_SUBMIT_ENABLED=true is explicitly set in backend/.env and the backend is restarted."
