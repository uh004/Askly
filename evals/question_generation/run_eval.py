"""Validate locally or run the question-generation experiment in LangSmith."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from langsmith import Client

from evals.question_generation.dataset import ensure_langsmith_dataset, load_cases
from evals.question_generation.evaluators import (
    question_quality_diagnostics_evaluator,
    question_quality_evaluator,
    route_compliance_evaluator,
)
from evals.question_generation.target import make_question_generation_target
from src.nodes.question_generation import select_question_context


DEFAULT_DATASET_NAME_TEMPLATE = "askly-question-generation-{version}"


def validate_locally(
    *,
    dataset_version: str = "v1",
    split: str | None = None,
) -> list[dict]:
    """Validate dataset structure and deterministic routing without API calls."""

    cases = load_cases(version=dataset_version, split=split)
    for case in cases:
        competency, question_type = select_question_context(case["inputs"])
        expected = case["reference_outputs"]
        if question_type != expected["expected_question_type"]:
            raise AssertionError(
                f"{case['metadata']['case_id']}: expected question_type "
                f"{expected['expected_question_type']}, got {question_type}"
            )
        if competency != expected["expected_competency"]:
            raise AssertionError(
                f"{case['metadata']['case_id']}: expected competency "
                f"{expected['expected_competency']}, got {competency}"
            )
    return cases


def require_environment(*names: str) -> None:
    missing = [
        name
        for name in names
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            "LangSmith 평가 실행에 필요한 환경변수가 없습니다: " + ", ".join(missing)
        )


def check_langsmith_connection() -> None:
    """Verify the LangSmith key without running an LLM evaluation."""

    require_environment("LANGSMITH_API_KEY")
    client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
    next(client.list_datasets(limit=1), None)
    print("LangSmith 연결 확인 완료")


def run_langsmith_experiment(
    dataset_name: str,
    experiment_prefix: str,
    *,
    dataset_version: str = "v1",
    split: str | None = None,
    prompt_version: str = "v1",
    include_diagnostics: bool = False,
) -> None:
    require_environment("OPENAI_API_KEY", "LANGSMITH_API_KEY")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "askly-agent-eval")

    all_cases = validate_locally(dataset_version=dataset_version)
    selected_cases = validate_locally(
        dataset_version=dataset_version,
        split=split,
    )
    client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
    dataset, created = ensure_langsmith_dataset(
        client,
        dataset_name=dataset_name,
        cases=all_cases,
        dataset_version=dataset_version,
    )
    action = "생성 및 업로드" if created else "기존 Dataset 재사용"
    print(f"LangSmith Dataset: {dataset.name} ({action})")

    quality_evaluator = (
        question_quality_diagnostics_evaluator
        if include_diagnostics
        else question_quality_evaluator
    )
    data = dataset_name
    if split is not None:
        data = list(
            client.list_examples(
                dataset_id=dataset.id,
                splits=[split],
            )
        )
        if len(data) != len(selected_cases):
            raise RuntimeError(
                f"LangSmith {split} split Case 수 불일치: "
                f"expected={len(selected_cases)}, actual={len(data)}"
            )

    results = client.evaluate(
        make_question_generation_target(prompt_version),
        data=data,
        evaluators=[route_compliance_evaluator, quality_evaluator],
        experiment_prefix=experiment_prefix,
        description=(
            f"Askly 질문 생성 {prompt_version} 진단 포함 평가"
            if include_diagnostics
            else f"Askly 질문 생성 {prompt_version} 핵심 지표 평가"
        ),
        metadata={
            "dataset_version": dataset_version,
            "dataset_split": split or "all",
            "prompt_version": prompt_version,
            "node": "question_generation",
            "evaluation_profile": "diagnostics" if include_diagnostics else "core",
        },
        max_concurrency=1,
    )
    print(f"LangSmith Experiment: {results.experiment_name}")
    print(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-langsmith",
        action="store_true",
        help="Dataset을 업로드하고 LangSmith 평가 Experiment를 실행합니다.",
    )
    parser.add_argument(
        "--check-langsmith",
        action="store_true",
        help="LLM 호출 없이 LangSmith API Key 연결만 확인합니다.",
    )
    parser.add_argument("--dataset-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--dataset-name")
    parser.add_argument("--split", choices=("all", "dev", "holdout"), default="all")
    parser.add_argument("--prompt-version", choices=("v1", "v2"), default="v1")
    parser.add_argument(
        "--experiment-prefix",
    )
    parser.add_argument(
        "--include-diagnostics",
        action="store_true",
        help="FOLLOW_UP 적합성과 근거 없는 가정 진단 지표를 함께 기록합니다.",
    )
    args = parser.parse_args()

    load_dotenv()
    selected_split = None if args.split == "all" else args.split
    dataset_name = args.dataset_name or DEFAULT_DATASET_NAME_TEMPLATE.format(
        version=args.dataset_version
    )
    experiment_prefix = args.experiment_prefix or (
        f"question-generation-{args.prompt_version}-{args.split}"
    )
    cases = validate_locally(
        dataset_version=args.dataset_version,
        split=selected_split,
    )
    print(f"로컬 검증 완료: {len(cases)}개 Case")

    if args.check_langsmith:
        check_langsmith_connection()
        return

    if not args.run_langsmith:
        print("API 호출은 하지 않았습니다. 실행하려면 --run-langsmith를 추가하세요.")
        return

    run_langsmith_experiment(
        dataset_name,
        experiment_prefix,
        dataset_version=args.dataset_version,
        split=selected_split,
        prompt_version=args.prompt_version,
        include_diagnostics=args.include_diagnostics,
    )


if __name__ == "__main__":
    main()
