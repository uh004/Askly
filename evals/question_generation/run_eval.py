"""Validate locally or run the question-generation experiment in LangSmith."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from langsmith import Client

from evals.question_generation.dataset import ensure_langsmith_dataset, load_cases
from evals.question_generation.evaluators import (
    question_quality_evaluator,
    route_compliance_evaluator,
)
from evals.question_generation.target import question_generation_target
from src.nodes.question_generation import select_question_context


DEFAULT_DATASET_NAME = "askly-question-generation-v1"


def validate_locally() -> list[dict]:
    """Validate dataset structure and deterministic routing without API calls."""

    cases = load_cases()
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


def run_langsmith_experiment(dataset_name: str, experiment_prefix: str) -> None:
    require_environment("OPENAI_API_KEY", "LANGSMITH_API_KEY")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "askly-agent-eval")

    cases = validate_locally()
    client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
    dataset, created = ensure_langsmith_dataset(
        client,
        dataset_name=dataset_name,
        cases=cases,
    )
    action = "생성 및 업로드" if created else "기존 Dataset 재사용"
    print(f"LangSmith Dataset: {dataset.name} ({action})")

    results = client.evaluate(
        question_generation_target,
        data=dataset_name,
        evaluators=[route_compliance_evaluator, question_quality_evaluator],
        experiment_prefix=experiment_prefix,
        description="Askly 질문 생성 v1 baseline",
        metadata={"dataset_version": "v1", "node": "question_generation"},
        max_concurrency=1,
    )
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
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument(
        "--experiment-prefix",
        default="question-generation-v1-baseline",
    )
    args = parser.parse_args()

    load_dotenv()
    cases = validate_locally()
    print(f"로컬 검증 완료: {len(cases)}개 Case")

    if args.check_langsmith:
        check_langsmith_connection()
        return

    if not args.run_langsmith:
        print("API 호출은 하지 않았습니다. 실행하려면 --run-langsmith를 추가하세요.")
        return

    run_langsmith_experiment(args.dataset_name, args.experiment_prefix)


if __name__ == "__main__":
    main()
