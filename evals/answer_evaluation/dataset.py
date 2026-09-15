"""Answer-evaluation dataset validation and LangSmith upload."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from langsmith import Client
from langsmith.utils import LangSmithNotFoundError

from evals.answer_evaluation.metrics import SCORE_FIELDS
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
QUALITY_LABELS = {"GOOD", "MEDIUM", "POOR"}
QUESTION_TYPES = {"INITIAL", "FOLLOW_UP", "NEXT"}
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
        inputs = case["inputs"]
        for key in (
            "current_question",
            "current_answer",
            "current_competency",
            "question_type",
            "interview_strategy",
        ):
            if not inputs.get(key):
                raise ValueError(f"Case {index}에 inputs.{key}가 필요합니다.")
        if inputs["question_type"] not in QUESTION_TYPES:
            raise ValueError(f"Case {index}의 question_type이 올바르지 않습니다.")

        reference = case["reference_outputs"]
        if reference.get("quality_label") not in QUALITY_LABELS:
            raise ValueError(f"Case {index}의 quality_label이 올바르지 않습니다.")
        scores = reference.get("reference_scores")
        if not isinstance(scores, dict) or set(scores) != set(SCORE_FIELDS):
            raise ValueError(f"Case {index}의 reference_scores 항목이 일치하지 않습니다.")
        if any(
            not isinstance(score, int) or not 1 <= score <= 5
            for score in scores.values()
        ):
            raise ValueError(f"Case {index}의 Reference 점수는 1~5 정수여야 합니다.")

        metadata = case["metadata"]
        if not metadata.get("case_id"):
            raise ValueError(f"Case {index}에 metadata.case_id가 필요합니다.")
        if metadata.get("suite") != suite:
            raise ValueError(
                f"{metadata['case_id']}: suite는 {suite!r}이어야 합니다."
            )
        if not metadata.get("weakness") and suite == "final_holdout":
            raise ValueError(f"{metadata['case_id']}: weakness 진단 태그가 필요합니다.")

    case_ids = [case["metadata"]["case_id"] for case in cases]
    if not cases:
        raise ValueError("검증 Case가 없습니다.")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("중복된 metadata.case_id가 있습니다.")

    quality_counts = Counter(
        case["reference_outputs"]["quality_label"] for case in cases
    )
    type_counts = Counter(case["inputs"]["question_type"] for case in cases)
    if set(quality_counts) != QUALITY_LABELS or len(set(quality_counts.values())) != 1:
        raise ValueError(f"품질 등급별 Case가 균형적이지 않습니다: {dict(quality_counts)}")
    if set(type_counts) != QUESTION_TYPES or len(set(type_counts.values())) != 1:
        raise ValueError(f"질문 유형별 Case가 균형적이지 않습니다: {dict(type_counts)}")

    pair_counts = Counter(
        (case["reference_outputs"]["quality_label"], case["inputs"]["question_type"])
        for case in cases
    )
    expected_pairs = {
        (quality, question_type)
        for quality in QUALITY_LABELS
        for question_type in QUESTION_TYPES
    }
    if set(pair_counts) != expected_pairs or max(pair_counts.values()) - min(pair_counts.values()) > 1:
        raise ValueError(
            f"품질 등급×질문 유형은 조합별 1건 차이 이내여야 합니다: {dict(pair_counts)}"
        )
    if suite == "final_holdout" and (
        set(quality_counts.values()) != {10} or set(type_counts.values()) != {10}
    ):
        raise ValueError("Final Holdout은 품질 등급과 질문 유형별 각각 10건이어야 합니다.")
    return cases


def pending_reference_reviews(cases: list[dict[str, Any]]) -> list[str]:
    return [
        case["metadata"]["case_id"]
        for case in cases
        if case["metadata"].get("reference_review_status") != "approved"
    ]


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
                "Askly 답변 평가 신뢰성 검증: GOOD/MEDIUM/POOR 균형 사례 "
                f"({suite}, {DATASET_VERSION})"
            ),
            metadata={
                "version": DATASET_VERSION,
                "suite": suite,
                "task": "answer_evaluation",
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
