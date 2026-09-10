"""Shared LangGraph state for the Askly interview workflow."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class InterviewState(TypedDict, total=False):
    # User input
    resume_file_path: str
    job_posting_url: str

    # Document parsing and validation
    resume_text: str
    job_description_text: str
    parsing_status: Literal["PENDING", "PASS", "FAIL"]
    parsing_error: str | None
    parsing_retry_count: int
    resume_parsing_status: Literal["PENDING", "PASS", "FAIL"]
    job_parsing_status: Literal["PENDING", "PASS", "FAIL"]
    resume_parsing_error: str | None
    job_parsing_error: str | None

    # Structured analyses and optional RAG context
    candidate_profile: dict[str, Any]
    jd_analysis: dict[str, Any]
    retrieved_knowledge: list[dict[str, Any]]

    # Interview strategy
    interview_strategy: dict[str, Any]
    target_competencies: list[str]

    # Current interview turn
    current_question: str
    current_answer: str
    current_competency: str
    question_type: Literal["INITIAL", "FOLLOW_UP", "NEXT"]

    # Interview and evaluation history
    interview_history: list[dict[str, Any]]
    question_count: int
    followup_count: int
    current_evaluation: dict[str, Any]
    evaluation_history: list[dict[str, Any]]

    # Routing and final report
    route: Literal["FOLLOW_UP", "NEXT", "END"]
    end_reason: str | None
    final_feedback: dict[str, Any]

