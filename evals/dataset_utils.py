"""Shared helpers for immutable evaluation datasets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


EVAL_SUITES = {"regression", "final_holdout"}
SERVER_MANAGED_METADATA_KEYS = {"dataset_split"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} JSON 형식 오류: {exc}") from exc
            cases.append(case)
    return cases


def dataset_content_hash(cases: Iterable[dict[str, Any]]) -> str:
    comparable_cases = []
    for case in cases:
        metadata = {
            key: value
            for key, value in case.get("metadata", {}).items()
            if key not in SERVER_MANAGED_METADATA_KEYS
        }
        comparable_cases.append({**case, "metadata": metadata})
    normalized = sorted(
        comparable_cases,
        key=lambda case: str(case.get("metadata", {}).get("case_id", "")),
    )
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def remote_examples_hash(examples: Iterable[Any]) -> str:
    cases = [
        {
            "inputs": example.inputs,
            "reference_outputs": example.outputs or {},
            "metadata": example.metadata or {},
        }
        for example in examples
    ]
    return dataset_content_hash(cases)
