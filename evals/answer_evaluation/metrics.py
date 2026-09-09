"""Dependency-free reliability metrics used by answer evaluation."""

from __future__ import annotations

from math import sqrt
from typing import Sequence


SCORE_FIELDS = (
    "relevance",
    "specificity",
    "logical_structure",
    "role_clarity",
    "action_clarity",
    "result_clarity",
)


def mean_absolute_error(actual: Sequence[float], expected: Sequence[float]) -> float:
    if len(actual) != len(expected) or not actual:
        raise ValueError("MAE 계산에는 길이가 같은 비어 있지 않은 두 점수 목록이 필요합니다.")
    return sum(abs(a - e) for a, e in zip(actual, expected)) / len(actual)


def within_one_agreement(actual: Sequence[float], expected: Sequence[float]) -> float:
    if len(actual) != len(expected) or not actual:
        raise ValueError(
            "Within-1 계산에는 길이가 같은 비어 있지 않은 두 점수 목록이 필요합니다."
        )
    return sum(abs(a - e) <= 1 for a, e in zip(actual, expected)) / len(actual)


def _average_ranks(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index + 1
        while end < len(indexed) and indexed[end][1] == indexed[index][1]:
            end += 1
        average_rank = ((index + 1) + end) / 2
        for offset in range(index, end):
            ranks[indexed[offset][0]] = average_rank
        index = end
    return ranks


def spearman_correlation(actual: Sequence[float], expected: Sequence[float]) -> float:
    """Compute Spearman rank correlation with average ranks for ties."""

    if len(actual) != len(expected) or len(actual) < 2:
        raise ValueError("Spearman 계산에는 길이가 같은 두 개 이상의 점수가 필요합니다.")
    actual_ranks = _average_ranks(actual)
    expected_ranks = _average_ranks(expected)
    actual_mean = sum(actual_ranks) / len(actual_ranks)
    expected_mean = sum(expected_ranks) / len(expected_ranks)
    numerator = sum(
        (a - actual_mean) * (e - expected_mean)
        for a, e in zip(actual_ranks, expected_ranks)
    )
    actual_scale = sqrt(sum((a - actual_mean) ** 2 for a in actual_ranks))
    expected_scale = sqrt(sum((e - expected_mean) ** 2 for e in expected_ranks))
    if actual_scale == 0 or expected_scale == 0:
        return 0.0
    return numerator / (actual_scale * expected_scale)
