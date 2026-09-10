"""Interview-answer evaluation chain."""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL
from src.schemas.interview import AnswerEvaluationResult


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
- FOLLOW_UP은 동일 역량의 이전 답변과 현재 답변을 함께 평가하세요.
- MATCH, PARTIAL, UNVERIFIED 상태는 점수에 직접 반영하지 마세요.

[근거 및 출력]
- 현재 답변과 동일 역량의 이전 답변에 직접 포함된 내용만 근거로 사용하세요.
- 질문이나 전략에만 있는 내용을 사용자가 답변한 사실로 간주하지 마세요.
- 확인할 수 없는 strengths와 answer_evidence는 빈 목록으로 반환하세요.
- 다음 진행 경로는 결정하지 마세요.
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
    llm = ChatOpenAI(model=model or OPENAI_MODEL, temperature=0)
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

