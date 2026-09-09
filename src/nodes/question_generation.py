"""Question-generation chain and LangGraph node.

The notebook and the evaluation harness import this module so both paths test
the same production logic.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Literal, Mapping

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


QuestionType = Literal["INITIAL", "FOLLOW_UP", "NEXT"]


class GeneratedInterviewQuestion(BaseModel):
    """Structured output returned by the question-generation LLM."""

    question: str = Field(
        min_length=10,
        max_length=300,
        description=(
            "지원자에게 제시할 개인화된 면접 질문 한 개. "
            "여러 질문을 결합하지 않고 한국어 의문문으로 작성"
        ),
    )


question_generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 실제 면접을 진행하는 전문 면접관입니다. "
            "선택된 핵심 역량과 지원자·채용공고 근거를 사용해 "
            "지원자에게 적합한 질문을 정확히 한 개만 생성하세요. "
            "INITIAL 또는 NEXT에서는 지원자의 구체적인 경험, 역할, 행동, "
            "기술적 판단이나 성과를 확인하는 새로운 질문을 작성하세요. "
            "FOLLOW_UP에서는 이전 답변과 평가에서 부족한 부분 한 가지를 "
            "더 구체적으로 확인하는 꼬리질문을 작성하세요. "
            "이미 질문한 내용을 반복하거나 문서에 없는 경험을 단정하지 마세요. "
            "질문 안에 답변 예시나 평가 결과를 노출하지 마세요. "
            "두 개 이상의 질문을 연결하지 말고 자연스러운 한국어 의문문으로 작성하세요.",
        ),
        (
            "human",
            "[질문 유형]\n{question_type}\n\n"
            "[현재 평가 역량]\n{current_competency}\n\n"
            "[역량별 면접 전략]\n{competency_strategy}\n\n"
            "[지원자 정보]\n{candidate_profile}\n\n"
            "[채용공고 정보]\n{jd_analysis}\n\n"
            "[이전 질문]\n{previous_question}\n\n"
            "[이전 답변]\n{current_answer}\n\n"
            "[이전 답변 평가]\n{current_evaluation}\n\n"
            "[면접 기록]\n{interview_history}",
        ),
    ]
)

_question_generation_chain: Any | None = None


def build_question_generation_chain(model: str | None = None) -> Any:
    """Build the structured-output question-generation chain."""

    question_llm = ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )
    structured_llm = question_llm.with_structured_output(
        GeneratedInterviewQuestion,
        method="function_calling",
        include_raw=False,
    )
    return question_generation_prompt | structured_llm


def get_question_generation_chain() -> Any:
    """Return a lazily initialized chain to keep local checks API-free."""

    global _question_generation_chain
    if _question_generation_chain is None:
        _question_generation_chain = build_question_generation_chain()
    return _question_generation_chain


def _to_serializable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {key: _to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_serializable(item) for item in value]
    return value


def _json_text(value: Any) -> str:
    return json.dumps(_to_serializable(value), ensure_ascii=False, indent=2)


def select_question_context(state: Mapping[str, Any]) -> tuple[str, QuestionType]:
    """Select the competency and question type from the current graph state."""

    route = state.get("route")
    target_competencies = state.get("target_competencies", [])
    interview_history = state.get("interview_history", [])

    if not target_competencies:
        raise ValueError("질문 생성에 사용할 target_competencies가 없습니다.")

    if route == "END":
        raise ValueError("route가 END이므로 새로운 질문을 생성할 수 없습니다.")

    if route == "FOLLOW_UP":
        current_competency = state.get("current_competency")
        if not current_competency:
            raise ValueError("FOLLOW_UP에는 current_competency가 필요합니다.")
        current_answer = str(state.get("current_answer") or "").strip()
        if not current_answer:
            raise ValueError("FOLLOW_UP에는 이전 답변이 필요합니다.")
        return str(current_competency), "FOLLOW_UP"

    is_first_question = (
        not interview_history
        and not state.get("current_question")
        and state.get("question_count", 0) == 0
    )
    if is_first_question:
        return str(target_competencies[0]), "INITIAL"

    asked_competencies = {
        item.get("competency") or item.get("current_competency")
        for item in interview_history
        if item.get("competency") or item.get("current_competency")
    }
    if state.get("current_competency"):
        asked_competencies.add(state["current_competency"])

    for competency in target_competencies:
        if competency not in asked_competencies:
            return str(competency), "NEXT"

    raise ValueError(
        "모든 target_competencies에 대한 질문이 생성되었습니다. "
        "route를 END로 변경하세요."
    )


def question_generation_node(
    state: Mapping[str, Any],
    *,
    chain: Any | None = None,
) -> dict[str, Any]:
    """Generate one INITIAL, FOLLOW_UP, or NEXT interview question."""

    interview_strategy = state.get("interview_strategy")
    candidate_profile = state.get("candidate_profile")
    jd_analysis = state.get("jd_analysis")

    if not interview_strategy or not candidate_profile or not jd_analysis:
        raise ValueError(
            "질문 생성에는 interview_strategy, candidate_profile, jd_analysis가 필요합니다."
        )

    current_competency, question_type = select_question_context(state)
    strategy_data = _to_serializable(interview_strategy)
    competency_strategy = next(
        (
            item
            for item in strategy_data.get("competencies", [])
            if item.get("competency") == current_competency
        ),
        {"competency": current_competency},
    )

    generation_chain = chain or get_question_generation_chain()
    generated = generation_chain.invoke(
        {
            "question_type": question_type,
            "current_competency": current_competency,
            "competency_strategy": _json_text(competency_strategy),
            "candidate_profile": _json_text(candidate_profile),
            "jd_analysis": _json_text(jd_analysis),
            "previous_question": state.get("current_question") or "없음",
            "current_answer": state.get("current_answer") or "없음",
            "current_evaluation": _json_text(state.get("current_evaluation", {})),
            "interview_history": _json_text(
                list(state.get("interview_history", []))[-10:]
            ),
        }
    )

    question = re.sub(r"\s+", " ", generated.question).strip()
    if "?" in question:
        question = question.split("?", 1)[0].strip() + "?"
    else:
        question += "?"

    return {
        "current_question": question,
        "current_competency": current_competency,
        "question_type": question_type,
        "current_answer": "",
        "current_evaluation": {},
    }
