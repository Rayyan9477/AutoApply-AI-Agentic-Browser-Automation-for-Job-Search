"""Cover-letter generation service.

Mounts the previously-orphaned ``DocumentGenerator.generate_cover_letter`` behind an API
route. Uses the per-user BYO LLM client; stores the rendered path on the application.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.documents.generator import DocumentGenerator
from app.core.exceptions import GenerationError, RecordNotFoundError
from app.core.llm.factory import build_llm_client_for_user
from app.core.storage.documents import persist_generated_document
from app.models.application import Application

logger = structlog.get_logger(__name__)


async def generate_cover_letter(db: AsyncSession, application_id: str, user_id: str) -> Application:
    """Generate a cover letter for an application and persist its path."""
    app = (
        await db.execute(
            select(Application)
            .options(selectinload(Application.job), selectinload(Application.resume))
            .where(Application.id == application_id)
        )
    ).scalar_one_or_none()
    if app is None:
        raise RecordNotFoundError("Application", application_id)
    if app.job is None or app.resume is None:
        raise GenerationError("Application needs both a job and a resume for a cover letter")

    llm = await build_llm_client_for_user(db, user_id)
    generator = DocumentGenerator(llm_client=llm)
    doc = await generator.generate_cover_letter(
        resume_text=app.resume.content_text or "",
        job_description=app.job.description or "",
        company_info=app.job.company or "",
    )
    pdf_key, docx_key = await persist_generated_document(user_id, doc)
    app.cover_letter_path = pdf_key or docx_key  # column holds the storage key
    await db.commit()
    await db.refresh(app)
    logger.info("cover_letter_generated", application_id=application_id)
    return app
