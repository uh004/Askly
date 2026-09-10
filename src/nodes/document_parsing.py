"""LangGraph node for collecting parsed source text."""

from __future__ import annotations

from typing import Any, Mapping

from src.services import parse_job_posting, parse_resume_pdf


def document_parsing_node(state: Mapping[str, Any]) -> dict[str, Any]:
    resume_file_path = state.get("resume_file_path")
    job_posting_url = state.get("job_posting_url")
    if not resume_file_path or not job_posting_url:
        return {
            "parsing_status": "FAIL",
            "parsing_error": "resume_file_path와 job_posting_url이 모두 필요합니다.",
        }

    updates: dict[str, Any] = {
        "parsing_status": "PENDING",
        "parsing_error": None,
    }
    errors: list[str] = []
    try:
        updates["resume_text"] = parse_resume_pdf(resume_file_path)["text"]
    except Exception as exc:
        errors.append(f"이력서 PDF 파싱 실패: {exc}")

    try:
        updates["job_description_text"] = parse_job_posting(job_posting_url)["text"]
    except Exception as exc:
        errors.append(f"채용공고 URL 파싱 실패: {exc}")

    if errors:
        updates["parsing_status"] = "FAIL"
        updates["parsing_error"] = " | ".join(errors)
    else:
        updates["parsing_status"] = "PASS"
    return updates

