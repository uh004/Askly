"""LangSmith target for the deterministic interview Router."""

from __future__ import annotations

from typing import Any

from src.nodes.interview_review import interview_review_node


def router_target(inputs: dict[str, Any]) -> dict[str, Any]:
    decision = interview_review_node(inputs)
    return {
        "route": decision["route"],
        "end_reason": decision.get("end_reason"),
    }
