"""Structured outputs used while conducting and reporting an interview."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


QuestionType = Literal["INITIAL", "FOLLOW_UP", "NEXT"]


class GeneratedInterviewQuestion(BaseModel):
    question: str = Field(
        min_length=10,
        max_length=300,
        description=(
            "지원자에게 제시할 개인화된 면접 질문 한 개. "
            "여러 질문을 결합하지 않고 한국어 의문문으로 작성"
        ),
    )


class AnswerEvaluationScores(BaseModel):
    relevance: int = Field(ge=1, le=5, description="질문의 의도와 답변 내용의 관련성")
    specificity: int = Field(ge=1, le=5, description="사례, 상황, 수치 등 답변의 구체성")
    logical_structure: int = Field(
        ge=1, le=5, description="답변 전개의 논리성과 이해 가능성"
    )
    role_clarity: int = Field(
        ge=1, le=5, description="지원자가 맡은 역할과 기여의 명확성"
    )
    action_clarity: int = Field(
        ge=1, le=5, description="지원자가 수행한 행동과 판단의 명확성"
    )
    result_clarity: int = Field(
        ge=1, le=5, description="행동의 결과, 성과 또는 학습의 명확성"
    )


class AnswerEvaluationResult(BaseModel):
    summary: str = Field(min_length=10, description="답변 품질을 사실 중심으로 요약한 평가")
    scores: AnswerEvaluationScores
    strengths: list[str] = Field(default_factory=list, max_length=3)
    improvement_points: list[str] = Field(default_factory=list, max_length=3)
    missing_points: list[str] = Field(default_factory=list, max_length=3)
    answer_evidence: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("strengths", "improvement_points", "missing_points", mode="before")
    @classmethod
    def limit_three_items(cls, value: Any) -> list[Any]:
        return list(value or [])[:3]

    @field_validator("answer_evidence", mode="before")
    @classmethod
    def limit_five_evidence_items(cls, value: Any) -> list[Any]:
        return list(value or [])[:5]


class InterviewRouteDecision(BaseModel):
    route: Literal["FOLLOW_UP", "NEXT", "END"]
    end_reason: str | None = None


class QuestionFeedback(BaseModel):
    question_number: int = Field(ge=1, description="질문 순서")
    question: str = Field(description="면접 질문")
    answer: str = Field(description="사용자 답변")
    competency: str = Field(description="평가 대상 역량")
    question_type: QuestionType
    overall_score: float = Field(ge=20, le=100)
    summary: str = Field(default="", description="해당 답변의 평가 요약")
    strengths: list[str] = Field(default_factory=list, max_length=3)
    improvement_points: list[str] = Field(default_factory=list, max_length=3)
    missing_points: list[str] = Field(default_factory=list, max_length=3)
    answer_evidence: list[str] = Field(default_factory=list, max_length=5)
    improvement_focus: str = Field(
        default="", description="다음 답변에서 우선 보완할 한 가지 항목"
    )


class CompetencyFeedback(BaseModel):
    competency: str = Field(description="평가 대상 핵심 역량명")
    summary: str = Field(min_length=10, description="해당 역량의 답변 품질 종합 요약")
    strengths: list[str] = Field(default_factory=list, max_length=3)
    improvement_points: list[str] = Field(default_factory=list, max_length=3)
    evidence: list[str] = Field(default_factory=list, max_length=3)


class FeedbackActionItem(BaseModel):
    action: str = Field(min_length=10, description="다음 면접 전에 실행할 구체적인 연습 행동")
    purpose: str = Field(min_length=10, description="해당 연습이 필요한 이유와 개선 목표")


class FinalInterviewFeedbackReport(BaseModel):
    overall_summary: str = Field(
        min_length=20, description="전체 면접 답변의 특징을 요약한 종합 피드백"
    )
    competency_feedback: list[CompetencyFeedback] = Field(
        min_length=1, description="대상 역량별 피드백"
    )
    key_strengths: list[str] = Field(default_factory=list, max_length=3)
    key_improvement_areas: list[str] = Field(default_factory=list, max_length=3)
    recurring_strengths: list[str] = Field(default_factory=list, max_length=3)
    recurring_improvement_patterns: list[str] = Field(
        default_factory=list, max_length=3
    )
    action_plan: list[FeedbackActionItem] = Field(default_factory=list, max_length=3)
    closing_message: str = Field(min_length=10, description="지원자에게 전달할 마무리 메시지")

