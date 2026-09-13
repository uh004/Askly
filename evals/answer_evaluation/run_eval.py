"""Validate or run the answer-evaluation reliability experiment."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from langsmith import Client

from evals.answer_evaluation.dataset import ensure_langsmith_dataset, load_cases
from evals.answer_evaluation.evaluators import (
    answer_diagnostic_summary,
    answer_reliability_summary,
    score_agreement_evaluator,
)
from evals.answer_evaluation.target import make_answer_evaluation_target
from src.nodes.answer_evaluation import calculate_overall_score


DEFAULT_DATASET_NAME_TEMPLATE = "askly-answer-evaluation-{version}"


def validate_locally(
    *,
    dataset_version: str = "v1",
    split: str | None = None,
) -> list[dict]:
    cases = load_cases(version=dataset_version, split=split)
    for case in cases:
        scores = case["reference_outputs"]["human_scores"]
        overall = calculate_overall_score(scores)
        if not 20 <= overall <= 100:
            raise AssertionError(f"Human overall 점수 범위 오류: {overall}")
    return cases


def require_environment(*names: str) -> None:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError("필요한 환경변수가 없습니다: " + ", ".join(missing))


def check_langsmith_connection() -> None:
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
    evaluators = [score_agreement_evaluator] if include_diagnostics else []
    summary_evaluators = [answer_reliability_summary]
    if include_diagnostics:
        summary_evaluators.append(answer_diagnostic_summary)

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
        make_answer_evaluation_target(prompt_version),
        data=data,
        evaluators=evaluators,
        summary_evaluators=summary_evaluators,
        experiment_prefix=experiment_prefix,
        description=(
            f"Askly 답변 평가 신뢰성 {prompt_version} 진단 포함 평가"
            if include_diagnostics
            else f"Askly 답변 평가 신뢰성 {prompt_version} 핵심 지표 평가"
        ),
        metadata={
            "dataset_version": dataset_version,
            "dataset_split": split or "all",
            "prompt_version": prompt_version,
            "node": "answer_evaluation",
            "evaluation_profile": "diagnostics" if include_diagnostics else "core",
        },
        max_concurrency=1,
    )
    print(f"LangSmith Experiment: {results.experiment_name}")
    print(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-langsmith", action="store_true")
    parser.add_argument("--check-langsmith", action="store_true")
    parser.add_argument("--dataset-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--dataset-name")
    parser.add_argument("--split", choices=("all", "dev", "holdout"), default="all")
    parser.add_argument("--prompt-version", choices=("v1", "v2"), default="v1")
    parser.add_argument(
        "--experiment-prefix"
    )
    parser.add_argument(
        "--include-diagnostics",
        action="store_true",
        help="항목별 점수 오차와 평가 근거 진단 지표를 함께 기록합니다.",
    )
    args = parser.parse_args()
    load_dotenv()
    selected_split = None if args.split == "all" else args.split
    dataset_name = args.dataset_name or DEFAULT_DATASET_NAME_TEMPLATE.format(
        version=args.dataset_version
    )
    experiment_prefix = args.experiment_prefix or (
        f"answer-evaluation-{args.prompt_version}-{args.split}"
    )
    cases = validate_locally(
        dataset_version=args.dataset_version,
        split=selected_split,
    )
    print(f"로컬 검증 완료: {len(cases)}개 Case")
    if args.check_langsmith:
        check_langsmith_connection()
        return
    if args.run_langsmith:
        run_langsmith_experiment(
            dataset_name,
            experiment_prefix,
            dataset_version=args.dataset_version,
            split=selected_split,
            prompt_version=args.prompt_version,
            include_diagnostics=args.include_diagnostics,
        )
        return
    print("API 호출은 하지 않았습니다. 실행하려면 --run-langsmith를 추가하세요.")


if __name__ == "__main__":
    main()
