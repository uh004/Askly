"""LangGraph node for composing question-level and overall feedback."""

from __future__ import annotations

import json
from typing import Any, Mapping

from src.chains.feedback import get_feedback_report_chain
from src.nodes.interview_review import get_evaluation_overall_score
from src.schemas.interview import QuestionFeedback


def calculate_feedback_scores(
    evaluation_history: list[dict[str, Any]],
    target_competencies: list[str],
) -> tuple[float, dict[str, float]]:
    latest_scores: dict[str, float | None] = {
        competency: None for competency in target_competencies
    }
    for item in evaluation_history:
        competency = item.get("competency")
        evaluation = item.get("evaluation", {})
        if competency not in latest_scores or not evaluation:
            continue
        latest_scores[competency] = get_evaluation_overall_score(evaluation)

    missing_competencies = [
        competency for competency, score in latest_scores.items() if score is None
    ]
    if missing_competencies:
        raise ValueError(
            "평가 이력이 없는 역량이 있습니다: " + ", ".join(missing_competencies)
        )

    competency_scores = {
        competency: round(float(score), 1)
        for competency, score in latest_scores.items()
        if score is not None
    }
    overall_score = round(
        sum(competency_scores.values()) / len(competency_scores),
        1,
    )
    return overall_score, competency_scores


def build_question_feedback(
    evaluation_history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    question_feedback: list[dict[str, Any]] = []
    for index, item in enumerate(evaluation_history, start=1):
        evaluation = item.get("evaluation", {})
        if not evaluation:
            raise ValueError(f"{index}번째 질문의 평가 결과가 없습니다.")

        improvement_points = [
            str(value).strip()
            for value in evaluation.get("improvement_points", [])
            if str(value).strip()
        ][:3]
        missing_points = [
            str(value).strip()
            for value in evaluation.get("missing_points", [])
            if str(value).strip()
        ][:3]
        feedback = QuestionFeedback(
            question_number=index,
            question=str(item.get("question") or "").strip(),
            answer=str(item.get("answer") or "").strip(),
            competency=str(item.get("competency") or "").strip(),
            question_type=item.get("question_type"),
            overall_score=get_evaluation_overall_score(evaluation),
            summary=str(evaluation.get("summary") or "").strip(),
            strengths=[
                str(value).strip()
                for value in evaluation.get("strengths", [])
                if str(value).strip()
            ][:3],
            improvement_points=improvement_points,
            missing_points=missing_points,
            answer_evidence=[
                str(value).strip()
                for value in evaluation.get("answer_evidence", [])
                if str(value).strip()
            ][:5],
            improvement_focus=next(
                iter(improvement_points or missing_points),
                "",
            ),
        )
        question_feedback.append(feedback.model_dump())
    return question_feedback


def final_feedback_node(
    state: Mapping[str, Any],
    *,
    chain: Any | None = None,
) -> dict[str, Any]:
    interview_history = list(state.get("interview_history", []))
    evaluation_history = list(state.get("evaluation_history", []))
    interview_strategy = state.get("interview_strategy")
    target_competencies = list(state.get("target_competencies", []))

    if not interview_history:
        raise ValueError("피드백 보고서에는 interview_history가 필요합니다.")
    if not evaluation_history:
        raise ValueError("피드백 보고서에는 evaluation_history가 필요합니다.")
    if not interview_strategy:
        raise ValueError("피드백 보고서에는 interview_strategy가 필요합니다.")
    if not target_competencies:
        raise ValueError("피드백 보고서에는 target_competencies가 필요합니다.")
    if any(
        not item.get("question") or not item.get("answer")
        for item in interview_history
    ):
        raise ValueError("질문 또는 답변이 누락된 면접 기록이 있습니다.")
    if len(interview_history) != len(evaluation_history):
        raise ValueError("면접 기록과 평가 이력의 개수가 일치하지 않습니다.")

    history_keys = ("question", "answer", "competency", "question_type")
    if any(
        interview_item.get(key) != evaluation_item.get(key)
        for interview_item, evaluation_item in zip(
            interview_history,
            evaluation_history,
        )
        for key in history_keys
    ):
        raise ValueError("면접 기록과 평가 이력의 내용이 일치하지 않습니다.")

    question_feedback = build_question_feedback(evaluation_history)
    overall_score, competency_scores = calculate_feedback_scores(
        evaluation_history,
        target_competencies,
    )
    report = (chain or get_feedback_report_chain()).invoke(
        {
            "target_competencies": json.dumps(
                target_competencies, ensure_ascii=False, indent=2
            ),
            "interview_strategy": json.dumps(
                interview_strategy, ensure_ascii=False, indent=2
            ),
            "question_feedback": json.dumps(
                question_feedback, ensure_ascii=False, indent=2
            ),
            "score_summary": json.dumps(
                {
                    "overall_score": overall_score,
                    "competency_scores": competency_scores,
                },
                ensure_ascii=False,
                indent=2,
            ),
        }
    )

    final_feedback = report.model_dump()
    reported_competencies = [
        item["competency"] for item in final_feedback["competency_feedback"]
    ]
    if (
        len(reported_competencies) != len(set(reported_competencies))
        or set(reported_competencies) != set(target_competencies)
    ):
        raise ValueError(
            "피드백 보고서의 역량 목록이 target_competencies와 일치하지 않습니다."
        )

    for item in final_feedback["competency_feedback"]:
        item["final_score"] = competency_scores[item["competency"]]
    final_feedback["question_feedback"] = question_feedback
    final_feedback["overall_score"] = overall_score
    final_feedback["competency_scores"] = competency_scores
    final_feedback["interview_statistics"] = {
        "question_count": len(interview_history),
        "evaluation_count": len(evaluation_history),
        "followup_count": sum(
            1
            for item in interview_history
            if item.get("question_type") == "FOLLOW_UP"
        ),
        "evaluated_competency_count": len(competency_scores),
    }
    return {"final_feedback": final_feedback}
