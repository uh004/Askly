"""Final interview-feedback report chain."""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL
from src.schemas.interview import FinalInterviewFeedbackReport


feedback_report_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
당신은 모의면접 종료 후 학습 목적의 전체 피드백을 제공하는 전문 코치입니다.

[작성 범위]
- 질문별 피드백은 이미 코드로 생성되므로 전체 및 역량별 피드백만 작성하세요.
- target_competencies의 각 역량을 competency_feedback에 정확히 한 번씩 포함하세요.
- 코드로 계산한 overall_score와 competency_scores를 변경하지 마세요.

[근거 규칙]
- 제공된 질문별 피드백과 면접 전략에서 확인되는 내용만 사용하세요.
- 제공되지 않은 경험, 수치, 성과를 만들거나 성격과 태도를 추정하지 마세요.
- 확인할 수 없는 strengths와 evidence는 빈 목록으로 반환하세요.

[종합 규칙]
- 둘 이상의 답변에서 확인된 내용만 반복 패턴으로 작성하세요.
- action_plan은 확인된 개선점이 있을 때만 1~3개 작성하세요.
- 합격·불합격 또는 채용 여부를 판단하지 마세요.
- 모든 결과는 한국어로 작성하세요.
""".strip(),
        ),
        (
            "human",
            "[대상 역량]\n{target_competencies}\n\n"
            "[면접 전략]\n{interview_strategy}\n\n"
            "[질문별 피드백]\n{question_feedback}\n\n"
            "[코드로 계산한 점수 요약]\n{score_summary}",
        ),
    ]
)

_feedback_report_chain: Any | None = None


def build_feedback_report_chain(model: str | None = None) -> Any:
    llm = ChatOpenAI(model=model or OPENAI_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(
        FinalInterviewFeedbackReport,
        method="function_calling",
        include_raw=False,
    )
    return feedback_report_prompt | structured_llm


def get_feedback_report_chain() -> Any:
    global _feedback_report_chain
    if _feedback_report_chain is None:
        _feedback_report_chain = build_feedback_report_chain()
    return _feedback_report_chain

