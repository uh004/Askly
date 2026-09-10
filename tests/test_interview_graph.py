from __future__ import annotations

import os
import unittest
import uuid
from typing import Any

# The structural integration test must stay local and API-free.
os.environ["LANGSMITH_TRACING"] = "false"

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.graph.interview_graph import build_interview_graph


def stub_document_parsing(state: dict[str, Any]) -> dict[str, Any]:
    attempt = state.get("parsing_retry_count", 0) + 1
    return {
        "resume_text": "" if attempt == 1 else "합성 지원자 문서 " * 20,
        "job_description_text": "" if attempt == 1 else "합성 채용공고 " * 20,
        "parsing_status": "FAIL" if attempt == 1 else "PASS",
        "parsing_error": "첫 번째 파싱 실패" if attempt == 1 else None,
        "parsing_retry_count": attempt,
    }


def stub_parsing_validation(state: dict[str, Any]) -> dict[str, Any]:
    passed = state.get("parsing_retry_count", 0) >= 2
    return {
        "resume_parsing_status": "PASS" if passed else "FAIL",
        "job_parsing_status": "PASS" if passed else "FAIL",
        "resume_parsing_error": None if passed else "이력서 Text 없음",
        "job_parsing_error": None if passed else "채용공고 Text 없음",
    }


def stub_candidate_jd_analysis(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_profile": {"summary": "합성 지원자"},
        "jd_analysis": {"position": "합성 백엔드 개발자"},
    }


def stub_interview_strategy(state: dict[str, Any]) -> dict[str, Any]:
    competencies = ["문제 해결", "협업"]
    return {
        "target_competencies": competencies,
        "interview_strategy": {
            "strategy_summary": "통합 테스트용 전략",
            "competencies": [
                {"competency": competency} for competency in competencies
            ],
        },
        "interview_history": [],
        "evaluation_history": [],
        "question_count": 0,
        "followup_count": 0,
    }


def stub_question_generation(state: dict[str, Any]) -> dict[str, Any]:
    question_count = state.get("question_count", 0)
    competencies = state["target_competencies"]
    if state.get("route") == "FOLLOW_UP":
        competency = state["current_competency"]
        question_type = "FOLLOW_UP"
    else:
        competency = competencies[min(question_count, len(competencies) - 1)]
        question_type = "INITIAL" if question_count == 0 else "NEXT"
    return {
        "current_question": f"{competency} 경험을 설명해 주세요?",
        "current_competency": competency,
        "question_type": question_type,
        "current_answer": "",
        "current_evaluation": {},
    }


def stub_answer_evaluation(state: dict[str, Any]) -> dict[str, Any]:
    needs_followup = (
        state["current_competency"] == "문제 해결"
        and state["question_type"] == "INITIAL"
    )
    evaluation = {
        "overall_score": 60.0 if needs_followup else 90.0,
        "missing_points": ["개선 결과"] if needs_followup else [],
    }
    evaluation_history = [
        dict(item) for item in state.get("evaluation_history", [])
    ]
    evaluation_history.append(
        {
            "question": state["current_question"],
            "answer": state["current_answer"],
            "competency": state["current_competency"],
            "question_type": state["question_type"],
            "evaluation": evaluation,
        }
    )
    return {
        "current_evaluation": evaluation,
        "evaluation_history": evaluation_history,
    }


def stub_final_feedback(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_feedback": {
            "overall_summary": "통합 테스트용 전체 피드백",
            "question_feedback": [
                {"question_number": index}
                for index, _ in enumerate(
                    state["evaluation_history"],
                    start=1,
                )
            ],
        }
    }


class InterviewGraphIntegrationTest(unittest.TestCase):
    def test_retry_followup_next_and_end_paths(self) -> None:
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
        config = {
            "configurable": {"thread_id": f"graph-test-{uuid.uuid4()}"}
        }

        first_pause = graph.invoke(
            {
                "resume_file_path": "synthetic_resume.pdf",
                "job_posting_url": "https://example.com/job",
                "retrieved_knowledge": [],
            },
            config=config,
        )
        self.assertIn("__interrupt__", first_pause)
        self.assertEqual(first_pause["parsing_retry_count"], 2)

        followup_pause = graph.invoke(
            Command(resume={"answer": "비동기 처리로 개선했습니다."}),
            config=config,
        )
        self.assertEqual(followup_pause["route"], "FOLLOW_UP")
        self.assertEqual(followup_pause["question_type"], "FOLLOW_UP")

        next_pause = graph.invoke(
            Command(resume={"answer": "응답 시간을 30% 단축했습니다."}),
            config=config,
        )
        self.assertEqual(next_pause["route"], "NEXT")
        self.assertEqual(next_pause["current_competency"], "협업")

        completed = graph.invoke(
            Command(resume={"answer": "의견 차이를 조율했습니다."}),
            config=config,
        )
        self.assertNotIn("__interrupt__", completed)
        self.assertEqual(completed["route"], "END")
        self.assertEqual(completed["question_count"], 3)
        self.assertEqual(completed["followup_count"], 1)
        self.assertEqual(len(completed["evaluation_history"]), 3)
        self.assertEqual(
            len(completed["final_feedback"]["question_feedback"]),
            3,
        )


if __name__ == "__main__":
    unittest.main()
