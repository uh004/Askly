"""FastAPI dependencies shared by route modules."""

from __future__ import annotations

from src.services.interview_service import InterviewService


interview_service = InterviewService()


def get_interview_service() -> InterviewService:
    return interview_service
