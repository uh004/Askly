"""LangSmith target function for the question-generation node."""

from __future__ import annotations

from typing import Any

from src.chains.question import build_question_generation_chain
from src.nodes.question_generation import question_generation_node


def question_generation_target(
    inputs: dict[str, Any],
    *,
    chain: Any | None = None,
) -> dict[str, Any]:
    """Run only the question-generation node and normalize its output."""

    result = question_generation_node(inputs, chain=chain)
    return {
        "question": result["current_question"],
        "question_type": result["question_type"],
        "competency": result["current_competency"],
    }


def make_question_generation_target(prompt_version: str) -> Any:
    """Bind one prompt version so v1/v2 experiments execute different prompts."""

    chain = build_question_generation_chain(prompt_version=prompt_version)

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        return question_generation_target(inputs, chain=chain)

    return target
