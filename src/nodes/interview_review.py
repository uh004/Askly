"""Deterministic interview routing policy and LangGraph node."""

from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel

from src.nodes.answer_evaluation import calculate_overall_score


MAX_INTERVIEW_QUESTIONS = 10
MAX_FOLLOWUPS_PER_COMPETENCY = 2
MIN_SUFFICIENT_SCORE = 70.0


class InterviewRouteDecision(BaseModel):
    route: Literal["FOLLOW_UP", "NEXT", "END"]
    end_reason: str | None = None


def get_evaluation_overall_score(evaluation: Mapping[str, Any]) -> float:
    """Read overall score, or derive it from dimension scores."""

    overall_score = evaluation.get("overall_score")
    if isinstance(overall_score, (int, float)):
        return float(overall_score)

    scores = evaluation.get("scores", {})
    if scores and all(isinstance(score, (int, float)) for score in scores.values()):
        return calculate_overall_score(scores)

    raise ValueError("current_evaluation에 유효한 평가 점수가 없습니다.")


def count_competency_followups(
    interview_history: list[dict[str, Any]],
    competency: str,
) -> int:
    """Count follow-up questions already used for one competency."""

    return sum(
        1
        for item in interview_history
        if item.get("competency") == competency
        and item.get("question_type") == "FOLLOW_UP"
    )


def interview_review_node(state: Mapping[str, Any]) -> dict[str, Any]:
    """Choose FOLLOW_UP, NEXT, or END from score and interview progress."""

    current_evaluation = state.get("current_evaluation")
    current_competency = str(state.get("current_competency") or "").strip()
    target_competencies = list(state.get("target_competencies", []))
    interview_history = list(state.get("interview_history", []))
    question_count = state.get("question_count", 0)
    followup_count = state.get("followup_count", 0)

    if not current_evaluation:
        raise ValueError("인터뷰 진행 검토에는 current_evaluation이 필요합니다.")
    if not current_competency:
        raise ValueError("인터뷰 진행 검토에는 current_competency가 필요합니다.")
    if not target_competencies:
        raise ValueError("인터뷰 진행 검토에는 target_competencies가 필요합니다.")
    if current_competency not in target_competencies:
        raise ValueError("current_competency가 target_competencies에 없습니다.")
    if not isinstance(question_count, int) or question_count < 0:
        raise ValueError("question_count는 0 이상의 정수여야 합니다.")
    if not isinstance(followup_count, int) or followup_count < 0:
        raise ValueError("followup_count는 0 이상의 정수여야 합니다.")

    if question_count >= MAX_INTERVIEW_QUESTIONS:
        return InterviewRouteDecision(
            route="END",
            end_reason=f"최대 질문 수({MAX_INTERVIEW_QUESTIONS}회)에 도달했습니다.",
        ).model_dump()

    overall_score = get_evaluation_overall_score(current_evaluation)
    missing_points = [
        str(item).strip()
        for item in current_evaluation.get("missing_points", [])
        if str(item).strip()
    ]
    needs_follow_up = bool(missing_points) or overall_score < MIN_SUFFICIENT_SCORE

    competency_followups = count_competency_followups(
        interview_history, current_competency
    )
    if followup_count < competency_followups:
        raise ValueError(
            "followup_count가 interview_history의 꼬리질문 수보다 작습니다."
        )

    reviewed_competencies = {
        item.get("competency")
        for item in interview_history
        if item.get("competency")
    }
    reviewed_competencies.add(current_competency)
    remaining_competencies = [
        competency
        for competency in target_competencies
        if competency not in reviewed_competencies
    ]
    remaining_question_slots = MAX_INTERVIEW_QUESTIONS - question_count
    can_follow_up_without_skipping_competency = (
        remaining_question_slots > len(remaining_competencies)
    )

    if (
        needs_follow_up
        and competency_followups < MAX_FOLLOWUPS_PER_COMPETENCY
        and can_follow_up_without_skipping_competency
    ):
        return InterviewRouteDecision(route="FOLLOW_UP").model_dump()

    if remaining_competencies:
        return InterviewRouteDecision(route="NEXT").model_dump()

    if needs_follow_up:
        end_reason = (
            "모든 핵심 역량을 검토했으며 현재 역량의 "
            "꼬리질문 제한에 도달했습니다."
        )
    else:
        end_reason = "모든 핵심 역량의 검증을 완료했습니다."

    return InterviewRouteDecision(route="END", end_reason=end_reason).model_dump()
