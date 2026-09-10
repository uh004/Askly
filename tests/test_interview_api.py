from __future__ import annotations

import os
import unittest
import uuid
from pathlib import Path
from typing import Any

os.environ["LANGSMITH_TRACING"] = "false"

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from src.api.dependencies import get_interview_service
from src.api.main import app
from src.graph.interview_graph import build_interview_graph
from src.services.interview_service import (
    InterviewService,
    InterviewSessionNotFoundError,
)
from tests.test_interview_graph import (
    stub_answer_evaluation,
    stub_candidate_jd_analysis,
    stub_document_parsing,
    stub_final_feedback,
    stub_interview_strategy,
    stub_parsing_validation,
    stub_question_generation,
)


def session_payload(
    session_id: str,
    *,
    completed: bool = False,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "status": "COMPLETED" if completed else "WAITING_ANSWER",
        "question": None
        if completed
        else {
            "question": "문제 해결 경험을 설명해 주세요?",
            "competency": "문제 해결",
            "question_type": "INITIAL",
        },
        "progress": {
            "question_count": 1 if completed else 0,
            "followup_count": 0,
            "target_competency_count": 1,
        },
        "target_competencies": ["문제 해결"],
        "end_reason": "면접 완료" if completed else None,
        "final_feedback": {"overall_score": 80.0} if completed else None,
    }


class FakeInterviewService:
    def __init__(self) -> None:
        self.upload_path: Path | None = None
        self.upload_content = b""
        self.session_id = ""

    def start_interview(
        self,
        resume_file_path: str | Path,
        job_posting_url: str,
        *,
        session_id: str,
    ) -> dict[str, Any]:
        self.upload_path = Path(resume_file_path)
        self.upload_content = self.upload_path.read_bytes()
        self.session_id = session_id
        return session_payload(session_id)

    def submit_answer(self, session_id: str, answer: str) -> dict[str, Any]:
        if session_id != self.session_id:
            raise InterviewSessionNotFoundError("면접 세션을 찾을 수 없습니다.")
        return session_payload(session_id, completed=True)

    def get_interview(self, session_id: str) -> dict[str, Any]:
        if session_id != self.session_id:
            raise InterviewSessionNotFoundError("면접 세션을 찾을 수 없습니다.")
        return session_payload(session_id)


class InterviewApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FakeInterviewService()
        app.dependency_overrides[get_interview_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_health_check(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_start_interview_uploads_pdf_and_removes_temporary_file(self) -> None:
        response = self.client.post(
            "/api/interviews/start",
            files={
                "resume_file": (
                    "resume.pdf",
                    b"%PDF-1.4 synthetic resume",
                    "application/pdf",
                )
            },
            data={
                "job_posting_url": (
                    "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=1"
                )
            },
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["status"], "WAITING_ANSWER")
        self.assertEqual(body["question"]["competency"], "문제 해결")
        self.assertEqual(self.service.upload_content[:5], b"%PDF-")
        self.assertIsNotNone(self.service.upload_path)
        self.assertFalse(self.service.upload_path.exists())

    def test_rejects_non_pdf_upload(self) -> None:
        response = self.client.post(
            "/api/interviews/start",
            files={"resume_file": ("resume.txt", b"plain text", "text/plain")},
            data={"job_posting_url": "https://www.wanted.co.kr/wd/1"},
        )
        self.assertEqual(response.status_code, 415)

    def test_submit_answer_returns_completed_feedback(self) -> None:
        session_id = str(uuid.uuid4())
        self.service.session_id = session_id
        response = self.client.post(
            f"/api/interviews/{session_id}/answers",
            json={"answer": "병목을 측정하고 비동기 처리로 개선했습니다."},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "COMPLETED")
        self.assertEqual(response.json()["final_feedback"]["overall_score"], 80.0)

    def test_unknown_session_returns_404(self) -> None:
        response = self.client.get(f"/api/interviews/{uuid.uuid4()}")
        self.assertEqual(response.status_code, 404)


class InterviewServiceTest(unittest.TestCase):
    def test_service_starts_resumes_and_reads_graph_session(self) -> None:
        graph = build_interview_graph(
            node_overrides={
                "document_parsing": stub_document_parsing,
                "parsing_validation": stub_parsing_validation,
                "candidate_jd_analysis": stub_candidate_jd_analysis,
                "interview_strategy": stub_interview_strategy,
                "question_generation": stub_question_generation,
                "answer_evaluation": stub_answer_evaluation,
                "final_feedback": stub_final_feedback,
            },
            checkpointer=InMemorySaver(),
        )
        service = InterviewService(graph)
        session_id = str(uuid.uuid4())

        started = service.start_interview(
            "synthetic_resume.pdf",
            "https://example.com/job",
            session_id=session_id,
        )
        self.assertEqual(started["status"], "WAITING_ANSWER")
        self.assertEqual(started["question"]["question_type"], "INITIAL")

        followup = service.submit_answer(session_id, "비동기 처리로 개선했습니다.")
        self.assertEqual(followup["question"]["question_type"], "FOLLOW_UP")

        service.submit_answer(session_id, "응답 시간을 30% 단축했습니다.")
        completed = service.submit_answer(session_id, "의견 차이를 조율했습니다.")
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertEqual(completed["progress"]["question_count"], 3)

        restored = service.get_interview(session_id)
        self.assertEqual(restored["status"], "COMPLETED")
        self.assertEqual(restored["final_feedback"], completed["final_feedback"])


if __name__ == "__main__":
    unittest.main()
