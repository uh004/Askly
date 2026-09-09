"""LangSmith target for the answer-evaluation node."""

from __future__ import annotations

from typing import Any

from src.nodes.answer_evaluation import answer_evaluation_node


def answer_evaluation_target(inputs: dict[str, Any]) -> dict[str, Any]:
    result = answer_evaluation_node(inputs)
    evaluation = result["current_evaluation"]
    return {
        "summary": evaluation["summary"],
        "scores": evaluation["scores"],
        "overall_score": evaluation["overall_score"],
        "strengths": evaluation["strengths"],
        "improvement_points": evaluation["improvement_points"],
        "missing_points": evaluation["missing_points"],
        "answer_evidence": evaluation["answer_evidence"],
        "competency": evaluation["competency"],
        "question_type": evaluation["question_type"],
    }
