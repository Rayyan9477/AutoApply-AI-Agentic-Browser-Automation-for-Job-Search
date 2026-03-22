"""Resume database model."""

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A resume document (base or tailored)."""

    __tablename__ = "resumes"
    __table_args__ = (Index("ix_resume_type", "type"),)

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="base")

    # Lineage (tailored resumes link to their base)
    base_resume_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Template used
    template_id: Mapped[str] = mapped_column(String(50), nullable=False, default="modern")

    # File paths
    file_path_pdf: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path_docx: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Scoring
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Extracted text for search and analysis
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    base_resume: Mapped["Resume | None"] = relationship(
        remote_side="Resume.id",
        backref="tailored_versions",
    )
    applications: Mapped[list["Application"]] = relationship(  # noqa: F821
        back_populates="resume",
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, name='{self.name}', type='{self.type}')>"
