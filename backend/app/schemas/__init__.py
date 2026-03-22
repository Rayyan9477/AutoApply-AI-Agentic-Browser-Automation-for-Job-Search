"""Pydantic API schemas -- request/response models for all endpoints."""

from app.schemas.analytics import (
    ApplicationFunnelData,
    ATSScoreDistribution,
    DashboardStats,
    LLMUsageStats,
    TimelineEntry,
)
from app.schemas.application import (
    ApplicationBatchCreate,
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from app.schemas.job import (
    JobAnalysisResponse,
    JobListingResponse,
    JobListResponse,
    JobSearchRequest,
)
from app.schemas.resume import (
    ResumeGenerateRequest,
    ResumeListResponse,
    ResumeResponse,
    ResumeScoreRequest,
    ResumeScoreResponse,
    ResumeUploadResponse,
)
from app.schemas.settings import LLMProviderStatus, SettingsResponse, SettingsUpdate

__all__ = [
    "ATSScoreDistribution",
    # application
    "ApplicationBatchCreate",
    "ApplicationCreate",
    # analytics
    "ApplicationFunnelData",
    "ApplicationListResponse",
    "ApplicationResponse",
    "ApplicationStatusUpdate",
    "DashboardStats",
    # job
    "JobAnalysisResponse",
    "JobListResponse",
    "JobListingResponse",
    "JobSearchRequest",
    # settings
    "LLMProviderStatus",
    "LLMUsageStats",
    # resume
    "ResumeGenerateRequest",
    "ResumeListResponse",
    "ResumeResponse",
    "ResumeScoreRequest",
    "ResumeScoreResponse",
    "ResumeUploadResponse",
    "SettingsResponse",
    "SettingsUpdate",
    "TimelineEntry",
]
