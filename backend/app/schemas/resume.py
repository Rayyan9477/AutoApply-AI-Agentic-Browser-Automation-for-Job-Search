"""Pydantic schemas for resume-related API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ResumeOptimizeRequest(BaseModel):
    """Request to optimize a resume for ATS compatibility."""

    job_id: str | None = None


class ResumeResponse(BaseModel):
    """Single resume in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    template_id: str
    base_resume_id: str | None = None
    job_id: str | None = None
    has_pdf: bool = False
    has_docx: bool = False
    ats_score: float | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _convert_paths_to_flags(cls, data: Any) -> Any:
        """Convert internal file paths to boolean flags to avoid leaking server paths."""
        if hasattr(data, "__dict__"):
            # ORM model — check attributes
            return {
                **{k: v for k, v in data.__dict__.items() if not k.startswith("_")},
                "has_pdf": bool(getattr(data, "file_path_pdf", None)),
                "has_docx": bool(getattr(data, "file_path_docx", None)),
            }
        if isinstance(data, dict):
            return {
                **data,
                "has_pdf": bool(data.get("file_path_pdf")),
                "has_docx": bool(data.get("file_path_docx")),
            }
        return data


class ResumeListResponse(BaseModel):
    """Paginated list of resumes."""

    items: list[ResumeResponse]
    total: int
