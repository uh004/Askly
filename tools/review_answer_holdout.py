"""Interactively review and approve Final Holdout answer Reference Scores."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evals.answer_evaluation.metrics import SCORE_FIELDS


DATASET_PATH = (
    Path(__file__).parents[1]
    / "evals"
    / "answer_evaluation"
    / "datasets"
    / "final_holdout_v1.jsonl"
)


def read_cases() -> list[dict[str, Any]]:
    with DATASET_PATH.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def save_cases(cases: list[dict[str, Any]]) -> None:
    temp_path = DATASET_PATH.with_suffix(".jsonl.tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as target:
        for case in cases:
            target.write(json.dumps(case, ensure_ascii=False, separators=(",", ":")))
            target.write("\n")
    temp_path.replace(DATASET_PATH)


def pending_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        case
        for case in cases
        if case["metadata"].get("reference_review_status") != "approved"
    ]


def show_case(case: dict[str, Any], index: int, total: int) -> None:
    inputs = case["inputs"]
    reference = case["reference_outputs"]
    scores = reference["reference_scores"]
    print("\n" + "=" * 72)
    print(f"[{index}/{total}] {case['metadata']['case_id']}")
    print(f"품질/질문 유형: {reference['quality_label']} / {inputs['question_type']}")
    print(f"질문: {inputs['current_question']}")
    print(f"답변: {inputs['current_answer']}")
    print("Reference Scores:")
    print("  " + ", ".join(f"{field}={scores[field]}" for field in SCORE_FIELDS))
    print(f"근거: {', '.join(reference.get('expected_evidence', [])) or '-'}")
    print(f"부족한 점: {', '.join(reference.get('expected_missing_points', [])) or '-'}")
    print(f"메모: {reference.get('reference_notes', '-')}")


def parse_scores(raw: str) -> dict[str, int]:
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != len(SCORE_FIELDS):
        raise ValueError("점수 6개를 쉼표로 구분해야 합니다.")
    values = [int(part) for part in parts]
    if any(value < 1 or value > 5 for value in values):
        raise ValueError("모든 점수는 1~5 사이여야 합니다.")
    return dict(zip(SCORE_FIELDS, values))


def approve(case: dict[str, Any]) -> None:
    case["metadata"]["reference_review_status"] = "approved"
    case["metadata"]["reference_reviewer"] = "owner"
    case["metadata"]["reference_reviewed_at"] = datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status",
        action="store_true",
        help="승인 현황만 출력하고 종료합니다.",
    )
    args = parser.parse_args()
    cases = read_cases()
    pending = pending_cases(cases)
    print(f"Reference 검토 현황: 승인 {len(cases) - len(pending)}/{len(cases)}, 대기 {len(pending)}")
    if args.status or not pending:
        return

    print("a=현재 점수 승인, e=점수 수정 후 승인, s=건너뛰기, q=저장 후 종료")
    changed = False
    for index, case in enumerate(pending, start=1):
        show_case(case, index, len(pending))
        while True:
            command = input("선택 [a/e/s/q]: ").strip().lower()
            if command == "a":
                approve(case)
                changed = True
                break
            if command == "e":
                print("점수 순서: " + ", ".join(SCORE_FIELDS))
                try:
                    scores = parse_scores(input("새 점수 6개: "))
                except (TypeError, ValueError) as exc:
                    print(f"입력 오류: {exc}")
                    continue
                case["reference_outputs"]["reference_scores"] = scores
                note = input("수정 메모(선택): ").strip()
                if note:
                    case["reference_outputs"]["reference_notes"] = note
                approve(case)
                changed = True
                break
            if command == "s":
                break
            if command == "q":
                if changed:
                    save_cases(cases)
                remaining = len(pending_cases(cases))
                print(f"저장 완료. 남은 검토: {remaining}건")
                return
            print("a, e, s, q 중 하나를 입력하세요.")

    if changed:
        save_cases(cases)
    remaining = len(pending_cases(cases))
    print(f"검토 저장 완료. 승인 {len(cases) - remaining}/{len(cases)}, 대기 {remaining}")


if __name__ == "__main__":
    main()
