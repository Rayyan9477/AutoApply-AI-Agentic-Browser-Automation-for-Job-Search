"""Pydantic schemas for job-related API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobSearchRequest(BaseModel):
    """Request body for multi-platform job search."""

    query: str = Field(..., min_length=1, max_length=500)
    location: str = ""
    platforms: list[str] = Field(default_factory=lambda: ["linkedin", "indeed", "glassdoor"])
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=20, ge=1, le=100)


class JobListingResponse(BaseModel):
    """Single job listing in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    platform_job_id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    salary_range: str | None = None
    job_type: str | None = None
    remote: bool = False
    posted_date: datetime | None = None
    experience_level: str | None = None
    match_score: float | None = None
    skills_required: dict | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    """Paginated list of job listings."""

    items: list[JobListingResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class JobAnalysisResponse(BaseModel):
    """Response for job analysis endpoint."""

    job_id: str
    match_score: float
    skill_match: float
    keyword_match: float
    missing_skills: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
