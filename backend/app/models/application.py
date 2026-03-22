"""Application tracking database model."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A job application submitted or queued for submission."""

    __tablename__ = "applications"
    __table_args__ = (
        Index("ix_application_status", "status"),
        Index("ix_application_job_id", "job_id"),
    )

    # Foreign keys
    job_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Application state
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    apply_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="review")

    # Scoring
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Documents
    cover_letter_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamps
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    browser_screenshots: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="applications")  # noqa: F821
    resume: Mapped["Resume | None"] = relationship(back_populates="applications")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, job_id={self.job_id}, status='{self.status}')>"
