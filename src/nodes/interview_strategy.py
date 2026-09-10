"""LangGraph node for generating a grounded interview strategy."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from src.chains.strategy import get_interview_strategy_chain
from src.config import (
    MAX_INTERVIEW_STRATEGY_ATTEMPTS,
    MIN_STRATEGY_EVIDENCE_COVERAGE,
)


def _normalize_strategy_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _collect_strategy_source_texts(value: Any) -> set[str]:
    texts: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, str):
            normalized = _normalize_strategy_text(item)
            if normalized:
                texts.add(normalized)
        elif isinstance(item, Mapping):
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return texts


def _compact_strategy_text(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣+#]+", "", value.casefold())


def _strategy_ngrams(value: str, size: int = 3) -> set[str]:
    if len(value) < size:
        return {value} if value else set()
    return {value[index : index + size] for index in range(len(value) - size + 1)}


def _is_strategy_evidence_supported(
    evidence: str,
    source_texts: set[str],
) -> bool:
    normalized = _normalize_strategy_text(evidence)
    if normalized in source_texts:
        return True

    compact_evidence = _compact_strategy_text(evidence)
    compact_sources = [_compact_strategy_text(source) for source in source_texts]
    if not compact_evidence or not compact_sources:
        return False

    evidence_numbers = set(re.findall(r"\d+(?:[.,]\d+)?%?", evidence))
    source_numbers = set(re.findall(r"\d+(?:[.,]\d+)?%?", " ".join(source_texts)))
    if not evidence_numbers.issubset(source_numbers):
        return False

    evidence_ngrams = _strategy_ngrams(compact_evidence)
    source_ngrams: set[str] = set()
    for source in compact_sources:
        source_ngrams.update(_strategy_ngrams(source))
    coverage = len(evidence_ngrams & source_ngrams) / len(evidence_ngrams)
    return coverage >= MIN_STRATEGY_EVIDENCE_COVERAGE


def _normalize_strategy_alignment(strategy_data: dict[str, Any]) -> dict[str, Any]:
    for item in strategy_data["competencies"]:
        candidate_evidence = item["candidate_evidence"]
        if not candidate_evidence:
            item["alignment_status"] = "UNVERIFIED"
            if not item["gap_to_verify"]:
                item["gap_to_verify"] = item["verification_points"][:3]
        elif item["alignment_status"] == "UNVERIFIED":
            item["alignment_status"] = "PARTIAL"
    return strategy_data


def _validate_interview_strategy(
    strategy_data: dict[str, Any],
    candidate_profile: dict[str, Any],
    jd_analysis: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    competencies = strategy_data["competencies"]

    priorities = [item["priority"] for item in competencies]
    if sorted(priorities) != list(range(1, len(competencies) + 1)):
        errors.append("priority는 1부터 역량 수까지 중복 없이 연속되어야 합니다.")

    competency_names = [
        _normalize_strategy_text(item["competency"]) for item in competencies
    ]
    if len(competency_names) != len(set(competency_names)):
        errors.append("동일한 competency가 중복되었습니다.")

    candidate_sources = _collect_strategy_source_texts(candidate_profile)
    jd_sources = _collect_strategy_source_texts(jd_analysis)
    for item in competencies:
        name = item["competency"]
        candidate_evidence = item["candidate_evidence"]
        jd_evidence = item["jd_evidence"]
        alignment_status = item["alignment_status"]

        if any(
            not _is_strategy_evidence_supported(evidence, candidate_sources)
            for evidence in candidate_evidence
        ):
            errors.append(
                f"{name}: candidate_evidence가 candidate_profile로 뒷받침되지 않습니다."
            )
        if any(
            not _is_strategy_evidence_supported(evidence, jd_sources)
            for evidence in jd_evidence
        ):
            errors.append(f"{name}: jd_evidence가 jd_analysis로 뒷받침되지 않습니다.")

        if alignment_status == "UNVERIFIED" and candidate_evidence:
            errors.append(
                f"{name}: UNVERIFIED이면 candidate_evidence가 비어 있어야 합니다."
            )
        if alignment_status in {"MATCH", "PARTIAL"} and not candidate_evidence:
            errors.append(f"{name}: {alignment_status}이면 candidate_evidence가 필요합니다.")
        if alignment_status != "MATCH" and not item["gap_to_verify"]:
            errors.append(f"{name}: {alignment_status}이면 gap_to_verify가 필요합니다.")

        direction_values = [*item["verification_points"], item["question_direction"]]
        if any("?" in value for value in direction_values):
            errors.append(f"{name}: 검증 항목과 질문 방향에는 물음표를 사용할 수 없습니다.")
    return errors


def interview_strategy_node(
    state: Mapping[str, Any],
    *,
    chain: Any | None = None,
) -> dict[str, Any]:
    candidate_profile = state.get("candidate_profile")
    jd_analysis = state.get("jd_analysis")
    retrieved_knowledge = state.get("retrieved_knowledge", [])
    if not candidate_profile or not jd_analysis:
        raise ValueError(
            "면접 전략 수립에는 candidate_profile과 jd_analysis가 필요합니다."
        )

    strategy_input = {
        "candidate_profile": json.dumps(
            candidate_profile, ensure_ascii=False, indent=2
        ),
        "jd_analysis": json.dumps(jd_analysis, ensure_ascii=False, indent=2),
        "retrieved_knowledge": json.dumps(
            retrieved_knowledge, ensure_ascii=False, indent=2
        ),
        "validation_feedback": "없음",
    }

    strategy_chain = chain or get_interview_strategy_chain()
    validation_errors: list[str] = []
    for _ in range(MAX_INTERVIEW_STRATEGY_ATTEMPTS):
        strategy = strategy_chain.invoke(strategy_input)
        strategy_data = _normalize_strategy_alignment(strategy.model_dump())
        validation_errors = _validate_interview_strategy(
            strategy_data,
            candidate_profile,
            jd_analysis,
        )
        if not validation_errors:
            break
        strategy_input["validation_feedback"] = (
            "이전 결과에서 다음 오류가 발견되었습니다. 입력에 없는 사실을 "
            "추가하지 말고 오류만 수정하세요: " + " / ".join(validation_errors)
        )
    else:
        raise ValueError("면접 전략 검증 실패: " + " / ".join(validation_errors))

    strategy_data["rag_applied"] = bool(retrieved_knowledge)
    if not retrieved_knowledge:
        for competency in strategy_data["competencies"]:
            competency["rag_basis"] = []

    strategy_data["competencies"] = sorted(
        strategy_data["competencies"],
        key=lambda item: item["priority"],
    )
    target_competencies = [
        item["competency"] for item in strategy_data["competencies"]
    ]
    strategy_data["interview_flow"] = [
        f"{competency} 검증" for competency in target_competencies
    ]
    return {
        "interview_strategy": strategy_data,
        "target_competencies": target_competencies,
    }

