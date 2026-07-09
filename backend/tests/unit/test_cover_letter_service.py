"""Phase 2.2: cover-letter generation service (mounts the previously-orphaned generator)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import GenerationError
from app.models.application import Application
from app.models.enums import ApplyMode
from app.models.job import Job
from app.models.resume import Resume
from app.services import cover_letter as cl
from tests.conftest import TEST_USER_ID


async def _seed(db, *, with_resume: bool) -> Application:
    job = Job(
        user_id=TEST_USER_ID, platform="linkedin", platform_job_id="j1",
        title="Engineer", company="Acme", url="https://x", description="Python role",
    )
    db.add(job)
    await db.flush()
    resume_id = None
    if with_resume:
        resume = Resume(
            user_id=TEST_USER_ID, name="r", type="base",
            template_id="modern", content_text="Python developer",
        )
        db.add(resume)
        await db.flush()
        resume_id = resume.id
    app = Application(
        user_id=TEST_USER_ID, job_id=job.id, resume_id=resume_id,
        status="queued", apply_mode=ApplyMode.REVIEW,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


class TestGenerateCoverLetter:
    async def test_generates_and_stores_path(self, db_session):
        app = await _seed(db_session, with_resume=True)
        fake_gen = MagicMock()
        fake_gen.generate_cover_letter = AsyncMock(
            return_value=MagicMock(pdf_path="/tmp/cl.pdf", docx_path=None)
        )
        key = "users/u/cover_letters/cl.pdf"
        with patch.object(cl, "DocumentGenerator", return_value=fake_gen), patch.object(
            cl, "persist_generated_document", new=AsyncMock(return_value=(key, None))
        ):
            result = await cl.generate_cover_letter(db_session, app.id, TEST_USER_ID)
        assert result.cover_letter_path == key  # column holds the storage key
        fake_gen.generate_cover_letter.assert_awaited_once()

    async def test_missing_resume_raises(self, db_session):
        app = await _seed(db_session, with_resume=False)
        with pytest.raises(GenerationError):
            await cl.generate_cover_letter(db_session, app.id, TEST_USER_ID)
