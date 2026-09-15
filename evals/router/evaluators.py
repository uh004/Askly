"""Policy conformance metrics for the deterministic Router."""

from __future__ import annotations

from typing import Any


ROUTE_ORDER = ("FOLLOW_UP", "NEXT", "END")


def policy_conformance_evaluator(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
    **_: Any,
) -> dict[str, Any]:
    actual = outputs.get("route")
    expected = reference_outputs.get("expected_route")
    return {
        "key": "policy_conformance",
        "score": 1 if actual == expected else 0,
        "comment": f"expected={expected}, actual={actual}",
    }


def router_policy_summary(
    *,
    outputs: list[dict[str, Any]],
    reference_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not outputs or len(outputs) != len(reference_outputs):
        raise ValueError("Summary 평가에는 길이가 같은 Router 결과와 정답이 필요합니다.")
    correct = [
        output.get("route") == reference.get("expected_route")
        for output, reference in zip(outputs, reference_outputs)
    ]
    boundary_indexes = [
        index
        for index, reference in enumerate(reference_outputs)
        if reference.get("is_boundary") is True
    ]
    boundary_rate = (
        sum(correct[index] for index in boundary_indexes) / len(boundary_indexes)
        if boundary_indexes
        else 0.0
    )
    return [
        {
            "key": "policy_conformance_rate",
            "score": sum(correct) / len(correct),
        },
        {
            "key": "boundary_scenario_pass_rate",
            "score": boundary_rate,
            "comment": f"경계 사례 {len(boundary_indexes)}건",
        },
    ]


def router_diagnostic_summary(
    *,
    outputs: list[dict[str, Any]],
    reference_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not outputs or len(outputs) != len(reference_outputs):
        raise ValueError("Summary 평가에는 길이가 같은 Router 결과와 정답이 필요합니다.")
    results: list[dict[str, Any]] = []
    for route in ROUTE_ORDER:
        indexes = [
            index
            for index, reference in enumerate(reference_outputs)
            if reference.get("expected_route") == route
        ]
        results.append(
            {
                "key": f"pass_rate_{route.lower()}",
                "score": (
                    sum(
                        outputs[index].get("route") == route for index in indexes
                    )
                    / len(indexes)
                    if indexes
                    else 0.0
                ),
            }
        )
    return results
