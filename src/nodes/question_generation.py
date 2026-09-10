"""LangGraph node for generating one interview question."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from pydantic import BaseModel

from src.chains.question import (
    build_question_generation_chain,
    get_question_generation_chain,
    question_generation_prompt,
)
from src.config import MAX_QUESTION_GENERATION_ATTEMPTS
from src.schemas.interview import GeneratedInterviewQuestion, QuestionType


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


def _normalize_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question).strip()
    if "?" in normalized:
        return normalized.split("?", 1)[0].strip() + "?"
    return normalized + "?"


def _question_key(question: str) -> str:
    return re.sub(r"[\s?]+", "", question).casefold()


def _validate_generated_question(
    question: str,
    previous_questions: list[str],
) -> list[str]:
    errors: list[str] = []
    if question.count("?") > 1:
        errors.append("두 개 이상의 질문이 포함되었습니다.")

    normalized = _normalize_question(question)
    previous_keys = {_question_key(item) for item in previous_questions if item}
    if _question_key(normalized) in previous_keys:
        errors.append("이전에 생성한 질문과 중복됩니다.")
    return errors


def select_question_context(state: Mapping[str, Any]) -> tuple[str, QuestionType]:
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
        if not str(state.get("current_answer") or "").strip():
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
    recent_history = list(state.get("interview_history", []))[-10:]
    previous_questions = [str(item.get("question") or "") for item in recent_history]
    if state.get("current_question"):
        previous_questions.append(str(state["current_question"]))

    generation_input = {
        "question_type": question_type,
        "current_competency": current_competency,
        "alignment_status": competency_strategy.get("alignment_status", "UNSPECIFIED"),
        "competency_strategy": _json_text(competency_strategy),
        "candidate_profile": _json_text(candidate_profile),
        "jd_analysis": _json_text(jd_analysis),
        "previous_question": state.get("current_question") or "없음",
        "current_answer": state.get("current_answer") or "없음",
        "current_evaluation": _json_text(state.get("current_evaluation", {})),
        "interview_history": _json_text(recent_history),
        "validation_feedback": "없음",
    }

    validation_errors: list[str] = []
    for _ in range(MAX_QUESTION_GENERATION_ATTEMPTS):
        generated = generation_chain.invoke(generation_input)
        validation_errors = _validate_generated_question(
            generated.question,
            previous_questions,
        )
        if not validation_errors:
            break
        generation_input["validation_feedback"] = (
            "이전 질문의 다음 오류만 수정하세요: " + " / ".join(validation_errors)
        )
    else:
        raise ValueError("질문 생성 검증 실패: " + " / ".join(validation_errors))

    return {
        "current_question": _normalize_question(generated.question),
        "current_competency": current_competency,
        "question_type": question_type,
        "current_answer": "",
        "current_evaluation": {},
    }
