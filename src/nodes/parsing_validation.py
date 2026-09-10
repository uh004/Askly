"""Deterministic validation for extracted document text."""

from __future__ import annotations

from typing import Any, Literal, Mapping

from src.config import MIN_JOB_TEXT_LENGTH, MIN_RESUME_TEXT_LENGTH
from src.services.text import normalize_text


def validate_extracted_text(
    text: str,
    document_name: str,
    min_length: int,
) -> tuple[Literal["PASS", "FAIL"], str | None]:
    cleaned_text = normalize_text(text or "")
    errors: list[str] = []
    if not cleaned_text:
        errors.append(f"{document_name} Text가 비어 있습니다.")
    elif len(cleaned_text) < min_length:
        errors.append(
            f"{document_name} Text가 너무 짧습니다: "
            f"{len(cleaned_text)}자 / 최소 {min_length}자"
        )

    if "\x00" in cleaned_text:
        errors.append(f"{document_name} Text에 NULL 문자가 포함되어 있습니다.")

    replacement_count = cleaned_text.count("�")
    allowed_replacement_count = max(3, len(cleaned_text) // 100)
    if replacement_count > allowed_replacement_count:
        errors.append(
            f"{document_name} Text에 깨진 문자가 너무 많습니다: "
            f"{replacement_count}개"
        )

    if cleaned_text:
        meaningful_ratio = sum(char.isalnum() for char in cleaned_text) / len(
            cleaned_text
        )
        if meaningful_ratio < 0.15:
            errors.append(
                f"{document_name} Text의 유효 문자 비율이 너무 낮습니다: "
                f"{meaningful_ratio:.1%}"
            )

    if errors:
        return "FAIL", " | ".join(errors)
    return "PASS", None


def parsing_validation_node(state: Mapping[str, Any]) -> dict[str, Any]:
    resume_status, resume_error = validate_extracted_text(
        str(state.get("resume_text") or ""),
        "이력서",
        MIN_RESUME_TEXT_LENGTH,
    )
    job_status, job_error = validate_extracted_text(
        str(state.get("job_description_text") or ""),
        "채용공고",
        MIN_JOB_TEXT_LENGTH,
    )
    return {
        "resume_parsing_status": resume_status,
        "job_parsing_status": job_status,
        "resume_parsing_error": resume_error,
        "job_parsing_error": job_error,
    }


def route_after_parsing_validation(
    state: Mapping[str, Any],
) -> Literal["PASS", "FAIL"]:
    if (
        state.get("resume_parsing_status") == "PASS"
        and state.get("job_parsing_status") == "PASS"
    ):
        return "PASS"
    return "FAIL"

