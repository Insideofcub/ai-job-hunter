from datetime import datetime
import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator
import re


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    version: str


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    company: str = Field(min_length=1, max_length=250)
    location: str = "Not specified"
    work_mode: str = "Unknown"
    source_url: HttpUrl
    description: str = ""
    posted_at: datetime | None = None
    verified_posting_time: bool = False


class JobRead(BaseModel):
    id: int
    title: str
    company: str
    location: str
    work_mode: str
    source_url: str
    description: str
    posted_at: datetime | None
    verified_posting_time: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JobSourceCreate(BaseModel):
    provider: Literal["greenhouse", "lever", "arbeitnow", "remoteok", "jobicy", "himalayas", "adzuna", "brave", "jobspy"]
    company_name: str = Field(min_length=1, max_length=250)
    board_id: str = Field(min_length=1, max_length=100)

    @field_validator("company_name")
    @classmethod
    def clean_company_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Company name is required")
        return value

    @field_validator("board_id")
    @classmethod
    def validate_board_id(cls, value: str, info) -> str:
        # Only accept ATS slugs/tokens, never arbitrary URLs, to avoid SSRF.
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
            raise ValueError("Use only a board token, aggregator default, or country code—not a URL")
        provider = str(info.data.get("provider", "")).lower()
        if provider in {"arbeitnow", "remoteok", "jobicy", "himalayas", "brave", "jobspy"} and value.lower() != "default":
            raise ValueError("For this public aggregator/search provider, use `default` as the board ID")
        if provider == "adzuna" and value.lower() not in {"in", "gb", "us", "ca", "au", "de", "fr", "nl", "sg", "pl", "za", "nz", "at", "be", "br", "ch", "es", "it", "mx"}:
            raise ValueError("For Adzuna, enter a supported country code such as in, gb, us, ca, or au")
        return value.lower()


class JobSourceRead(BaseModel):
    id: int
    provider: str
    company_name: str
    board_id: str
    enabled: bool
    created_at: datetime
    last_checked_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class JobSourceToggle(BaseModel):
    enabled: bool


class SearchFilterFields(BaseModel):
    """Reusable search filters shared by Find Jobs and Run Job Agent."""
    region: Literal["global", "india", "asia", "europe", "americas", "middle_east", "africa", "oceania", "custom"] = "global"
    custom_location: str = Field(default="", max_length=200)
    work_modes: list[Literal["remote", "hybrid", "onsite", "unknown"]] = Field(
        default_factory=lambda: ["remote", "hybrid", "onsite", "unknown"]
    )
    employment_types: list[Literal["full_time", "part_time", "contract_freelance", "internship", "temporary", "unknown"]] = Field(
        default_factory=lambda: ["full_time", "part_time", "contract_freelance", "internship", "temporary", "unknown"]
    )

    @field_validator("custom_location")
    @classmethod
    def clean_custom_location(cls, value: str) -> str:
        return " ".join(value.split()).strip()

    @model_validator(mode="after")
    def validate_location_filter(self):
        if self.region == "custom" and not self.custom_location.strip():
            raise ValueError("Enter a city, country, or region for Custom location.")
        return self


class DiscoveryRequest(SearchFilterFields):
    query: str = Field(default="", max_length=2000, description="Job titles, keywords, or concise natural-language instructions")
    hours: int = Field(default=24, ge=1, le=720)
    include_unverified: bool = True


class DiscoveryItem(BaseModel):
    id: int | None = None
    title: str
    company: str
    location: str
    work_mode: str
    source_url: str
    description: str = ""
    posted_at: datetime | None = None
    verified_posting_time: bool = False
    provider: str
    source_company: str
    age_hours: float | None = None
    already_saved: bool = False
    salary_range: str = "Not disclosed"
    experience_required: str = "Not disclosed"
    required_skills: list[str] = Field(default_factory=list)
    match_score: int = 0
    rule_based_score: int | None = None
    semantic_fit_score: int | None = None
    semantic_similarity: float | None = None
    match_method: str = "rule_based"
    matching_note: str = ""
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    match_reasons: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    posting_time_evidence: str = ""
    verification_status: str = "unverified"
    qualification_reasons: list[str] = Field(default_factory=list)


