"""LangGraph node for candidate and job-description analysis."""

from __future__ import annotations

from typing import Any, Mapping

from src.chains.analysis import (
    get_candidate_analysis_chain,
    get_jd_analysis_chain,
)
from src.nodes.parsing_validation import route_after_parsing_validation


def candidate_jd_analysis_node(
    state: Mapping[str, Any],
    *,
    candidate_chain: Any | None = None,
    jd_chain: Any | None = None,
) -> dict[str, Any]:
    if route_after_parsing_validation(state) != "PASS":
        raise ValueError("파싱 검증을 통과한 이력서와 채용공고가 필요합니다.")

    resume_text = str(state.get("resume_text") or "").strip()
    job_description_text = str(state.get("job_description_text") or "").strip()
    candidate_profile = (candidate_chain or get_candidate_analysis_chain()).invoke(
        {"resume_text": resume_text}
    )
    jd_analysis = (jd_chain or get_jd_analysis_chain()).invoke(
        {"job_description_text": job_description_text}
    )
    return {
        "candidate_profile": candidate_profile.model_dump(),
        "jd_analysis": jd_analysis.model_dump(),
    }

