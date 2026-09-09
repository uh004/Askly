"""Code and LLM-as-a-Judge evaluators for generated questions."""

from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class RubricScore(BaseModel):
    score: int = Field(ge=1, le=5)
    reason: str = Field(min_length=1, max_length=500)


class QuestionQualityJudgment(BaseModel):
    groundedness: RubricScore
    jd_relevance: RubricScore
    personalization: RubricScore
    followup_relevance: RubricScore | None = None
    unsupported_assumption: bool
    unsupported_assumption_reason: str = Field(default="", max_length=500)


_judge_chain: Any | None = None


def _build_judge_chain() -> Any:
    judge_llm = ChatOpenAI(
        model=os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini"),
        temperature=0,
    )
    structured_judge = judge_llm.with_structured_output(
        QuestionQualityJudgment,
        method="function_calling",
        include_raw=False,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "당신은 AI 면접 질문 품질을 평가하는 엄격한 심사자입니다. "
                "제공된 지원자 정보, 채용공고, 이전 답변과 평가에 명시된 사실만 "
                "근거로 사용하세요. 각 1~5점은 rubric.md 기준으로 평가하세요. "
                "FOLLOW_UP이 아니면 followup_relevance는 null로 반환하세요. "
                "질문이 존재하지 않는 경험·기술·수치·역할을 사실처럼 전제하면 "
                "unsupported_assumption을 true로 판단하세요.",
            ),
            (
                "human",
                "[Node 입력]\n{inputs}\n\n"
                "[생성 결과]\n{outputs}\n\n"
                "[기대값과 평가 근거]\n{reference_outputs}",
            ),
        ]
    )
    return prompt | structured_judge


def _get_judge_chain() -> Any:
    global _judge_chain
    if _judge_chain is None:
        _judge_chain = _build_judge_chain()
    return _judge_chain


def route_compliance_evaluator(
    *,
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
    **_: Any,
) -> dict[str, Any]:
    """Compare generated type/competency with deterministic expectations."""

    expected_type = reference_outputs.get("expected_question_type")
    expected_competency = reference_outputs.get("expected_competency")
    actual_type = outputs.get("question_type")
    actual_competency = outputs.get("competency")
    passed = actual_type == expected_type and actual_competency == expected_competency
    return {
        "key": "route_compliance",
        "score": 1 if passed else 0,
        "comment": (
            f"expected=({expected_type}, {expected_competency}), "
            f"actual=({actual_type}, {actual_competency})"
        ),
    }


def question_quality_evaluator(
    *,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
    **_: Any,
) -> list[dict[str, Any]]:
    """Score semantic quality with one structured LLM judge call."""

    judgment: QuestionQualityJudgment = _get_judge_chain().invoke(
        {
            "inputs": json.dumps(inputs, ensure_ascii=False, indent=2),
            "outputs": json.dumps(outputs, ensure_ascii=False, indent=2),
            "reference_outputs": json.dumps(
                reference_outputs, ensure_ascii=False, indent=2
            ),
        }
    )

    assumption_reason = judgment.unsupported_assumption_reason.strip()
    if not assumption_reason:
        assumption_reason = (
            "Judge가 근거 없는 가정을 발견했지만 판단 이유를 제공하지 않았습니다."
            if judgment.unsupported_assumption
            else "근거 없는 가정이 발견되지 않았습니다."
        )

    results: list[dict[str, Any]] = [
        {
            "key": "groundedness",
            "score": judgment.groundedness.score,
            "comment": judgment.groundedness.reason,
        },
        {
            "key": "jd_relevance",
            "score": judgment.jd_relevance.score,
            "comment": judgment.jd_relevance.reason,
        },
        {
            "key": "personalization",
            "score": judgment.personalization.score,
            "comment": judgment.personalization.reason,
        },
        {
            "key": "unsupported_assumption_free",
            "score": 0 if judgment.unsupported_assumption else 1,
            "comment": assumption_reason,
        },
    ]

    if reference_outputs.get("expected_question_type") == "FOLLOW_UP":
        followup = judgment.followup_relevance
        results.append(
            {
                "key": "followup_relevance",
                "score": followup.score if followup else 1,
                "comment": (
                    followup.reason
                    if followup
                    else "Judge가 FOLLOW_UP 점수를 반환하지 않았습니다."
                ),
            }
        )

    return results
