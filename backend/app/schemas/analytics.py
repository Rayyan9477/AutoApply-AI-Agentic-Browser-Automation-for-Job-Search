"""Pydantic schemas for analytics and dashboard API responses."""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Top-level dashboard statistics."""

    total_jobs_found: int = 0
    total_applications: int = 0
    applications_pending: int = 0
    applications_applied: int = 0
    applications_interview: int = 0
    applications_rejected: int = 0
    applications_offer: int = 0
    avg_ats_score: float = 0.0
    total_llm_cost_usd: float = 0.0


class ApplicationFunnelData(BaseModel):
    """Application funnel stage counts."""

    stage: str
    count: int


class ATSScoreDistribution(BaseModel):
    """ATS score histogram bucket."""

    range_label: str
    count: int


class LLMUsageStats(BaseModel):
    """LLM usage aggregation."""

    provider: str
    model: str
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0


class TimelineEntry(BaseModel):
    """Daily activity timeline entry."""

    date: str
    applications_created: int = 0
    applications_applied: int = 0
    jobs_found: int = 0
