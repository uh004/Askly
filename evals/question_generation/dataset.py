"""Local dataset validation and LangSmith upload helpers."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from langsmith import Client
from langsmith.utils import LangSmithNotFoundError


DEFAULT_DATASET_PATH = Path(__file__).with_name("dataset_v1.jsonl")
EXPECTED_QUESTION_TYPES = {"INITIAL", "FOLLOW_UP", "NEXT"}


def load_cases(path: Path = DEFAULT_DATASET_PATH) -> list[dict[str, Any]]:
    """Load and validate JSONL evaluation cases."""

    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} JSON 형식 오류: {exc}") from exc

            for key in ("inputs", "reference_outputs", "metadata"):
                if key not in case or not isinstance(case[key], dict):
                    raise ValueError(f"{path}:{line_number}에 dict 타입 {key}가 필요합니다.")

            expected_type = case["reference_outputs"].get("expected_question_type")
            if expected_type not in EXPECTED_QUESTION_TYPES:
                raise ValueError(
                    f"{path}:{line_number} expected_question_type이 올바르지 않습니다: "
                    f"{expected_type!r}"
                )
            if not case["reference_outputs"].get("expected_competency"):
                raise ValueError(f"{path}:{line_number} expected_competency가 필요합니다.")
            if not case["metadata"].get("case_id"):
                raise ValueError(f"{path}:{line_number} metadata.case_id가 필요합니다.")
            cases.append(case)

    if not cases:
        raise ValueError(f"검증 Case가 없습니다: {path}")

    counts = Counter(
        case["reference_outputs"]["expected_question_type"] for case in cases
    )
    missing_types = EXPECTED_QUESTION_TYPES - set(counts)
    if missing_types:
        raise ValueError(f"질문 유형 Case가 누락되었습니다: {sorted(missing_types)}")
    if len(set(counts.values())) != 1:
        raise ValueError(f"질문 유형별 Case 수가 균형적이지 않습니다: {dict(counts)}")

    return cases


def ensure_langsmith_dataset(
    client: Client,
    *,
    dataset_name: str,
    cases: list[dict[str, Any]],
) -> tuple[Any, bool]:
    """Create and upload the dataset once, or reuse it if it already exists."""

    try:
        return client.read_dataset(dataset_name=dataset_name), False
    except LangSmithNotFoundError:
        dataset = client.create_dataset(
            dataset_name,
            description=(
                "Askly 질문 생성 품질 검증셋: INITIAL/FOLLOW_UP/NEXT 균형 Case"
            ),
            metadata={"version": "v1", "task": "question_generation"},
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
