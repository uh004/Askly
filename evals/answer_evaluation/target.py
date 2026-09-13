"""LangSmith target for the answer-evaluation node."""

from __future__ import annotations

from typing import Any

from src.chains.evaluation import build_answer_evaluation_chain
from src.nodes.answer_evaluation import answer_evaluation_node


def answer_evaluation_target(
    inputs: dict[str, Any],
    *,
    chain: Any | None = None,
) -> dict[str, Any]:
    result = answer_evaluation_node(inputs, chain=chain)
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


def make_answer_evaluation_target(prompt_version: str) -> Any:
    """Bind one prompt version so v1/v2 experiments execute different prompts."""

    chain = build_answer_evaluation_chain(prompt_version=prompt_version)

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        return answer_evaluation_target(inputs, chain=chain)

    return target
