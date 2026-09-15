"""Reference-score agreement evaluators for answer evaluation."""

from __future__ import annotations

from typing import Any

from evals.answer_evaluation.metrics import SCORE_FIELDS, mean_absolute_error
from src.nodes.answer_evaluation import calculate_overall_score


def score_agreement_evaluator(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
    **_: Any,
) -> list[dict[str, Any]]:
    ai_scores = outputs.get("scores")
    reference_scores = reference_outputs["reference_scores"]
    if not isinstance(ai_scores, dict) or any(
        field not in ai_scores for field in SCORE_FIELDS
    ):
        return [
            {
                "key": "evaluation_output_valid",
                "score": 0,
                "comment": "Target 출력에 완전한 scores가 없습니다.",
            },
            {
                "key": "mae_case",
                "score": 4,
                "comment": "Target 실패를 최대 점수 오차로 처리했습니다.",
            },
            {
                "key": "overall_score_consistency",
                "score": 0,
                "comment": "Target 실패로 종합점수를 확인할 수 없습니다.",
            },
        ]

    ai_values = [float(ai_scores[field]) for field in SCORE_FIELDS]
    reference_values = [float(reference_scores[field]) for field in SCORE_FIELDS]
    differences = {
        field: abs(float(ai_scores[field]) - float(reference_scores[field]))
        for field in SCORE_FIELDS
    }
    expected_overall = calculate_overall_score(ai_scores)
    overall_matches = abs(float(outputs["overall_score"]) - expected_overall) < 0.05
    details = ", ".join(f"{field}={gap:g}" for field, gap in differences.items())
    return [
        {
            "key": "evaluation_output_valid",
            "score": 1,
            "comment": "6개 세부 점수가 모두 생성되었습니다.",
        },
        {
            "key": "mae_case",
            "score": mean_absolute_error(ai_values, reference_values),
            "comment": f"항목별 절대 오차: {details}",
        },
        {
            "key": "overall_score_consistency",
            "score": 1 if overall_matches else 0,
            "comment": (
                f"expected={expected_overall:.1f}, actual={outputs['overall_score']}"
            ),
        },
    ]


def _valid_pairs(
    outputs: list[dict[str, Any]],
    reference_outputs: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    if not outputs or len(outputs) != len(reference_outputs):
        raise ValueError("Summary 평가에는 길이가 같은 결과와 Reference Score가 필요합니다.")
    return [
        (output, reference)
        for output, reference in zip(outputs, reference_outputs)
        if isinstance(output.get("scores"), dict)
        and all(field in output["scores"] for field in SCORE_FIELDS)
    ]


def answer_reliability_summary(
    *,
    outputs: list[dict[str, Any]],
    reference_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return the portfolio-facing overall MAE.

    Every repeated output contributes separately. Invalid outputs receive the
    maximum possible 4-point error so failures cannot improve the result.
    """

    valid_pairs = _valid_pairs(outputs, reference_outputs)
    total_score_slots = len(outputs) * len(SCORE_FIELDS)
    valid_score_slots = len(valid_pairs) * len(SCORE_FIELDS)
    absolute_error = sum(
        abs(float(output["scores"][field]) - float(reference["reference_scores"][field]))
        for output, reference in valid_pairs
        for field in SCORE_FIELDS
    )
    mae_overall = (
        absolute_error + (total_score_slots - valid_score_slots) * 4
    ) / total_score_slots
    return [
        {
            "key": "mae_overall",
            "score": mae_overall,
            "comment": f"유효 출력 {len(valid_pairs)}/{len(outputs)}회",
        }
    ]


def answer_diagnostic_summary(
    *,
    outputs: list[dict[str, Any]],
    reference_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return output coverage and the six dimension-level MAEs."""

    valid_pairs = _valid_pairs(outputs, reference_outputs)
    results: list[dict[str, Any]] = [
        {
            "key": "evaluation_output_coverage",
            "score": len(valid_pairs) / len(outputs),
        }
    ]
    total_attempts = len(outputs)
    for field in SCORE_FIELDS:
        absolute_error = sum(
            abs(
                float(output["scores"][field])
                - float(reference["reference_scores"][field])
            )
            for output, reference in valid_pairs
        )
        invalid_attempts = total_attempts - len(valid_pairs)
        results.append(
            {
                "key": f"mae_{field}",
                "score": (absolute_error + invalid_attempts * 4) / total_attempts,
            }
        )
    return results
