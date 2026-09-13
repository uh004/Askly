"""Local dataset validation and LangSmith upload helpers."""

from __future__ import annotations

import json
from copy import deepcopy
from collections import Counter
from pathlib import Path
from typing import Any

from langsmith import Client
from langsmith.utils import LangSmithNotFoundError


DEFAULT_DATASET_PATH = Path(__file__).with_name("dataset_v1.jsonl")
V2_ADDITIONS_PATH = Path(__file__).with_name("dataset_v2_additions.jsonl")
EXPECTED_QUESTION_TYPES = {"INITIAL", "FOLLOW_UP", "NEXT"}
DATASET_VERSIONS = {"v1", "v2"}
DATASET_SPLITS = {"dev", "holdout"}


def _read_cases(path: Path) -> list[dict[str, Any]]:
    """Read one JSONL file without applying dataset-level balance checks."""

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

    return cases


def load_cases(
    path: Path | None = None,
    *,
    version: str = "v1",
    split: str | None = None,
) -> list[dict[str, Any]]:
    """Load and validate a versioned, optionally split evaluation dataset."""

    if version not in DATASET_VERSIONS:
        raise ValueError(f"지원하지 않는 Dataset 버전입니다: {version}")
    if split is not None and split not in DATASET_SPLITS:
        raise ValueError(f"지원하지 않는 Dataset split입니다: {split}")

    if path is not None:
        cases = _read_cases(path)
    else:
        cases = _read_cases(DEFAULT_DATASET_PATH)
        if version == "v2":
            base_cases = deepcopy(cases)
            for case in base_cases:
                case["metadata"]["split"] = "dev"
                case["metadata"]["dataset_version"] = "v2"
            cases = base_cases + _read_cases(V2_ADDITIONS_PATH)

    case_ids = [case["metadata"]["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("중복된 metadata.case_id가 있습니다.")

    if version == "v2":
        invalid_splits = {
            case["metadata"].get("split") for case in cases
        } - DATASET_SPLITS
        if invalid_splits:
            raise ValueError(f"v2 Case의 split이 올바르지 않습니다: {invalid_splits}")
        if split is not None:
            cases = [case for case in cases if case["metadata"]["split"] == split]

    if not cases:
        raise ValueError("검증 Case가 없습니다.")

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
    dataset_version: str = "v1",
) -> tuple[Any, bool]:
    """Create the dataset once, then reject stale content instead of overwriting it."""

    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        created = False
    except LangSmithNotFoundError:
        dataset = client.create_dataset(
            dataset_name,
            description=(
                "Askly 질문 생성 품질 검증셋: INITIAL/FOLLOW_UP/NEXT 균형 Case "
                f"({dataset_version})"
            ),
            metadata={"version": dataset_version, "task": "question_generation"},
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
        created = True

    examples = list(client.list_examples(dataset_id=dataset.id))
    expected_case_ids = {case["metadata"]["case_id"] for case in cases}
    actual_case_ids = {
        example.metadata.get("case_id")
        for example in examples
        if example.metadata
    }
    if actual_case_ids != expected_case_ids:
        raise RuntimeError(
            f"LangSmith Dataset {dataset_name!r}의 Case가 로컬과 다릅니다. "
            "기존 Dataset을 덮어쓰지 말고 새 버전 이름을 사용하세요."
        )

    for split_name in sorted(DATASET_SPLITS):
        example_ids = [
            example.id
            for example in examples
            if example.metadata and example.metadata.get("split") == split_name
        ]
        if example_ids:
            client.update_dataset_splits(
                dataset_id=dataset.id,
                split_name=split_name,
                example_ids=example_ids,
            )
    return dataset, created
