"""Per-case and aggregate Router classification metrics."""

from __future__ import annotations

from typing import Any


ROUTE_ORDER = ("FOLLOW_UP", "NEXT", "END")


def route_exact_match_evaluator(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
    **_: Any,
) -> dict[str, Any]:
    actual = outputs.get("route")
    expected = reference_outputs.get("expected_route")
    return {
        "key": "route_accuracy",
        "score": 1 if actual == expected else 0,
        "comment": f"expected={expected}, actual={actual}",
    }


def _class_f1(expected: list[str], predicted: list[str], route: str) -> float:
    true_positive = sum(e == route and p == route for e, p in zip(expected, predicted))
    false_positive = sum(e != route and p == route for e, p in zip(expected, predicted))
    false_negative = sum(e == route and p != route for e, p in zip(expected, predicted))
    denominator = 2 * true_positive + false_positive + false_negative
    return 0.0 if denominator == 0 else (2 * true_positive) / denominator


def router_classification_summary(
    *,
    outputs: list[dict[str, Any]],
    reference_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not outputs or len(outputs) != len(reference_outputs):
        raise ValueError("Summary 평가에는 길이가 같은 Router 결과와 정답이 필요합니다.")

    predicted = [str(output.get("route")) for output in outputs]
    expected = [str(reference.get("expected_route")) for reference in reference_outputs]
    accuracy = sum(e == p for e, p in zip(expected, predicted)) / len(expected)
    class_scores = {
        route: _class_f1(expected, predicted, route) for route in ROUTE_ORDER
    }
    results: list[dict[str, Any]] = [
        {"key": "accuracy", "score": accuracy},
        {
            "key": "macro_f1",
            "score": sum(class_scores.values()) / len(class_scores),
        },
    ]
    results.extend(
        {"key": f"f1_{route.lower()}", "score": score}
        for route, score in class_scores.items()
    )
    for expected_route in ROUTE_ORDER:
        for predicted_route in ROUTE_ORDER:
            count = sum(
                e == expected_route and p == predicted_route
                for e, p in zip(expected, predicted)
            )
            results.append(
                {
                    "key": (
                        f"cm_{expected_route.lower()}_to_{predicted_route.lower()}"
                    ),
                    "score": count,
                }
            )
    return results
