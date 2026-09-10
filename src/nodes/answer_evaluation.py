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
        description="평가를 뒷받침하는 현재 또는 동일 역량 이전 답변 속 핵심 표현",
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


VALID_QUESTION_TYPES = {"INITIAL", "NEXT", "FOLLOW_UP"}
ANSWER_EVALUATION_WEIGHTS = {
    "relevance": 20,
    "specificity": 15,
    "logical_structure": 10,
    "role_clarity": 15,
    "action_clarity": 20,
    "result_clarity": 20,
}


answer_evaluation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
당신은 사용자의 면접 답변을 객관적으로 평가하는 전문 면접관입니다.

[평가 항목]
- relevance: 질문 의도와 평가 역량에 맞는 답변인지 평가
- specificity: 상황, 사례, 기술, 수치가 구체적인지 평가
- logical_structure: 답변 흐름이 자연스럽고 이해하기 쉬운지 평가
- role_clarity: 지원자가 직접 맡은 역할과 기여가 명확한지 평가
- action_clarity: 수행한 행동과 판단 근거가 명확한지 평가
- result_clarity: 성과, 변화, 실패 결과 또는 학습이 명확한지 평가

[점수 기준]
- 1점: 답변에서 확인할 수 없음
- 2점: 언급은 있지만 매우 모호함
- 3점: 일부 확인되지만 설명이 부족함
- 4점: 구체적인 사례와 근거로 설명함
- 5점: 역할, 행동, 판단 또는 결과가 명확한 근거와 함께 확인됨

[평가 범위]
- INITIAL과 NEXT는 현재 답변을 중심으로 평가하세요.
- FOLLOW_UP은 동일 역량의 이전 답변과 현재 답변을 함께 보고 부족했던 내용이 보완됐는지 평가하세요.
- MATCH, PARTIAL, UNVERIFIED 상태는 점수에 직접 반영하지 말고 사용자가 실제로 답변한 내용만 평가하세요.

[근거 및 출력]
- 현재 답변과 동일 역량의 이전 답변에 직접 포함된 내용만 평가 근거로 사용하세요.
- 질문이나 면접 전략에만 있는 내용을 사용자가 답변한 사실처럼 간주하지 마세요.
- answer_evidence에는 답변에서 확인 가능한 핵심 표현만 작성하세요.
- 확인할 수 없는 strengths와 answer_evidence는 빈 목록으로 반환하세요.
- missing_points에는 현재 질문 또는 verification_points와 관련해 아직 확인되지 않은 내용만 작성하세요.
- FOLLOW_UP, NEXT, END 등 다음 진행 경로는 결정하지 마세요.
- 모든 결과는 한국어로 작성하세요.
""".strip(),
        ),
        (
            "human",
            "[현재 질문]\n{current_question}\n\n"
            "[사용자 답변]\n{current_answer}\n\n"
            "[평가 역량]\n{current_competency}\n\n"
            "[질문 유형]\n{question_type}\n\n"
            "[역량별 면접 전략]\n{competency_strategy}\n\n"
            "[동일 역량 이전 답변]\n{previous_competency_answers}",
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
    """Convert weighted 1-5 dimension scores to a 100-point score."""

    if not scores:
        return 0.0
    missing_fields = set(ANSWER_EVALUATION_WEIGHTS) - set(scores)
    if missing_fields:
        raise ValueError(
            "종합점수 계산에 필요한 항목이 없습니다: "
            + ", ".join(sorted(missing_fields))
        )
    return round(
        sum(
            float(scores[field]) / 5 * weight
            for field, weight in ANSWER_EVALUATION_WEIGHTS.items()
        ),
        1,
    )


def answer_evaluation_node(
    state: Mapping[str, Any],
    *,
    chain: Any | None = None,
) -> dict[str, Any]:
    """Evaluate the current answer and append the result to evaluation history."""

    current_question = str(state.get("current_question") or "").strip()
    current_answer = str(state.get("current_answer") or "").strip()
    current_competency = str(state.get("current_competency") or "").strip()
    question_type = state.get("question_type")
    interview_strategy = _to_serializable(state.get("interview_strategy"))

    if not current_question:
        raise ValueError("답변 평가에는 current_question이 필요합니다.")
    if not current_answer:
        raise ValueError("답변 평가에는 current_answer가 필요합니다.")
    if not current_competency:
        raise ValueError("답변 평가에는 current_competency가 필요합니다.")
    if not interview_strategy:
        raise ValueError("답변 평가에는 interview_strategy가 필요합니다.")
    if question_type not in VALID_QUESTION_TYPES:
        raise ValueError("답변 평가에는 유효한 question_type이 필요합니다.")

    competency_strategy = next(
        (
            item
            for item in interview_strategy.get("competencies", [])
            if item.get("competency") == current_competency
        ),
        None,
    )
    if competency_strategy is None:
        raise ValueError("current_competency가 interview_strategy에 없습니다.")

    previous_competency_answers = []
    if question_type == "FOLLOW_UP":
        previous_competency_answers = [
            {
                "question": str(item.get("question") or "").strip(),
                "answer": str(item.get("answer") or "").strip(),
            }
            for item in state.get("evaluation_history", [])
            if item.get("competency") == current_competency
            and str(item.get("answer") or "").strip()
        ]

    evaluation_chain = chain or get_answer_evaluation_chain()
    evaluation: AnswerEvaluationResult = evaluation_chain.invoke(
        {
            "current_question": current_question,
            "current_answer": current_answer,
            "current_competency": current_competency,
            "question_type": question_type,
            "competency_strategy": json.dumps(
                competency_strategy, ensure_ascii=False, indent=2
            ),
            "previous_competency_answers": json.dumps(
                previous_competency_answers, ensure_ascii=False, indent=2
            ),
        }
    )

    current_evaluation = evaluation.model_dump()
    current_evaluation["overall_score"] = calculate_overall_score(
        current_evaluation["scores"]
    )
    current_evaluation["competency"] = current_competency
    current_evaluation["question_type"] = question_type

    evaluation_history = [
        dict(item) for item in state.get("evaluation_history", [])
    ]
    evaluation_history.append(
        {
            "question": current_question,
            "answer": current_answer,
            "competency": current_competency,
            "question_type": question_type,
            "evaluation": current_evaluation,
        }
    )

    return {
        "current_evaluation": current_evaluation,
        "evaluation_history": evaluation_history,
    }
