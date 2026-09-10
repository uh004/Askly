"""Complete LangGraph wiring for the Askly interview workflow."""

from __future__ import annotations

from typing import Any, Literal, Mapping

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from src.config import MAX_DOCUMENT_PARSING_ATTEMPTS
from src.nodes.answer_evaluation import answer_evaluation_node
from src.nodes.candidate_jd_analysis import candidate_jd_analysis_node
from src.nodes.document_parsing import document_parsing_node
from src.nodes.final_feedback import final_feedback_node
from src.nodes.interview_review import interview_review_node
from src.nodes.interview_strategy import interview_strategy_node
from src.nodes.parsing_validation import (
    parsing_validation_node,
    route_after_parsing_validation,
)
from src.nodes.question_generation import question_generation_node
from src.nodes.user_answer import user_answer_node
from src.state import InterviewState


def document_parsing_with_retry_node(
    state: Mapping[str, Any],
) -> dict[str, Any]:
    updates = {
        "resume_text": "",
        "job_description_text": "",
        **document_parsing_node(state),
    }
    updates["parsing_retry_count"] = state.get("parsing_retry_count", 0) + 1
    return updates


def route_after_pipeline_parsing_validation(
    state: Mapping[str, Any],
) -> Literal["PASS", "RETRY"]:
    if route_after_parsing_validation(state) == "PASS":
        return "PASS"

    attempt_count = state.get("parsing_retry_count", 0)
    if attempt_count < MAX_DOCUMENT_PARSING_ATTEMPTS:
        return "RETRY"

    errors = [
        state.get("parsing_error"),
        state.get("resume_parsing_error"),
        state.get("job_parsing_error"),
    ]
    error_message = " | ".join(str(error) for error in errors if error)
    raise RuntimeError(
        "문서 파싱 검증이 최대 재시도 횟수를 초과했습니다. "
        + (error_message or "상세 오류 없음")
    )


def route_after_interview_review(
    state: Mapping[str, Any],
) -> Literal["FOLLOW_UP", "NEXT", "END"]:
    route = state.get("route")
    if route not in {"FOLLOW_UP", "NEXT", "END"}:
        raise ValueError("인터뷰 진행 검토 결과에 유효한 route가 없습니다.")
    return route


def build_interview_graph(
    node_overrides: Mapping[str, Any] | None = None,
    checkpointer: Any = None,
):
    """Build the production graph, optionally replacing nodes for tests."""

    nodes = {
        "document_parsing": document_parsing_with_retry_node,
        "parsing_validation": parsing_validation_node,
        "candidate_jd_analysis": candidate_jd_analysis_node,
        "interview_strategy": interview_strategy_node,
        "question_generation": question_generation_node,
        "user_answer": user_answer_node,
        "answer_evaluation": answer_evaluation_node,
        "interview_review": interview_review_node,
        "final_feedback": final_feedback_node,
    }
    if node_overrides:
        unknown_nodes = set(node_overrides) - set(nodes)
        if unknown_nodes:
            raise ValueError(
                "정의되지 않은 노드 이름입니다: "
                + ", ".join(sorted(unknown_nodes))
            )
        nodes.update(node_overrides)

    builder = StateGraph(InterviewState)
    for node_name, node_function in nodes.items():
        builder.add_node(node_name, node_function)

    builder.add_edge(START, "document_parsing")
    builder.add_edge("document_parsing", "parsing_validation")
    builder.add_conditional_edges(
        "parsing_validation",
        route_after_pipeline_parsing_validation,
        {
            "PASS": "candidate_jd_analysis",
            "RETRY": "document_parsing",
        },
    )
    builder.add_edge("candidate_jd_analysis", "interview_strategy")
    builder.add_edge("interview_strategy", "question_generation")
    builder.add_edge("question_generation", "user_answer")
    builder.add_edge("user_answer", "answer_evaluation")
    builder.add_edge("answer_evaluation", "interview_review")
    builder.add_conditional_edges(
        "interview_review",
        route_after_interview_review,
        {
            "FOLLOW_UP": "question_generation",
            "NEXT": "question_generation",
            "END": "final_feedback",
        },
    )
    builder.add_edge("final_feedback", END)
    return builder.compile(checkpointer=checkpointer)


# Development-only state store. Replace it with a persistent checkpointer in the API.
interview_checkpointer = InMemorySaver()
interview_graph = build_interview_graph(checkpointer=interview_checkpointer)

