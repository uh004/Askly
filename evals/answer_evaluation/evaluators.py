"""Human-score agreement and answer-grounding evaluators."""

from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from evals.answer_evaluation.metrics import (
    SCORE_FIELDS,
    mean_absolute_error,
    spearman_correlation,
    within_one_agreement,
)
from src.nodes.answer_evaluation import calculate_overall_score


class JudgeScore(BaseModel):
    score: int = Field(ge=1, le=5)
    reason: str = Field(default="", max_length=500)


class AnswerSupportJudgment(BaseModel):
    evidence_groundedness: JudgeScore
    missing_point_validity: JudgeScore


_support_judge_chain: Any | None = None


def _build_support_judge_chain() -> Any:
    llm = ChatOpenAI(
        model=os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini"),
        temperature=0,
    )
    structured_llm = llm.with_structured_output(
        AnswerSupportJudgment,
        method="function_calling",
        include_raw=False,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "당신은 면접 답변 평가 결과의 근거성을 검증하는 심사자입니다. "
                "Evidence Groundedness는 answer_evidence와 평가 설명이 실제 사용자 "
                "답변에 근거하면 5점, 답변에 없는 사실을 근거로 사용하면 1점입니다. "
                "답변에 인용할 내용이 없어 evidence가 빈 목록인 것은 적절할 수 있습니다. "
                "Missing Point Validity는 missing_points가 질문 의도, 검증 항목, 실제 "
                "답변에서 빠진 내용을 정확히 지적하면 5점, 이미 답한 내용이나 질문과 "
                "무관한 내용을 부족하다고 하면 1점입니다. 입력에 없는 사실을 만들지 마세요.",
            ),
            (
                "human",
                "[Node 입력]\n{inputs}\n\n"
                "[AI 평가 결과]\n{outputs}\n\n"
                "[Human 기준]\n{reference_outputs}",
            ),
        ]
    )
    return prompt | structured_llm


def _get_support_judge_chain() -> Any:
    global _support_judge_chain
    if _support_judge_chain is None:
        _support_judge_chain = _build_support_judge_chain()
    return _support_judge_chain


def score_agreement_evaluator(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
    **_: Any,
) -> list[dict[str, Any]]:
    ai_scores = outputs.get("scores")
    human_scores = reference_outputs["human_scores"]
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
                "key": "within_1_agreement_case",
                "score": 0,
                "comment": "Target 실패로 점수를 비교할 수 없습니다.",
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
    human_values = [float(human_scores[field]) for field in SCORE_FIELDS]
    differences = {
        field: abs(float(ai_scores[field]) - float(human_scores[field]))
        for field in SCORE_FIELDS
    }
    details = ", ".join(f"{field}={gap:g}" for field, gap in differences.items())
    expected_overall = calculate_overall_score(ai_scores)
    overall_matches = abs(float(outputs["overall_score"]) - expected_overall) < 0.05
    return [
        {
            "key": "evaluation_output_valid",
            "score": 1,
            "comment": "6개 세부 점수가 모두 생성되었습니다.",
        },
        {
            "key": "within_1_agreement_case",
            "score": within_one_agreement(ai_values, human_values),
            "comment": f"항목별 절대 오차: {details}",
        },
        {
            "key": "mae_case",
            "score": mean_absolute_error(ai_values, human_values),
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


def answer_support_evaluator(
    *,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
    **_: Any,
) -> list[dict[str, Any]]:
    if not isinstance(outputs.get("scores"), dict):
        return [
            {
                "key": "evidence_groundedness",
                "score": 1,
                "comment": "Target 실패로 평가 근거를 확인할 수 없습니다.",
            },
            {
                "key": "missing_point_validity",
                "score": 1,
                "comment": "Target 실패로 누락 항목을 확인할 수 없습니다.",
            },
        ]

    judgment: AnswerSupportJudgment = _get_support_judge_chain().invoke(
        {
            "inputs": json.dumps(inputs, ensure_ascii=False, indent=2),
            "outputs": json.dumps(outputs, ensure_ascii=False, indent=2),
            "reference_outputs": json.dumps(
                reference_outputs, ensure_ascii=False, indent=2
            ),
        }
    )
    evidence_reason = (
        judgment.evidence_groundedness.reason.strip() or "평가 이유가 제공되지 않았습니다."
    )
    missing_reason = (
        judgment.missing_point_validity.reason.strip() or "평가 이유가 제공되지 않았습니다."
    )
    return [
        {
            "key": "evidence_groundedness",
            "score": judgment.evidence_groundedness.score,
            "comment": evidence_reason,
        },
        {
            "key": "missing_point_validity",
            "score": judgment.missing_point_validity.score,
            "comment": missing_reason,
        },
    ]


def answer_reliability_summary(
    *,
    outputs: list[dict[str, Any]],
    reference_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not outputs or len(outputs) != len(reference_outputs):
        raise ValueError("Summary 평가에는 길이가 같은 결과와 Human Label이 필요합니다.")

    valid_pairs = [
        (output, reference)
        for output, reference in zip(outputs, reference_outputs)
        if isinstance(output.get("scores"), dict)
        and all(field in output["scores"] for field in SCORE_FIELDS)
    ]
    coverage = len(valid_pairs) / len(outputs)
    results: list[dict[str, Any]] = [
        {"key": "evaluation_output_coverage", "score": coverage}
    ]
    if not valid_pairs:
        return results

    all_ai: list[float] = []
    all_human: list[float] = []
    for field in SCORE_FIELDS:
        ai_values = [float(output["scores"][field]) for output, _ in valid_pairs]
        human_values = [
            float(reference["human_scores"][field]) for _, reference in valid_pairs
        ]
        all_ai.extend(ai_values)
        all_human.extend(human_values)
        results.extend(
            [
                {
                    "key": f"within1_{field}",
                    "score": within_one_agreement(ai_values, human_values),
                },
                {
                    "key": f"mae_{field}",
                    "score": mean_absolute_error(ai_values, human_values),
                },
                {
                    "key": f"spearman_{field}",
                    "score": (
                        spearman_correlation(ai_values, human_values)
                        if len(ai_values) >= 2
                        else 0.0
                    ),
                },
            ]
        )

    results.extend(
        [
            {
                "key": "within1_overall",
                "score": within_one_agreement(all_ai, all_human),
            },
            {"key": "mae_overall", "score": mean_absolute_error(all_ai, all_human)},
            {
                "key": "spearman_overall",
                "score": (
                    spearman_correlation(all_ai, all_human)
                    if len(all_ai) >= 2
                    else 0.0
                ),
            },
        ]
    )
    return results
