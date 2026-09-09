"""Router dataset validation and LangSmith upload."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from langsmith import Client
from langsmith.utils import LangSmithNotFoundError


DEFAULT_DATASET_PATH = Path(__file__).with_name("dataset_v1.jsonl")
ROUTES = {"FOLLOW_UP", "NEXT", "END"}


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
                "current_evaluation",
                "current_competency",
                "target_competencies",
                "interview_history",
                "question_count",
                "followup_count",
            ):
                if key not in inputs:
                    raise ValueError(f"{path}:{line_number} inputs.{key}가 필요합니다.")
            expected_route = case["reference_outputs"].get("expected_route")
            if expected_route not in ROUTES:
                raise ValueError(f"{path}:{line_number} expected_route가 올바르지 않습니다.")
            if not case["metadata"].get("case_id"):
                raise ValueError(f"{path}:{line_number} metadata.case_id가 필요합니다.")
            if not case["metadata"].get("boundary"):
                raise ValueError(f"{path}:{line_number} metadata.boundary가 필요합니다.")
            cases.append(case)

    if not cases:
        raise ValueError(f"검증 Case가 없습니다: {path}")
    counts = Counter(case["reference_outputs"]["expected_route"] for case in cases)
    if set(counts) != ROUTES or len(set(counts.values())) != 1:
        raise ValueError(f"Route별 Case가 균형적이지 않습니다: {dict(counts)}")
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
            description="Askly Router 검증셋: FOLLOW_UP/NEXT/END 균형 및 경계값 Case",
            metadata={"version": "v1", "task": "router"},
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
