"""Interview session HTTP endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import HttpUrl
from starlette.concurrency import run_in_threadpool

from src.api.dependencies import get_interview_service
from src.api.schemas import InterviewSessionResponse, SubmitAnswerRequest
from src.config import MAX_RESUME_UPLOAD_BYTES, UPLOAD_DIR
from src.services.interview_service import (
    InterviewService,
    InterviewSessionNotFoundError,
    InterviewSessionNotWaitingError,
)


router = APIRouter(prefix="/interviews", tags=["interviews"])
ALLOWED_PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}


def _raise_graph_http_error(exc: Exception) -> None:
    if isinstance(exc, InterviewSessionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, InterviewSessionNotWaitingError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.post(
    "/start",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_interview(
    resume_file: Annotated[UploadFile, File(description="지원자 이력서 PDF")],
    job_posting_url: Annotated[HttpUrl, Form(description="사람인 또는 원티드 공고 URL")],
    service: Annotated[InterviewService, Depends(get_interview_service)],
) -> dict:
    filename = resume_file.filename or ""
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="PDF 파일만 업로드할 수 있습니다.",
        )
    if resume_file.content_type not in ALLOWED_PDF_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="지원하지 않는 파일 형식입니다.",
        )

    content = await resume_file.read(MAX_RESUME_UPLOAD_BYTES + 1)
    await resume_file.close()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="업로드한 PDF가 비어 있습니다.",
        )
    if len(content) > MAX_RESUME_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="이력서 PDF는 10MB 이하만 업로드할 수 있습니다.",
        )
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="유효한 PDF 파일이 아닙니다.",
        )

    session_id = str(uuid.uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temporary_path = UPLOAD_DIR / f"{session_id}.pdf"
    try:
        temporary_path.write_bytes(content)
        return await run_in_threadpool(
            service.start_interview,
            temporary_path,
            str(job_posting_url),
            session_id=session_id,
        )
    except Exception as exc:
        _raise_graph_http_error(exc)
        raise
    finally:
        temporary_path.unlink(missing_ok=True)


@router.post(
    "/{session_id}/answers",
    response_model=InterviewSessionResponse,
)
async def submit_answer(
    session_id: uuid.UUID,
    payload: SubmitAnswerRequest,
    service: Annotated[InterviewService, Depends(get_interview_service)],
) -> dict:
    try:
        return await run_in_threadpool(
            service.submit_answer,
            str(session_id),
            payload.answer,
        )
    except Exception as exc:
        _raise_graph_http_error(exc)
        raise


@router.get(
    "/{session_id}",
    response_model=InterviewSessionResponse,
)
async def get_interview(
    session_id: uuid.UUID,
    service: Annotated[InterviewService, Depends(get_interview_service)],
) -> dict:
    try:
        return await run_in_threadpool(service.get_interview, str(session_id))
    except Exception as exc:
        _raise_graph_http_error(exc)
        raise
