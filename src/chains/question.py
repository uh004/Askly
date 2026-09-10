"""Interview-question generation chain."""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL
from src.schemas.interview import GeneratedInterviewQuestion


question_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
당신은 실제 면접을 진행하는 전문 면접관입니다.

[질문 유형]
- INITIAL과 NEXT는 선택된 역량을 처음 확인하는 새로운 질문을 작성하세요.
- FOLLOW_UP은 직전 답변의 missing_points 중 한 가지만 구체적으로 확인하세요.

[연결 상태]
- MATCH는 확인된 경험의 역할, 행동, 기술적 판단 또는 성과를 깊게 확인하세요.
- PARTIAL은 확인된 경험을 바탕으로 gap_to_verify 중 한 가지를 확인하세요.
- UNVERIFIED는 관련 경험이 있다고 단정하지 말고 경험 유무를 중립적으로 확인하세요.
- FOLLOW_UP에서는 연결 상태보다 직전 답변과 평가 결과를 우선하세요.

[공통 규칙]
- 입력 근거와 사용자 답변에 있는 사실만 사용하세요.
- 문서에 없는 경험, 기술, 역할, 성과 또는 수치를 단정하지 마세요.
- 이미 질문한 내용을 반복하거나 답변 예시와 평가 결과를 노출하지 마세요.
- 두 개 이상의 질문을 연결하지 말고 자연스러운 한국어 질문 하나만 작성하세요.
""".strip(),
        ),
        (
            "human",
            "[질문 유형]\n{question_type}\n\n"
            "[현재 평가 역량]\n{current_competency}\n\n"
            "[연결 상태]\n{alignment_status}\n\n"
            "[역량별 면접 전략]\n{competency_strategy}\n\n"
            "[지원자 정보]\n{candidate_profile}\n\n"
            "[채용공고 정보]\n{jd_analysis}\n\n"
            "[이전 질문]\n{previous_question}\n\n"
            "[이전 답변]\n{current_answer}\n\n"
            "[이전 답변 평가]\n{current_evaluation}\n\n"
            "[면접 기록]\n{interview_history}\n\n"
            "[검증 보정 지시]\n{validation_feedback}",
        ),
    ]
)

_question_generation_chain: Any | None = None


def build_question_generation_chain(model: str | None = None) -> Any:
    llm = ChatOpenAI(model=model or OPENAI_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(
        GeneratedInterviewQuestion,
        method="function_calling",
        include_raw=False,
    )
    return question_generation_prompt | structured_llm


def get_question_generation_chain() -> Any:
    global _question_generation_chain
    if _question_generation_chain is None:
        _question_generation_chain = build_question_generation_chain()
    return _question_generation_chain

