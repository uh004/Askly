"""Validate or run the deterministic Router policy suite."""

from __future__ import annotations

import argparse
import os
from typing import Any

from dotenv import load_dotenv
from langsmith import Client

from evals.dataset_utils import dataset_content_hash
from evals.router.dataset import (
    DATASET_VERSION,
    ensure_langsmith_dataset,
    load_cases,
)
from evals.router.evaluators import (
    policy_conformance_evaluator,
    router_diagnostic_summary,
    router_policy_summary,
)
from evals.router.target import router_target


def safe_router_target(inputs: dict[str, Any]) -> dict[str, Any]:
    """Record policy errors as outputs so failed cases remain visible."""

    try:
        return router_target(inputs)
    except Exception as exc:  # evaluator must record all failed scenarios
        return {"route": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def validate_locally(*, suite: str = "regression") -> list[dict]:
    """Validate only the dataset schema; do not hide policy mismatches."""

    return load_cases(suite=suite)


def evaluate_locally(cases: list[dict]) -> tuple[list[dict], list[dict]]:
    outputs = [safe_router_target(case["inputs"]) for case in cases]
    references = [case["reference_outputs"] for case in cases]
    summary = router_policy_summary(
        outputs=outputs,
        reference_outputs=references,
    )
    failures = [
        {
            "case_id": case["metadata"]["case_id"],
            "expected": reference["expected_route"],
            "actual": output.get("route"),
        }
        for case, output, reference in zip(cases, outputs, references)
        if output.get("route") != reference["expected_route"]
    ]
    return summary, failures


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
    include_diagnostics: bool = False,
) -> None:
    require_environment("LANGSMITH_API_KEY")
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
    summary_evaluators = [router_policy_summary]
    if include_diagnostics:
        summary_evaluators.append(router_diagnostic_summary)
    results = client.evaluate(
        safe_router_target,
        data=dataset_name,
        evaluators=[policy_conformance_evaluator],
        summary_evaluators=summary_evaluators,
        experiment_prefix=experiment_prefix,
        description=f"Askly Router {suite} 정책 일치 검증",
        metadata={
            "dataset_version": DATASET_VERSION,
            "dataset_suite": suite,
            "dataset_sha256": dataset_content_hash(cases),
            "node": "interview_review",
            "evaluation_profile": "diagnostics" if include_diagnostics else "core",
        },
        num_repetitions=1,
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
    parser.add_argument("--experiment-prefix")
    parser.add_argument("--include-diagnostics", action="store_true")
    args = parser.parse_args()
    load_dotenv()

    cases = validate_locally(suite=args.suite)
    summary, failures = evaluate_locally(cases)
    by_key = {metric["key"]: metric["score"] for metric in summary}
    print(
        f"로컬 평가 완료: suite={args.suite}, cases={len(cases)}, "
        f"policy_conformance={by_key['policy_conformance_rate']:.3f}, "
        f"boundary_pass={by_key['boundary_scenario_pass_rate']:.3f}"
    )
    if failures:
        print(f"실패 Case {len(failures)}건: {failures}")
    if args.check_langsmith:
        check_langsmith_connection()
        return
    if not args.run_langsmith:
        print("API 호출 없음: --run-langsmith를 추가하면 모든 성공·실패를 기록합니다.")
        return

    dataset_name = args.dataset_name or (
        f"askly-router-{args.suite.replace('_', '-')}-{DATASET_VERSION}"
    )
    experiment_prefix = args.experiment_prefix or f"router-{args.suite}"
    run_langsmith_experiment(
        dataset_name,
        experiment_prefix,
        suite=args.suite,
        include_diagnostics=args.include_diagnostics,
    )


if __name__ == "__main__":
    main()
