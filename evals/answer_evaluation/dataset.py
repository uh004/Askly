"""Answer-evaluation dataset validation and LangSmith upload."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from langsmith import Client
from langsmith.utils import LangSmithNotFoundError

from evals.answer_evaluation.metrics import SCORE_FIELDS


DEFAULT_DATASET_PATH = Path(__file__).with_name("dataset_v1.jsonl")
QUALITY_LABELS = {"GOOD", "MEDIUM", "POOR"}
QUESTION_TYPES = {"INITIAL", "FOLLOW_UP", "NEXT"}


def load_cases(path: Path = DEFAULT_DATASET_PATH) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            if not raw_line.strip():
                continue
            try:
                case = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} JSON 형식 오류: {exc}") from exc

            for key in ("inputs", "reference_outputs", "metadata"):
                if not isinstance(case.get(key), dict):
                    raise ValueError(f"{path}:{line_number}에 dict 타입 {key}가 필요합니다.")

            inputs = case["inputs"]
            for key in (
                "current_question",
                "current_answer",
                "current_competency",
                "question_type",
                "interview_strategy",
            ):
                if not inputs.get(key):
                    raise ValueError(f"{path}:{line_number} inputs.{key}가 필요합니다.")
            if inputs["question_type"] not in QUESTION_TYPES:
                raise ValueError(f"{path}:{line_number} question_type이 올바르지 않습니다.")

            reference = case["reference_outputs"]
            if reference.get("quality_label") not in QUALITY_LABELS:
                raise ValueError(f"{path}:{line_number} quality_label이 올바르지 않습니다.")
            human_scores = reference.get("human_scores")
            if not isinstance(human_scores, dict) or set(human_scores) != set(SCORE_FIELDS):
                raise ValueError(f"{path}:{line_number} human_scores 항목이 일치하지 않습니다.")
            if any(
                not isinstance(score, int) or not 1 <= score <= 5
                for score in human_scores.values()
            ):
                raise ValueError(f"{path}:{line_number} Human 점수는 1~5 정수여야 합니다.")
            if not case["metadata"].get("case_id"):
                raise ValueError(f"{path}:{line_number} metadata.case_id가 필요합니다.")
            cases.append(case)

    if not cases:
        raise ValueError(f"검증 Case가 없습니다: {path}")

    quality_counts = Counter(
        case["reference_outputs"]["quality_label"] for case in cases
    )
    type_counts = Counter(case["inputs"]["question_type"] for case in cases)
    if set(quality_counts) != QUALITY_LABELS or len(set(quality_counts.values())) != 1:
        raise ValueError(f"품질 등급별 Case가 균형적이지 않습니다: {dict(quality_counts)}")
    if set(type_counts) != QUESTION_TYPES or len(set(type_counts.values())) != 1:
        raise ValueError(f"질문 유형별 Case가 균형적이지 않습니다: {dict(type_counts)}")
    return cases


def ensure_langsmith_dataset(
    client: Client,
    *,
    dataset_name: str,
    cases: list[dict[str, Any]],
) -> tuple[Any, bool]:
    try:
        return client.read_dataset(dataset_name=dataset_name), False
    except LangSmithNotFoundError:
        dataset = client.create_dataset(
            dataset_name,
            description="Askly 답변 평가 신뢰성 검증셋: GOOD/MEDIUM/POOR 균형 Case",
            metadata={"version": "v1", "task": "answer_evaluation"},
        )
        client.create_examples(
            dataset_id=dataset.id,
            examples=[
                {
                    "inputs": case["inputs"],
                    "outputs": case["reference_outputs"],
                    "metadata": case["metadata"],
                }
                for case in cases
            ],
        )
        return dataset, True
