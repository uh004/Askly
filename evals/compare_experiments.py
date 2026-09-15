"""Print a compact v1/v2 metric table from two LangSmith experiments."""

from __future__ import annotations

import argparse
import os
from numbers import Real
from typing import Any, Iterable

from dotenv import load_dotenv
from langsmith import Client


QUESTION_METRICS = (
    "groundedness",
    "jd_relevance",
    "personalization",
    "route_compliance",
)
ANSWER_CORE_METRICS = (
    "mae_overall",
)
ANSWER_DIMENSIONS = (
    "relevance",
    "specificity",
    "logical_structure",
    "role_clarity",
    "action_clarity",
    "result_clarity",
)


def _numeric_value(value: Any) -> float | None:
    if isinstance(value, Real) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, dict):
        return None
    for key in ("avg", "mean", "average", "score", "value"):
        candidate = value.get(key)
        if isinstance(candidate, Real) and not isinstance(candidate, bool):
            return float(candidate)
    return None


def _read_scores(client: Client, experiment_name: str) -> dict[str, float]:
    experiment = client.read_project(
        project_name=experiment_name,
        include_stats=True,
    )
    scores: dict[str, float] = {}
    for source in (
        experiment.feedback_stats or {},
        experiment.session_feedback_stats or {},
    ):
        for key, raw_value in source.items():
            value = _numeric_value(raw_value)
            if value is not None:
                scores[key] = value
    return scores


def _change(metric: str, v1: float, v2: float) -> str:
    delta = v2 - v1
    improved = delta < 0 if metric.startswith("mae_") else delta > 0
    if abs(delta) < 0.0005:
        label = "동일"
    else:
        label = "개선" if improved else "하락"
    return f"{delta:+.3f} ({label})"


def _print_table(
    metrics: Iterable[str],
    v1_scores: dict[str, float],
    v2_scores: dict[str, float],
) -> None:
    print("| Metric | v1 | v2 | 변화 |")
    print("|---|---:|---:|---:|")
    for metric in metrics:
        v1 = v1_scores.get(metric)
        v2 = v2_scores.get(metric)
        if v1 is None or v2 is None:
            print(f"| {metric} | - | - | 실험 지표 없음 |")
            continue
        print(f"| {metric} | {v1:.3f} | {v2:.3f} | {_change(metric, v1, v2)} |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("question", "answer"), required=True)
    parser.add_argument("--v1", required=True, help="v1 LangSmith Experiment 이름")
    parser.add_argument("--v2", required=True, help="v2 LangSmith Experiment 이름")
    parser.add_argument(
        "--include-dimensions",
        action="store_true",
        help="답변 평가의 6개 항목별 MAE도 출력합니다.",
    )
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        raise RuntimeError("LANGSMITH_API_KEY가 필요합니다.")

    client = Client(api_key=api_key)
    v1_scores = _read_scores(client, args.v1)
    v2_scores = _read_scores(client, args.v2)

    if args.kind == "question":
        metrics = QUESTION_METRICS
    else:
        metrics = list(ANSWER_CORE_METRICS)
        if args.include_dimensions:
            for dimension in ANSWER_DIMENSIONS:
                metrics.append(f"mae_{dimension}")
    _print_table(metrics, v1_scores, v2_scores)


if __name__ == "__main__":
    main()
