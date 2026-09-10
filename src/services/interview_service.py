"""Application service that starts, resumes, and reads interview sessions."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Mapping

from langgraph.types import Command

from src.graph.interview_graph import interview_graph


class InterviewSessionNotFoundError(LookupError):
    """Raised when a thread_id has no checkpointed interview state."""


class InterviewSessionNotWaitingError(RuntimeError):
    """Raised when an answer is submitted outside an interrupt point."""


class InterviewService:
    def __init__(self, graph: Any = interview_graph) -> None:
        self.graph = graph

    @staticmethod
    def _config(session_id: str) -> dict[str, Any]:
        return {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 200,
        }

    def start_interview(
        self,
        resume_file_path: str | Path,
        job_posting_url: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        active_session_id = session_id or str(uuid.uuid4())
        result = self.graph.invoke(
            {
                "resume_file_path": str(resume_file_path),
                "job_posting_url": job_posting_url,
                "retrieved_knowledge": [],
            },
            config=self._config(active_session_id),
        )
        return self._serialize_session(
            active_session_id,
            result,
            waiting_for_answer="__interrupt__" in result,
        )

    def submit_answer(self, session_id: str, answer: str) -> dict[str, Any]:
        normalized_answer = " ".join(answer.split())
        if not normalized_answer:
            raise ValueError("답변은 비어 있을 수 없습니다.")

        snapshot = self._get_snapshot(session_id)
        if snapshot.values.get("final_feedback"):
            raise InterviewSessionNotWaitingError("이미 종료된 면접입니다.")
        if "user_answer" not in snapshot.next:
            raise InterviewSessionNotWaitingError(
                "현재 세션은 사용자 답변을 기다리는 상태가 아닙니다."
            )

        result = self.graph.invoke(
            Command(resume={"answer": normalized_answer}),
            config=self._config(session_id),
        )
        return self._serialize_session(
            session_id,
            result,
            waiting_for_answer="__interrupt__" in result,
        )

    def get_interview(self, session_id: str) -> dict[str, Any]:
        snapshot = self._get_snapshot(session_id)
        return self._serialize_session(
            session_id,
            snapshot.values,
            waiting_for_answer="user_answer" in snapshot.next,
        )

    def _get_snapshot(self, session_id: str) -> Any:
        snapshot = self.graph.get_state(self._config(session_id))
        if not snapshot.values:
            raise InterviewSessionNotFoundError(
                f"면접 세션을 찾을 수 없습니다: {session_id}"
            )
        return snapshot

    @staticmethod
    def _serialize_session(
        session_id: str,
        state: Mapping[str, Any],
        *,
        waiting_for_answer: bool,
    ) -> dict[str, Any]:
        final_feedback = state.get("final_feedback")
        status = "COMPLETED" if final_feedback else "WAITING_ANSWER"
        question = None
        if waiting_for_answer and not final_feedback:
            question = {
                "question": str(state.get("current_question") or ""),
                "competency": str(state.get("current_competency") or ""),
                "question_type": state.get("question_type"),
            }

        return {
            "session_id": session_id,
            "status": status,
            "question": question,
            "progress": {
                "question_count": int(state.get("question_count", 0)),
                "followup_count": int(state.get("followup_count", 0)),
                "target_competency_count": len(
                    state.get("target_competencies", [])
                ),
            },
            "target_competencies": list(
                state.get("target_competencies", [])
            ),
            "end_reason": state.get("end_reason"),
            "final_feedback": final_feedback,
        }
