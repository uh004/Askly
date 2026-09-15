"""Question-generation dataset validation and LangSmith upload."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from langsmith import Client
from langsmith.utils import LangSmithNotFoundError

from evals.dataset_utils import (
    EVAL_SUITES,
    dataset_content_hash,
    read_jsonl,
    remote_examples_hash,
)


DATASET_DIR = Path(__file__).with_name("datasets")
DATASET_PATHS = {
    "regression": DATASET_DIR / "regression_v1.jsonl",
    "final_holdout": DATASET_DIR / "final_holdout_v1.jsonl",
}
EXPECTED_QUESTION_TYPES = {"INITIAL", "FOLLOW_UP", "NEXT"}
DATASET_VERSION = "v1"


def load_cases(
    path: Path | None = None,
    *,
    suite: str = "regression",
) -> list[dict[str, Any]]:
    if suite not in EVAL_SUITES:
        raise ValueError(f"지원하지 않는 평가 suite입니다: {suite}")
    cases = read_jsonl(path or DATASET_PATHS[suite])

    for index, case in enumerate(cases, start=1):
        for key in ("inputs", "reference_outputs", "metadata"):
            if not isinstance(case.get(key), dict):
                raise ValueError(f"Case {index}에 dict 타입 {key}가 필요합니다.")
        expected = case["reference_outputs"]
        if expected.get("expected_question_type") not in EXPECTED_QUESTION_TYPES:
            raise ValueError(f"Case {index}의 expected_question_type이 올바르지 않습니다.")
        if not expected.get("expected_competency"):
            raise ValueError(f"Case {index}에 expected_competency가 필요합니다.")
        metadata = case["metadata"]
        if not metadata.get("case_id"):
            raise ValueError(f"Case {index}에 metadata.case_id가 필요합니다.")
        if metadata.get("suite") != suite:
            raise ValueError(
                f"{metadata['case_id']}: suite는 {suite!r}이어야 합니다."
            )
        if not metadata.get("scenario"):
            raise ValueError(f"{metadata['case_id']}: scenario가 필요합니다.")

    case_ids = [case["metadata"]["case_id"] for case in cases]
    if not cases:
        raise ValueError("검증 Case가 없습니다.")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("중복된 metadata.case_id가 있습니다.")

    counts = Counter(
        case["reference_outputs"]["expected_question_type"] for case in cases
    )
    if set(counts) != EXPECTED_QUESTION_TYPES or len(set(counts.values())) != 1:
        raise ValueError(f"질문 유형별 Case 수가 균형적이지 않습니다: {dict(counts)}")
    if suite == "final_holdout" and set(counts.values()) != {10}:
        raise ValueError(f"Final Holdout은 질문 유형별 10건이어야 합니다: {dict(counts)}")
    return cases


def ensure_langsmith_dataset(
    client: Client,
    *,
    dataset_name: str,
    cases: list[dict[str, Any]],
    suite: str,
) -> tuple[Any, bool]:
    content_hash = dataset_content_hash(cases)
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        created = False
    except LangSmithNotFoundError:
        dataset = client.create_dataset(
            dataset_name,
            description=(
                "Askly 질문 생성 평가: INITIAL/FOLLOW_UP/NEXT 균형 사례 "
                f"({suite}, {DATASET_VERSION})"
            ),
            metadata={
                "version": DATASET_VERSION,
                "suite": suite,
                "task": "question_generation",
                "content_sha256": content_hash,
            },
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
    if remote_examples_hash(examples) != content_hash:
        raise RuntimeError(
            f"LangSmith Dataset {dataset_name!r}의 내용이 로컬과 다릅니다. "
            "기존 Dataset을 덮어쓰지 말고 새 버전 이름을 사용하세요."
        )
    return dataset, created
