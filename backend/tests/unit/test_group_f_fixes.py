"""Group F remediation regression tests: per-tenant document storage + pre-apply ATS gate."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.storage import documents
from app.core.storage.local import LocalFileStorage
from app.workers import tasks

# --- F2: generated documents land in per-tenant storage ---------------------


class TestPersistGeneratedDocument:
    async def test_moves_bytes_to_storage_and_removes_temp(self, tmp_path):
        pdf = tmp_path / "a.pdf"
        pdf.write_bytes(b"PDFDATA")
        docx = tmp_path / "a.docx"
        docx.write_bytes(b"DOCXDATA")
        doc = MagicMock(type="resume", document_id="doc1", pdf_path=str(pdf), docx_path=str(docx))
        store = LocalFileStorage(str(tmp_path / "store"), "sig-secret")

        with patch.object(documents, "get_storage", return_value=store):
            pdf_key, docx_key = await documents.persist_generated_document("u1", doc)

        assert pdf_key == "users/u1/resumes/doc1.pdf"  # per-tenant prefixed key
        assert docx_key == "users/u1/resumes/doc1.docx"
        assert await store.get(pdf_key) == b"PDFDATA"  # bytes moved into storage
        assert await store.get(docx_key) == b"DOCXDATA"
        assert not pdf.exists() and not docx.exists()  # temp render files removed

    async def test_cover_letter_uses_cover_letter_prefix(self, tmp_path):
        pdf = tmp_path / "c.pdf"
        pdf.write_bytes(b"CL")
        doc = MagicMock(type="cover_letter", document_id="cl1", pdf_path=str(pdf), docx_path=None)
        store = LocalFileStorage(str(tmp_path / "store"), "sig-secret")

        with patch.object(documents, "get_storage", return_value=store):
            pdf_key, docx_key = await documents.persist_generated_document("u1", doc)

        assert pdf_key == "users/u1/cover_letters/cl1.pdf"
        assert docx_key is None


# --- F4: pre-apply ATS gate -------------------------------------------------


class TestAtsGate:
    async def test_no_resume_passes(self, db_session):
        ok, score = await tasks._ats_gate_ok(db_session, MagicMock(resume_id=None))
        assert ok is True and score == 0.0

    async def test_below_threshold_blocks(self, db_session):
        app = MagicMock(resume_id="r1", job_id="j1", id="a1")
        with patch(
            "app.services.resume.score_resume",
            new=AsyncMock(return_value=MagicMock(overall_score=0.30)),
        ):
            ok, score = await tasks._ats_gate_ok(db_session, app)
        assert ok is False and score == 0.30

    async def test_zero_score_unavailable_does_not_block(self, db_session):
        app = MagicMock(resume_id="r1", job_id="j1", id="a1")
        with patch(
            "app.services.resume.score_resume",
            new=AsyncMock(return_value=MagicMock(overall_score=0.0)),
        ):
            ok, _ = await tasks._ats_gate_ok(db_session, app)
        assert ok is True  # 0.0 means scoring was unavailable — don't block

    async def test_above_threshold_passes(self, db_session):
        app = MagicMock(resume_id="r1", job_id="j1", id="a1")
        with patch(
            "app.services.resume.score_resume",
            new=AsyncMock(return_value=MagicMock(overall_score=0.90)),
        ):
            ok, score = await tasks._ats_gate_ok(db_session, app)
        assert ok is True and score == 0.90

    async def test_scoring_exception_does_not_block(self, db_session):
        app = MagicMock(resume_id="r1", job_id="j1", id="a1")
        with patch(
            "app.services.resume.score_resume", new=AsyncMock(side_effect=RuntimeError("boom"))
        ):
            ok, _ = await tasks._ats_gate_ok(db_session, app)
        assert ok is True  # scoring failure must not block the apply
