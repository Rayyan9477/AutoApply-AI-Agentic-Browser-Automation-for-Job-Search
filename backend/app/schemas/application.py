"""Pydantic schemas for application-related API requests and responses."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ApplyModeEnum(StrEnum):
    """Valid apply modes for application creation."""

    AUTONOMOUS = "autonomous"
    REVIEW = "review"
    BATCH = "batch"


class StatusEnum(StrEnum):
    """Valid application status values."""

    QUEUED = "queued"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    APPLYING = "applying"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"
    WITHDRAWN = "withdrawn"
    FAILED = "failed"


class ApplicationCreate(BaseModel):
    """Request to create a single job application."""

    job_id: str
    resume_id: str | None = None
    apply_mode: ApplyModeEnum = ApplyModeEnum.REVIEW


class ApplicationBatchCreate(BaseModel):
    """Request to create multiple job applications at once."""

    job_ids: list[str] = Field(..., min_length=1)
    resume_id: str | None = None
    apply_mode: ApplyModeEnum = ApplyModeEnum.REVIEW


class ApplicationStatusUpdate(BaseModel):
    """Request to update application status."""

    status: StatusEnum
    notes: str | None = None


class ApplicationResponse(BaseModel):
    """Single application in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    resume_id: str | None = None
    status: str
    apply_mode: str
    ats_score: float | None = None
    cover_letter_path: str | None = None
    applied_at: datetime | None = None
    response_date: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationListResponse(BaseModel):
    """Paginated list of applications."""

    items: list[ApplicationResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
