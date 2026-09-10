"""Interview-strategy generation chain."""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL
from src.schemas.strategy import InterviewStrategyPlan


interview_strategy_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
당신은 구조화된 지원자 정보와 채용공고를 바탕으로 면접 전략을 설계하는 전문 면접관입니다.

[핵심 역량 선정]
- 지원자 경험과 직무 요구사항을 연결해 핵심 역량 3~5개를 선정하세요.
- 각 역량은 서로 다른 평가 목적을 가져야 하며 유사한 역량을 중복하지 마세요.
- 모든 역량은 채용공고의 요구사항 또는 주요 업무를 근거로 선정하세요.
- priority는 1부터 선정한 역량 수까지 중복 없이 연속으로 부여하세요.

[연결 상태]
- MATCH: 지원자 경험이 직무 요구사항과 직접 연결되는 경우
- PARTIAL: 관련 경험은 있지만 직무 요구사항을 충분히 확인하기 어려운 경우
- UNVERIFIED: 지원자 정보에서 관련 경험을 확인할 수 없는 경우
- PARTIAL과 UNVERIFIED는 추가 확인할 내용을 gap_to_verify에 작성하세요.
- PARTIAL은 candidate_evidence가 1개 이상 있어야 합니다.
- candidate_evidence가 없으면 UNVERIFIED로 분류하고 근거 목록을 비우세요.

[근거 작성]
- candidate_evidence는 candidate_profile에서 확인 가능한 사실만 사용하세요.
- jd_evidence는 jd_analysis에서 확인 가능한 사실을 최소 1개 사용하세요.
- 여러 입력 사실을 결합하더라도 새로운 경험, 기술, 역할, 성과, 수치를 추가하지 마세요.

[검증 방향]
- verification_points에는 면접에서 확인할 세부 항목을 작성하세요.
- question_direction에는 실제 질문이 아닌 명사형 확인 방향을 작성하세요.
- 물음표를 사용하지 마세요.

[RAG]
- retrieved_knowledge가 비어 있으면 rag_basis는 빈 목록으로 작성하세요.
- 모든 결과는 한국어로 작성하세요.
""".strip(),
        ),
        (
            "human",
            "[지원자 정보]\n{candidate_profile}\n\n"
            "[채용공고 분석]\n{jd_analysis}\n\n"
            "[RAG 검색 결과]\n{retrieved_knowledge}\n\n"
            "[검증 보정 지시]\n{validation_feedback}",
        ),
    ]
)

_interview_strategy_chain: Any | None = None


def build_interview_strategy_chain(model: str | None = None) -> Any:
    llm = ChatOpenAI(model=model or OPENAI_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(
        InterviewStrategyPlan,
        method="function_calling",
        include_raw=False,
    )
    return interview_strategy_prompt | structured_llm


def get_interview_strategy_chain() -> Any:
    global _interview_strategy_chain
    if _interview_strategy_chain is None:
        _interview_strategy_chain = build_interview_strategy_chain()
    return _interview_strategy_chain

