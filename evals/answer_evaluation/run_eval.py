"""Validate or run the answer-evaluation reliability experiment."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from langsmith import Client

from evals.answer_evaluation.dataset import ensure_langsmith_dataset, load_cases
from evals.answer_evaluation.evaluators import (
    answer_reliability_summary,
    answer_support_evaluator,
    score_agreement_evaluator,
)
from evals.answer_evaluation.target import answer_evaluation_target
from src.nodes.answer_evaluation import calculate_overall_score


DEFAULT_DATASET_NAME = "askly-answer-evaluation-v1"


def validate_locally() -> list[dict]:
    cases = load_cases()
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


def run_langsmith_experiment(dataset_name: str, experiment_prefix: str) -> None:
    require_environment("OPENAI_API_KEY", "LANGSMITH_API_KEY")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "askly-agent-eval")
    cases = validate_locally()
    client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
    dataset, created = ensure_langsmith_dataset(
        client, dataset_name=dataset_name, cases=cases
    )
    action = "생성 및 업로드" if created else "기존 Dataset 재사용"
    print(f"LangSmith Dataset: {dataset.name} ({action})")
    results = client.evaluate(
        answer_evaluation_target,
        data=dataset_name,
        evaluators=[score_agreement_evaluator, answer_support_evaluator],
        summary_evaluators=[answer_reliability_summary],
        experiment_prefix=experiment_prefix,
        description="Askly 답변 평가 신뢰성 v1 baseline",
        metadata={"dataset_version": "v1", "node": "answer_evaluation"},
        max_concurrency=1,
    )
    print(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-langsmith", action="store_true")
    parser.add_argument("--check-langsmith", action="store_true")
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument(
        "--experiment-prefix", default="answer-evaluation-v1-baseline"
    )
    args = parser.parse_args()
    load_dotenv()
    cases = validate_locally()
    print(f"로컬 검증 완료: {len(cases)}개 Case")
    if args.check_langsmith:
        check_langsmith_connection()
        return
    if args.run_langsmith:
        run_langsmith_experiment(args.dataset_name, args.experiment_prefix)
        return
    print("API 호출은 하지 않았습니다. 실행하려면 --run-langsmith를 추가하세요.")


if __name__ == "__main__":
    main()