class SourceCheckStatus(BaseModel):
    source_id: int
    provider: str
    company_name: str
    status: Literal["success", "empty", "error", "skipped"]
    fetched_count: int = 0
    message: str = ""


class ExcludedListing(BaseModel):
    title: str = "Untitled listing"
    company: str = "Unknown company"
    location: str = "Location not specified"
    source_url: str = ""
    provider: str = "unknown"
    reason_code: str
    reason: str
    posted_at: datetime | None = None
    posting_time_evidence: str = ""


class FilterFunnelStage(BaseModel):
    stage: str
    description: str
    input_count: int = 0
    passed_count: int = 0
    excluded_count: int = 0


class DiscoveryResponse(BaseModel):
    query: str
    hours: int
    checked_at: datetime
    sources_checked: int
    fresh_count: int
    unverified_count: int
    fresh_jobs: list[DiscoveryItem]
    unverified_jobs: list[DiscoveryItem]
    source_statuses: list[SourceCheckStatus]
    region: str = "global"
    custom_location: str = ""
    work_modes: list[str] = Field(default_factory=lambda: ["remote", "hybrid", "onsite", "unknown"])
    employment_types: list[str] = Field(default_factory=lambda: ["full_time", "part_time", "contract_freelance", "internship", "temporary", "unknown"])
    # Diagnostics explain how geographic and work preference filters affected results.
    raw_postings_count: int = 0
    unique_postings_count: int = 0
    duplicate_removed_count: int = 0
    query_filtered_out_count: int = 0
    query_matched_count: int = 0
    location_matched_count: int = 0
    work_mode_matched_count: int = 0
    employment_type_matched_count: int = 0
    location_filtered_out_count: int = 0
    work_mode_filtered_out_count: int = 0
    employment_type_filtered_out_count: int = 0
    time_window_excluded_count: int = 0
    timestamp_unverified_candidates_count: int = 0
    excluded_listing_count: int = 0
    excluded_listings_truncated: bool = False
    exclusion_reason_counts: dict[str, int] = Field(default_factory=dict)
    excluded_listings: list[ExcludedListing] = Field(default_factory=list)
    filter_funnel: list[FilterFunnelStage] = Field(default_factory=list)
    web_search_configured: bool = False
    web_search_queries: int = 0
    web_search_original_pages_verified: int = 0
    web_search_notes: list[str] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    full_name: str = ""
    years_experience: float = Field(default=0, ge=0, le=80)
    target_titles: str = ""
    skills: str = ""
    preferred_locations: str = ""
    preferred_work_modes: str = ""
    verified_facts_json: str = "{}"
    resume_headline: str = Field(default="", max_length=300)
    profile_summary: str = ""
    employment_highlights: str = ""
    employment_history_json: str = "[]"
    education_json: str = "[]"
    it_skills_json: str = "[]"
    projects_json: str = "[]"
    online_profiles_json: str = "[]"
    work_samples_json: str = "[]"
    publications_json: str = "[]"
    presentations_json: str = "[]"
    patents_json: str = "[]"
    certifications_json: str = "[]"
    career_profile_json: str = "{}"
    personal_details_json: str = "{}"
    languages_json: str = "[]"

    @field_validator(
        "verified_facts_json", "employment_history_json", "education_json", "it_skills_json",
        "projects_json", "online_profiles_json", "work_samples_json", "publications_json",
        "presentations_json", "patents_json", "certifications_json", "career_profile_json",
        "personal_details_json", "languages_json",
    )
    @classmethod
    def valid_profile_json(cls, value: str, info):
        try:
            parsed = json.loads(value or ("{}" if info.field_name in {"verified_facts_json", "career_profile_json", "personal_details_json"} else "[]"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{info.field_name} must contain valid JSON") from exc
        object_fields = {"verified_facts_json", "career_profile_json", "personal_details_json"}
        if info.field_name in object_fields and not isinstance(parsed, dict):
            raise ValueError(f"{info.field_name} must be a JSON object")
        if info.field_name not in object_fields and not isinstance(parsed, list):
            raise ValueError(f"{info.field_name} must be a JSON array")
        return json.dumps(parsed, ensure_ascii=False)


class ProfileRead(ProfileUpdate):
    id: int
    resume_original_filename: str | None = None
    resume_uploaded_at: datetime | None = None
    resume_size_bytes: int | None = None
    resume_parse_status: str = "not_uploaded"
    photo_original_filename: str | None = None
    photo_content_type: str | None = None
    photo_size_bytes: int | None = None
    photo_uploaded_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class ResumeUploadResponse(BaseModel):
    filename: str
    size_bytes: int
    uploaded_at: datetime
    parse_status: str
    extracted_characters: int
    extracted_text_preview: str = ""


class ResumeTextResponse(BaseModel):
    filename: str
    parse_status: str
    text: str


class PhotoUploadResponse(BaseModel):
    filename: str
    size_bytes: int
    content_type: str
    uploaded_at: datetime


class JobMatchRead(BaseModel):
    job: JobRead
    match_score: int
    matched_keywords: list[str]
    reasons: list[str]
    rule_based_score: int | None = None
    semantic_fit_score: int | None = None
    semantic_similarity: float | None = None
    match_method: str = "rule_based"
    matching_note: str = ""
    score_breakdown: dict[str, Any] = Field(default_factory=dict)


class JobAnalysisResponse(BaseModel):
    job_id: int
    title: str
    company: str
    source_url: str
    analysis_provider: str = "Rule-based fallback"
    ai_assisted: bool = False
    match_score: int = Field(ge=0, le=100)
    rule_based_score: int | None = Field(default=None, ge=0, le=100)
    semantic_fit_score: int | None = Field(default=None, ge=0, le=100)
    semantic_similarity: float | None = None
    match_method: str = "rule_based"
    matching_note: str = ""
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    fit_summary: str
    matching_evidence: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    skills_evidenced_by_profile: list[str] = Field(default_factory=list)
    skills_not_found_in_profile: list[str] = Field(default_factory=list)
    experience_assessment: str = "Not enough information to assess experience fit."
    location_assessment: str = "Review the original posting to confirm location and eligibility."
    resume_points_to_emphasize: list[str] = Field(default_factory=list)
    suggested_screening_questions: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    posting_time_evidence: str = "Original publication time not verified."
    verification_note: str = "Estimated profile fit only; this is not an employer assessment. Verify all details on the original listing."


APPLICATION_STATUSES = {
    "draft", "ready_for_review", "needs_manual_action", "submitted", "submitted_unconfirmed",
    "failed", "interview", "offer", "rejected", "withdrawn",
}


class ApplicationQueueJob(BaseModel):
    """A selected discovery lead to add to the application review queue."""
    job_id: int | None = None
    title: str = Field(min_length=1, max_length=250)
    company: str = Field(min_length=1, max_length=250)
    location: str = Field(default="Not specified", max_length=250)
    work_mode: str = Field(default="Unknown", max_length=50)
    source_url: HttpUrl
    description: str = Field(default="", max_length=20000)
    posted_at: datetime | None = None
    verified_posting_time: bool = False
    match_score: int = Field(default=0, ge=0, le=100)
    matched_keywords: list[str] = Field(default_factory=list, max_length=30)


class ApplicationQueueRequest(BaseModel):
    """Batch-prepare selected jobs. This endpoint never submits applications."""
    jobs: list[ApplicationQueueJob] = Field(min_length=1, max_length=50)


class ApplicationQueueItem(BaseModel):
    job_id: int | None = None
    application_id: int | None = None
    title: str
    company: str
    action: Literal["created", "reused", "failed"]
    message: str


class ApplicationQueueResponse(BaseModel):
    requested: int
    created: int
    reused: int
    saved_jobs_created: int
    failed: int
    submitted: int = 0
    items: list[ApplicationQueueItem]
    message: str


class ApplicationCreate(BaseModel):
    job_id: int | None = None
    title: str = Field(min_length=1, max_length=250)
    company: str = Field(min_length=1, max_length=250)
    location: str = "Not specified"
    work_mode: str = "Unknown"
    source_url: HttpUrl
    platform: str = "unknown"
    status: str = "ready_for_review"
    match_score: int = Field(default=0, ge=0, le=100)
    matched_keywords_json: str = "[]"
    notes: str = ""

    @field_validator("status")
    @classmethod
    def valid_application_status(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in APPLICATION_STATUSES:
            raise ValueError("Unsupported application status")
        return value

    @field_validator("matched_keywords_json")
    @classmethod
    def valid_keywords_json(cls, value: str) -> str:
        try:
            parsed = json.loads(value or "[]")
        except ValueError as exc:
            raise ValueError("matched_keywords_json must be valid JSON") from exc
        if not isinstance(parsed, list):
            raise ValueError("matched_keywords_json must be a JSON array")
        return json.dumps(parsed, ensure_ascii=False)


class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def valid_application_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().lower()
        if value not in APPLICATION_STATUSES:
            raise ValueError("Unsupported application status")
        return value


class ApplicationRead(BaseModel):
    id: int
    job_id: int | None
    title: str
    company: str
    location: str
    work_mode: str
    source_url: str
    platform: str
    status: str
    match_score: int
    matched_keywords_json: str
    answers_json: str
    notes: str
    resume_filename: str | None
    applied_at: datetime | None
    last_attempt_at: datetime | None
    submission_message: str
    confirmation_id: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScreeningAnswerRequest(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=40)

    @field_validator("questions")
    @classmethod
    def clean_questions(cls, value: list[str]) -> list[str]:
        cleaned = [" ".join(question.split())[:1200] for question in value if question and question.strip()]
        if not cleaned:
            raise ValueError("Add at least one screening question")
        return cleaned


class ScreeningAnswer(BaseModel):
    question: str
    answer: str = ""
    source: str = ""
    status: Literal["draft", "needs_review", "verified"] = "draft"
    confidence: Literal["high", "medium", "low"] = "low"


class ScreeningAnswerUpdate(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)
    status: Literal["draft", "needs_review", "verified"] = "verified"

    @field_validator("answer")
    @classmethod
    def nonblank_answer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter an answer before saving or verifying it")
        return value


class AgentRunRequest(SearchFilterFields):
    query: str = Field(default="", max_length=2000)
    hours: int = Field(default=24, ge=1, le=720)
    min_match_score: int = Field(default=35, ge=0, le=100)
    max_applications: int = Field(default=10, ge=1, le=50)
    include_unverified: bool = True
    prepare_applications: bool = True
    auto_apply: bool = False


class AgentRunResponse(BaseModel):
    started_at: datetime
    finished_at: datetime
    query: str
    hours: int = 24
    sources_checked: int
    discovered_fresh: int
    matched_jobs: int
    applications_created: int
    already_tracked: int
    browser_attempted: int = 0
    submitted: int = 0
    needs_review: int = 0
    warnings: list[str] = []
    application_ids: list[int] = []


class BrowserApplyRequest(BaseModel):
    confirm_submit: bool = False


class BrowserApplyResponse(BaseModel):
    application_id: int
    status: str
    opened_url: str
    filled_fields: list[str] = []
    missing_required: list[str] = []
    needs_human_verification: bool = False
    submitted: bool = False
    message: str


class AutomationSettingsResponse(BaseModel):
    auto_submit_enabled: bool
    supported_hosts: list[str]
    note: str


class AnalyticsResponse(BaseModel):
    total_applications: int
    submitted: int
    awaiting_review: int
    interviews: int
    offers: int
    rejected: int
    applied_last_7_days: int
    applied_last_30_days: int
    by_status: dict[str, int]
    by_platform: dict[str, int]
