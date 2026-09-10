"""HTTP request and response schemas for the interview API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.schemas.interview import QuestionType


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=10_000)

    @field_validator("answer")
    @classmethod
    def answer_must_not_be_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("답변은 비어 있을 수 없습니다.")
        return normalized


class InterviewQuestionResponse(BaseModel):
    question: str
    competency: str
    question_type: QuestionType


class InterviewProgressResponse(BaseModel):
    question_count: int = Field(ge=0)
    followup_count: int = Field(ge=0)
    target_competency_count: int = Field(ge=0)


class InterviewSessionResponse(BaseModel):
    session_id: str
    status: Literal["WAITING_ANSWER", "COMPLETED"]
    question: InterviewQuestionResponse | None = None
    progress: InterviewProgressResponse
    target_competencies: list[str] = Field(default_factory=list)
    end_reason: str | None = None
    final_feedback: dict[str, Any] | None = None
