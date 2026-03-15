"""Pydantic schemas for resume-related API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeUploadResponse(BaseModel):
    """Response after uploading a resume file."""

    id: str
    name: str
    file_format: str
    word_count: int
    skills_detected: list[str] = Field(default_factory=list)


class ResumeGenerateRequest(BaseModel):
    """Request to generate a tailored resume."""

    base_resume_id: str
    job_id: str
    template_id: str = "modern"
    output_formats: list[str] = Field(default_factory=lambda: ["pdf", "docx"])


class ResumeScoreRequest(BaseModel):
    """Request to score a resume against a job."""

    job_id: str


class ResumeScoreResponse(BaseModel):
    """Response with ATS score details."""

    resume_id: str
    job_id: str
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    keyword_score: float
    missing_skills: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ResumeResponse(BaseModel):
    """Single resume in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    template_id: str
    base_resume_id: str | None = None
    job_id: str | None = None
    file_path_pdf: str | None = None
    file_path_docx: str | None = None
    ats_score: float | None = None
    created_at: datetime
    updated_at: datetime


class ResumeListResponse(BaseModel):
    """Paginated list of resumes."""

    items: list[ResumeResponse]
    total: int
