"""LangGraph interrupt node for collecting one user answer."""

from __future__ import annotations

import re
from typing import Any, Mapping

from langgraph.types import interrupt


VALID_QUESTION_TYPES = {"INITIAL", "NEXT", "FOLLOW_UP"}


def normalize_user_answer(answer: Any) -> str:
    if isinstance(answer, dict):
        answer = answer.get("answer", "")
    if not isinstance(answer, str):
        return ""
    return re.sub(r"\s+", " ", answer).strip()


def user_answer_node(state: Mapping[str, Any]) -> dict[str, Any]:
    current_question = str(state.get("current_question") or "").strip()
    current_competency = str(state.get("current_competency") or "").strip()
    question_type = state.get("question_type")
    if not current_question:
        raise ValueError("사용자 답변을 받으려면 current_question이 필요합니다.")
    if not current_competency:
        raise ValueError("사용자 답변을 기록하려면 current_competency가 필요합니다.")
    if question_type not in VALID_QUESTION_TYPES:
        raise ValueError("유효한 question_type이 필요합니다.")

    answer_input = interrupt(
        {
            "type": "user_answer_required",
            "message": "아래 면접 질문에 답변해 주세요.",
            "question": current_question,
            "competency": current_competency,
            "question_type": question_type,
        }
    )
    current_answer = normalize_user_answer(answer_input)
    if not current_answer:
        raise ValueError("사용자 답변은 비어 있을 수 없습니다.")

    interview_history = [
        dict(item) for item in state.get("interview_history", [])
    ]
    interview_history.append(
        {
            "question": current_question,
            "answer": current_answer,
            "competency": current_competency,
            "question_type": question_type,
        }
    )
    return {
        "current_answer": current_answer,
        "interview_history": interview_history,
        "question_count": state.get("question_count", 0) + 1,
        "followup_count": state.get("followup_count", 0)
        + (1 if question_type == "FOLLOW_UP" else 0),
    }
