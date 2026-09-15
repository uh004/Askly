"""Validate or run a question-generation evaluation suite."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from langsmith import Client

from evals.dataset_utils import dataset_content_hash
from evals.question_generation.dataset import (
    DATASET_VERSION,
    ensure_langsmith_dataset,
    load_cases,
)
from evals.question_generation.evaluators import (
    question_quality_diagnostics_evaluator,
    question_quality_evaluator,
    route_compliance_evaluator,
)
from evals.question_generation.target import make_question_generation_target
from src.nodes.question_generation import select_question_context


def validate_locally(*, suite: str = "regression") -> list[dict]:
    """Validate structure and deterministic question context without API calls."""

    cases = load_cases(suite=suite)
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
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError("평가 실행에 필요한 환경변수가 없습니다: " + ", ".join(missing))


def check_langsmith_connection() -> None:
    require_environment("LANGSMITH_API_KEY")
    client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
    next(client.list_datasets(limit=1), None)
    print("LangSmith 연결 확인 완료")


def run_langsmith_experiment(
    dataset_name: str,
    experiment_prefix: str,
    *,
    suite: str,
    prompt_version: str,
    num_repetitions: int,
    include_diagnostics: bool = False,
) -> None:
    require_environment("OPENAI_API_KEY", "LANGSMITH_API_KEY")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "askly-agent-eval")
    cases = validate_locally(suite=suite)
    client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
    dataset, created = ensure_langsmith_dataset(
        client,
        dataset_name=dataset_name,
        cases=cases,
        suite=suite,
    )
    print(f"LangSmith Dataset: {dataset.name} ({'생성' if created else '재사용'})")
    quality_evaluator = (
        question_quality_diagnostics_evaluator
        if include_diagnostics
        else question_quality_evaluator
    )
    results = client.evaluate(
        make_question_generation_target(prompt_version),
        data=dataset_name,
        evaluators=[route_compliance_evaluator, quality_evaluator],
        experiment_prefix=experiment_prefix,
        description=f"Askly 질문 생성 {suite} 평가",
        metadata={
            "dataset_version": DATASET_VERSION,
            "dataset_suite": suite,
            "dataset_sha256": dataset_content_hash(cases),
            "prompt_version": prompt_version,
            "generation_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "judge_model": os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini"),
            "num_repetitions": num_repetitions,
            "node": "question_generation",
            "evaluation_profile": "diagnostics" if include_diagnostics else "core",
        },
        num_repetitions=num_repetitions,
        max_concurrency=1,
    )
    results.wait()
    print(f"LangSmith Experiment: {results.experiment_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-langsmith", action="store_true")
    parser.add_argument("--check-langsmith", action="store_true")
    parser.add_argument(
        "--suite", choices=("regression", "final_holdout"), default="regression"
    )
    parser.add_argument("--dataset-name")
    parser.add_argument("--prompt-version", choices=("v1", "v2"), default="v2")
    parser.add_argument("--experiment-prefix")
    parser.add_argument("--num-repetitions", type=int, default=3)
    parser.add_argument("--include-diagnostics", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    if args.num_repetitions < 1:
        parser.error("--num-repetitions는 1 이상이어야 합니다.")

    cases = validate_locally(suite=args.suite)
    print(
        f"로컬 검증 완료: suite={args.suite}, cases={len(cases)}, "
        f"repetitions={args.num_repetitions}"
    )
    if args.check_langsmith:
        check_langsmith_connection()
        return
    if not args.run_langsmith:
        print("API 호출 없음: --run-langsmith를 추가하면 실험을 실행합니다.")
        return

    dataset_name = args.dataset_name or (
        f"askly-question-generation-{args.suite.replace('_', '-')}-{DATASET_VERSION}"
    )
    experiment_prefix = args.experiment_prefix or (
        f"question-generation-{args.suite}-{args.prompt_version}"
    )
    run_langsmith_experiment(
        dataset_name,
        experiment_prefix,
        suite=args.suite,
        prompt_version=args.prompt_version,
        num_repetitions=args.num_repetitions,
        include_diagnostics=args.include_diagnostics,
    )


if __name__ == "__main__":
    main()
