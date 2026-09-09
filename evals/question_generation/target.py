"""LangSmith target function for the question-generation node."""

from __future__ import annotations

from typing import Any

from src.nodes.question_generation import question_generation_node


def question_generation_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run only the question-generation node and normalize its output."""

    result = question_generation_node(inputs)
    return {
        "question": result["current_question"],
        "question_type": result["question_type"],
        "competency": result["current_competency"],
    }
