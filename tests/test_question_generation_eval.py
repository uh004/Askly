from __future__ import annotations

import unittest
from collections import Counter
from unittest.mock import patch

from evals.question_generation.dataset import load_cases
from evals.question_generation.evaluators import (
    QuestionQualityJudgment,
    question_quality_diagnostics_evaluator,
    question_quality_evaluator,
    route_compliance_evaluator,
)
from src.nodes.question_generation import (
    GeneratedInterviewQuestion,
    _normalize_question,
    question_generation_node,
    select_question_context,
)


class FakeQuestionChain:
    def invoke(self, payload: dict) -> GeneratedInterviewQuestion:
        return GeneratedInterviewQuestion(
            question=(
                f"{payload['current_competency']}과 관련해 본인이 수행한 "
                "구체적인 행동과 결과를 설명해 주시겠습니까?"
            )
        )


class SequencedQuestionChain:
    def __init__(self, questions: list[str]) -> None:
        self.questions = questions
        self.payloads: list[dict] = []

    def invoke(self, payload: dict) -> GeneratedInterviewQuestion:
        self.payloads.append(payload)
        return GeneratedInterviewQuestion(
            question=self.questions[len(self.payloads) - 1]
        )


class FakeQuestionJudgeChain:
    def invoke(self, _: dict) -> QuestionQualityJudgment:
        return QuestionQualityJudgment.model_validate(
            {
                "groundedness": {"score": 5, "reason": "입력 근거와 직접 연결됨"},
                "jd_relevance": {"score": 4, "reason": "JD 역량과 관련됨"},
                "personalization": {"score": 5, "reason": "지원자 경험을 반영함"},
                "followup_relevance": {
                    "score": 4,
                    "reason": "직전 답변의 빠진 내용을 확인함",
                },
                "unsupported_assumption": False,
                "unsupported_assumption_reason": "",
            }
        )


class QuestionGenerationEvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.regression_cases = load_cases(suite="regression")
        cls.holdout_cases = load_cases(suite="final_holdout")

    @staticmethod
    def _route_counts(cases: list[dict]) -> Counter:
        return Counter(
            case["reference_outputs"]["expected_question_type"] for case in cases
        )

    def test_regression_dataset_keeps_existing_30_cases(self) -> None:
        self.assertEqual(len(self.regression_cases), 30)
        self.assertEqual(
            self._route_counts(self.regression_cases),
            {"INITIAL": 10, "FOLLOW_UP": 10, "NEXT": 10},
        )

    def test_final_holdout_has_30_balanced_unique_cases(self) -> None:
        self.assertEqual(len(self.holdout_cases), 30)
        self.assertEqual(
            self._route_counts(self.holdout_cases),
            {"INITIAL": 10, "FOLLOW_UP": 10, "NEXT": 10},
        )
        case_ids = [case["metadata"]["case_id"] for case in self.holdout_cases]
        scenarios = [case["metadata"]["scenario"] for case in self.holdout_cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertEqual(len(scenarios), len(set(scenarios)))

    def test_context_selection_matches_every_holdout_reference(self) -> None:
        for case in self.holdout_cases:
            with self.subTest(case_id=case["metadata"]["case_id"]):
                competency, question_type = select_question_context(case["inputs"])
                reference = case["reference_outputs"]
                self.assertEqual(question_type, reference["expected_question_type"])
                self.assertEqual(competency, reference["expected_competency"])

    def test_judge_schema_accepts_empty_assumption_reason(self) -> None:
        judgment = QuestionQualityJudgment.model_validate(
            {
                "groundedness": {"score": 5, "reason": "근거와 직접 연결됨"},
                "jd_relevance": {"score": 5, "reason": "JD와 직접 관련됨"},
                "personalization": {"score": 5, "reason": "지원자 경험을 반영함"},
                "followup_relevance": {
                    "score": 5,
                    "reason": "평가 대상 아님",
                },
                "unsupported_assumption": False,
                "unsupported_assumption_reason": "",
            }
        )
        self.assertEqual(judgment.unsupported_assumption_reason, "")

    def test_core_and_diagnostic_metric_sets_are_separated(self) -> None:
        case = next(
            case
            for case in self.holdout_cases
            if case["reference_outputs"]["expected_question_type"] == "FOLLOW_UP"
        )
        kwargs = {
            "inputs": case["inputs"],
            "outputs": {
                "question": "그 개선 결과를 어떤 수치로 확인했습니까?",
                "question_type": "FOLLOW_UP",
                "competency": case["reference_outputs"]["expected_competency"],
            },
            "reference_outputs": case["reference_outputs"],
        }
        with patch(
            "evals.question_generation.evaluators._get_judge_chain",
            return_value=FakeQuestionJudgeChain(),
        ):
            core = question_quality_evaluator(**kwargs)
            diagnostics = question_quality_diagnostics_evaluator(**kwargs)

        self.assertEqual(
            {metric["key"] for metric in core},
            {"groundedness", "jd_relevance", "personalization"},
        )
        self.assertEqual(
            {metric["key"] for metric in diagnostics},
            {
                "groundedness",
                "jd_relevance",
                "personalization",
                "unsupported_assumption_free",
                "followup_relevance",
            },
        )

    def test_node_matches_expected_route_for_regression_cases(self) -> None:
        for case in self.regression_cases:
            with self.subTest(case_id=case["metadata"]["case_id"]):
                result = question_generation_node(
                    case["inputs"], chain=FakeQuestionChain()
                )
                outputs = {
                    "question": result["current_question"],
                    "question_type": result["question_type"],
                    "competency": result["current_competency"],
                }
                evaluation = route_compliance_evaluator(
                    outputs=outputs,
                    reference_outputs=case["reference_outputs"],
                )
                self.assertEqual(evaluation["score"], 1, evaluation["comment"])
                self.assertEqual(outputs["question"].count("?"), 1)

    def test_node_retries_once_when_question_is_duplicated(self) -> None:
        state = self.regression_cases[2]["inputs"]
        chain = SequencedQuestionChain(
            [
                state["current_question"],
                "프로젝트에서 맡은 구체적인 역할을 설명해 주시겠습니까?",
            ]
        )
        result = question_generation_node(state, chain=chain)
        self.assertEqual(len(chain.payloads), 2)
        self.assertIn("중복", chain.payloads[1]["validation_feedback"])
        self.assertEqual(
            result["current_question"],
            "프로젝트에서 맡은 구체적인 역할을 설명해 주시겠습니까?",
        )

    def test_question_normalization_replaces_sentence_end_punctuation(self) -> None:
        self.assertEqual(
            _normalize_question("프로젝트에서 맡은 역할을 설명해 주세요."),
            "프로젝트에서 맡은 역할을 설명해 주세요?",
        )


if __name__ == "__main__":
    unittest.main()
