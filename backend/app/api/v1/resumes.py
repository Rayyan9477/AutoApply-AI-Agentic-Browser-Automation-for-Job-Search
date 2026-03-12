"""Resume management API routes."""

from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import RecordNotFoundError
from app.schemas.resume import (
    ResumeGenerateRequest,
    ResumeListResponse,
    ResumeResponse,
    ResumeScoreRequest,
    ResumeScoreResponse,
    ResumeUploadResponse,
)
from app.services import resume as resume_service

logger = structlog.get_logger(__name__)
router = APIRouter()

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=201,
    summary="Upload a resume file",
)
async def upload_resume(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> ResumeUploadResponse:
    """Upload a PDF or DOCX resume for parsing and storage."""
    # Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Only PDF and DOCX files accepted, got '{file_ext}'",
        )

    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type: {file.content_type}",
        )

    # Validate file size by reading in chunks to avoid loading huge files into memory
    size = 0
    chunk_size = 64 * 1024  # 64KB
    while chunk := await file.read(chunk_size):
        size += len(chunk)
        if size > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Max 10MB.")
    await file.seek(0)

    return await resume_service.upload_resume(db, file)


@router.get(
    "/",
    response_model=ResumeListResponse,
    summary="List all resumes",
)
async def list_resumes(
    db: AsyncSession = Depends(get_db),
) -> ResumeListResponse:
    """List all uploaded and generated resumes."""
    return await resume_service.list_resumes(db)


@router.post(
    "/generate",
    response_model=ResumeResponse,
    status_code=201,
    summary="Generate a tailored resume",
)
async def generate_resume(
    request: ResumeGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    """Generate a job-tailored resume from a base resume.

    Uses LLM to rewrite content. Placeholder until Phase 5.
    """
    return await resume_service.generate_tailored_resume(db, request)


@router.post(
    "/{resume_id}/score",
    response_model=ResumeScoreResponse,
    summary="Score resume against a job",
)
async def score_resume(
    resume_id: str,
    request: ResumeScoreRequest,
    db: AsyncSession = Depends(get_db),
) -> ResumeScoreResponse:
    """Score a resume's ATS compatibility against a specific job."""
    return await resume_service.score_resume(db, resume_id, request)


@router.post(
    "/{resume_id}/optimize",
    response_model=ResumeResponse,
    summary="Optimize resume for ATS",
)
async def optimize_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    """Optimize a resume for ATS keyword matching.

    Placeholder: returns the existing resume unmodified until Phase 5.
    """
    resume = await resume_service.get_resume(db, resume_id)
    logger.info("resume_optimize_requested", resume_id=resume_id)
    return ResumeResponse.model_validate(resume)


@router.get(
    "/{resume_id}/download",
    summary="Download resume file",
)
async def download_resume(
    resume_id: str,
    format: str = Query(default="pdf", pattern="^(pdf|docx)$"),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Download a resume in PDF or DOCX format."""
    resume = await resume_service.get_resume(db, resume_id)

    file_path = resume.file_path_pdf if format == "pdf" else resume.file_path_docx
    if not file_path or not Path(file_path).exists():
        raise RecordNotFoundError("Resume file", resume_id)

    media_type = (
        "application/pdf" if format == "pdf" else
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=f"{resume.name}.{format}",
    )
