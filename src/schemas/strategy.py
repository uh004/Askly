"""Structured output for interview strategy generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CompetencyStrategy(BaseModel):
    competency: str = Field(description="면접에서 검증할 핵심 역량명")
    priority: int = Field(
        ge=1,
        le=5,
        description="검증 우선순위. 1이 가장 높고 5가 가장 낮음",
    )
    selection_reason: str = Field(
        description="지원자 경험과 채용공고를 근거로 이 역량을 선정한 이유"
    )
    alignment_status: Literal["MATCH", "PARTIAL", "UNVERIFIED"] = Field(
        description="JD 요구사항과 지원자 경험의 연결 상태"
    )
    gap_to_verify: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="면접에서 추가로 확인할 경험·역할·성과의 공백",
    )
    candidate_evidence: list[str] = Field(
        default_factory=list,
        description="지원자 서류에서 확인된 관련 경험과 근거",
    )
    jd_evidence: list[str] = Field(
        min_length=1,
        description="채용공고에서 이 역량이 필요하다고 판단한 근거",
    )
    verification_points: list[str] = Field(
        min_length=1,
        max_length=3,
        description="면접에서 사실 여부와 깊이를 확인할 세부 항목 1~3개",
    )
    question_direction: str = Field(
        description="실제 질문 문장이 아닌 해당 역량의 확인 방향"
    )
    rag_basis: list[str] = Field(
        default_factory=list,
        description="RAG 검색 결과에서 참고한 평가 기준. 미연결이면 빈 목록",
    )


class InterviewStrategyPlan(BaseModel):
    strategy_summary: str = Field(description="면접 전체 전략 요약")
    role_focus: str = Field(description="채용 직무에서 가장 중요하게 볼 역할과 업무")
    alignment_summary: str = Field(
        description="지원자 경험과 채용공고 요구사항의 연결점 및 확인이 필요한 공백"
    )
    competencies: list[CompetencyStrategy] = Field(
        min_length=3,
        max_length=5,
        description="우선순위가 지정된 핵심 평가 역량 3~5개",
    )
    interview_flow: list[str] = Field(
        min_length=3,
        max_length=5,
        description="면접에서 역량을 확인할 권장 진행 순서",
    )
    cautions: list[str] = Field(
        description="문서에 없는 사실을 단정하지 않기 위한 면접 진행 주의사항"
    )
    rag_applied: bool = Field(
        description="retrieved_knowledge가 실제 전략 수립에 사용되었는지 여부"
    )

