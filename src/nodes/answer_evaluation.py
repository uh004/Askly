"""LangGraph node for evaluating an interview answer."""

from __future__ import annotations

import json
from typing import Any, Mapping

from pydantic import BaseModel

from src.chains.evaluation import (
    answer_evaluation_prompt,
    build_answer_evaluation_chain,
    get_answer_evaluation_chain,
)
from src.schemas.interview import AnswerEvaluationResult, AnswerEvaluationScores


VALID_QUESTION_TYPES = {"INITIAL", "NEXT", "FOLLOW_UP"}
ANSWER_EVALUATION_WEIGHTS = {
    "relevance": 20,
    "specificity": 15,
    "logical_structure": 10,
    "role_clarity": 15,
    "action_clarity": 20,
    "result_clarity": 20,
}


def _to_serializable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {key: _to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_serializable(item) for item in value]
    return value


def calculate_overall_score(scores: Mapping[str, int | float]) -> float:
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

    evaluation: AnswerEvaluationResult = (
        chain or get_answer_evaluation_chain()
    ).invoke(
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
