"""Validate or run an answer-evaluation reliability suite."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from langsmith import Client

from evals.answer_evaluation.dataset import (
    DATASET_VERSION,
    ensure_langsmith_dataset,
    load_cases,
    pending_reference_reviews,
)
from evals.answer_evaluation.evaluators import (
    answer_diagnostic_summary,
    answer_reliability_summary,
    score_agreement_evaluator,
)
from evals.answer_evaluation.target import make_answer_evaluation_target
from evals.dataset_utils import dataset_content_hash
from src.nodes.answer_evaluation import calculate_overall_score


def validate_locally(*, suite: str = "regression") -> list[dict]:
    cases = load_cases(suite=suite)
    for case in cases:
        overall = calculate_overall_score(
            case["reference_outputs"]["reference_scores"]
        )
        if not 20 <= overall <= 100:
            raise AssertionError(f"Reference 종합 점수 범위 오류: {overall}")
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
    per_case_evaluators = [score_agreement_evaluator] if include_diagnostics else []
    summary_evaluators = [answer_reliability_summary]
    if include_diagnostics:
        summary_evaluators.append(answer_diagnostic_summary)
    results = client.evaluate(
        make_answer_evaluation_target(prompt_version),
        data=dataset_name,
        evaluators=per_case_evaluators,
        summary_evaluators=summary_evaluators,
        experiment_prefix=experiment_prefix,
        description=f"Askly 답변 평가 {suite} 신뢰성 검증",
        metadata={
            "dataset_version": DATASET_VERSION,
            "dataset_suite": suite,
            "dataset_sha256": dataset_content_hash(cases),
            "prompt_version": prompt_version,
            "generation_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "num_repetitions": num_repetitions,
            "node": "answer_evaluation",
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
    parser.add_argument(
        "--confirm-reference-reviewed",
        action="store_true",
        help="Final Holdout의 Reference Score를 직접 검토했음을 확인합니다.",
    )
    args = parser.parse_args()
    load_dotenv()
    if args.num_repetitions < 1:
        parser.error("--num-repetitions는 1 이상이어야 합니다.")

    cases = validate_locally(suite=args.suite)
    pending = pending_reference_reviews(cases) if args.suite == "final_holdout" else []
    print(
        f"로컬 검증 완료: suite={args.suite}, cases={len(cases)}, "
        f"repetitions={args.num_repetitions}"
    )
    if pending:
        print(f"Reference 검토 표시 대기: {len(pending)}건")
    if args.check_langsmith:
        check_langsmith_connection()
        return
    if not args.run_langsmith:
        print("API 호출 없음: --run-langsmith를 추가하면 실험을 실행합니다.")
        return
    if args.suite == "final_holdout" and pending:
        raise RuntimeError(
            "Final Holdout Reference Score 검토가 끝나지 않았습니다. "
            "먼저 `python -m tools.review_answer_holdout`을 실행하세요."
        )
    if args.suite == "final_holdout" and not args.confirm_reference_reviewed:
        raise RuntimeError(
            "검토 완료 후 최종 실행에는 --confirm-reference-reviewed가 필요합니다."
        )

    dataset_name = args.dataset_name or (
        f"askly-answer-evaluation-{args.suite.replace('_', '-')}-{DATASET_VERSION}"
    )
    experiment_prefix = args.experiment_prefix or (
        f"answer-evaluation-{args.suite}-{args.prompt_version}"
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
