"""Answer-evaluation chain and LangGraph node."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator


class AnswerEvaluationScores(BaseModel):
    relevance: int = Field(
        ge=1, le=5, description="질문의 의도와 답변 내용의 관련성"
    )
    specificity: int = Field(
        ge=1, le=5, description="사례, 상황, 수치 등 답변의 구체성"
    )
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
    summary: str = Field(
        min_length=10,
        description="답변 품질을 사실 중심으로 요약한 평가",
    )
    scores: AnswerEvaluationScores
    strengths: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="답변에서 잘 드러난 점. 확인되지 않으면 빈 목록",
    )
    improvement_points: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="더 명확하게 보완할 수 있는 점. 없으면 빈 목록",
    )
    missing_points: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="질문 의도나 검증 항목 중 답변에서 확인되지 않은 내용",
    )
    answer_evidence: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="평가를 뒷받침하는 사용자 답변 속 핵심 표현",
    )

    @field_validator("strengths", "improvement_points", "missing_points", mode="before")
    @classmethod
    def limit_three_items(cls, value: Any) -> list[Any]:
        """Keep structured output valid even if the model returns extra items."""

        return list(value or [])[:3]

    @field_validator("answer_evidence", mode="before")
    @classmethod
    def limit_five_evidence_items(cls, value: Any) -> list[Any]:
        return list(value or [])[:5]


answer_evaluation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 지원자의 면접 답변만 객관적으로 평가하는 전문 면접관입니다. "
            "현재 질문, 평가 역량, 역량별 검증 항목을 기준으로 답변을 평가하세요. "
            "관련성, 구체성, 논리성, 역할, 행동, 결과의 명확성을 각각 "
            "1점부터 5점까지 부여하세요. 1점은 확인되지 않음, 3점은 일부 확인, "
            "5점은 구체적인 근거와 함께 명확히 확인됨을 의미합니다. "
            "사용자 답변에 직접 포함된 내용만 평가 근거로 사용하고, 이력서나 "
            "질문에만 있는 정보를 사용자가 답변한 사실처럼 간주하지 마세요. "
            "answer_evidence에는 실제 답변에서 확인 가능한 표현만 작성하세요. "
            "답변에서 강점이나 인용 가능한 근거를 확인할 수 없으면 strengths와 "
            "answer_evidence는 빈 목록으로 반환하세요. strengths, improvement_points, "
            "missing_points는 각각 최대 3개, answer_evidence는 최대 5개로 제한하세요. "
            "FOLLOW_UP, NEXT, END 등 "
            "다음 진행 경로는 결정하지 마세요. 모든 결과는 한국어로 작성하세요.",
        ),
        (
            "human",
            "[현재 질문]\n{current_question}\n\n"
            "[사용자 답변]\n{current_answer}\n\n"
            "[평가 역량]\n{current_competency}\n\n"
            "[질문 유형]\n{question_type}\n\n"
            "[역량별 면접 전략]\n{competency_strategy}",
        ),
    ]
)

_answer_evaluation_chain: Any | None = None


def build_answer_evaluation_chain(model: str | None = None) -> Any:
    llm = ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )
    structured_llm = llm.with_structured_output(
        AnswerEvaluationResult,
        method="function_calling",
        include_raw=False,
    )
    return answer_evaluation_prompt | structured_llm


def get_answer_evaluation_chain() -> Any:
    global _answer_evaluation_chain
    if _answer_evaluation_chain is None:
        _answer_evaluation_chain = build_answer_evaluation_chain()
    return _answer_evaluation_chain


def _to_serializable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {key: _to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_serializable(item) for item in value]
    return value


def calculate_overall_score(scores: Mapping[str, int | float]) -> float:
    """Convert the mean of 1-5 dimension scores to a 100-point score."""

    if not scores:
        return 0.0
    return round(sum(float(score) for score in scores.values()) / (len(scores) * 5) * 100, 1)


def answer_evaluation_node(
    state: Mapping[str, Any],
    *,
    chain: Any | None = None,
) -> dict[str, Any]:
    """Evaluate the current answer and append the result to evaluation history."""

    current_question = str(state.get("current_question") or "").strip()
    current_answer = str(state.get("current_answer") or "").strip()
    current_competency = str(state.get("current_competency") or "").strip()
    interview_strategy = _to_serializable(state.get("interview_strategy"))

    if not current_question:
        raise ValueError("답변 평가에는 current_question이 필요합니다.")
    if not current_answer:
        raise ValueError("답변 평가에는 current_answer가 필요합니다.")
    if not current_competency:
        raise ValueError("답변 평가에는 current_competency가 필요합니다.")
    if not interview_strategy:
        raise ValueError("답변 평가에는 interview_strategy가 필요합니다.")

    competency_strategy = next(
        (
            item
            for item in interview_strategy.get("competencies", [])
            if item.get("competency") == current_competency
        ),
        {"competency": current_competency},
    )

    evaluation_chain = chain or get_answer_evaluation_chain()
    evaluation: AnswerEvaluationResult = evaluation_chain.invoke(
        {
            "current_question": current_question,
            "current_answer": current_answer,
            "current_competency": current_competency,
            "question_type": state.get("question_type", "INITIAL"),
            "competency_strategy": json.dumps(
                competency_strategy, ensure_ascii=False, indent=2
            ),
        }
    )

    current_evaluation = evaluation.model_dump()
    current_evaluation["overall_score"] = calculate_overall_score(
        current_evaluation["scores"]
    )
    current_evaluation["competency"] = current_competency
    current_evaluation["question_type"] = state.get("question_type", "INITIAL")

    evaluation_history = [
        dict(item) for item in state.get("evaluation_history", [])
    ]
    evaluation_history.append(
        {
            "question": current_question,
            "answer": current_answer,
            "competency": current_competency,
            "question_type": state.get("question_type", "INITIAL"),
            "evaluation": current_evaluation,
        }
    )

    return {
        "current_evaluation": current_evaluation,
        "evaluation_history": evaluation_history,
    }
