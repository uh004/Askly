from __future__ import annotations

import json
import unittest
from collections import Counter

from evals.answer_evaluation.dataset import load_cases, pending_reference_reviews
from evals.answer_evaluation.evaluators import (
    answer_diagnostic_summary,
    answer_reliability_summary,
    score_agreement_evaluator,
)
from evals.answer_evaluation.metrics import SCORE_FIELDS
from src.nodes.answer_evaluation import (
    AnswerEvaluationResult,
    AnswerEvaluationScores,
    answer_evaluation_node,
    calculate_overall_score,
)


class FakeAnswerEvaluationChain:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def invoke(self, inputs: dict) -> AnswerEvaluationResult:
        self.calls.append(inputs)
        return AnswerEvaluationResult(
            summary="질문 의도와 관련된 내용을 구체적으로 설명했습니다.",
            scores=AnswerEvaluationScores(
                relevance=3,
                specificity=3,
                logical_structure=3,
                role_clarity=3,
                action_clarity=3,
                result_clarity=3,
            ),
            strengths=["질문과 관련된 내용을 답함"],
            improvement_points=["결과를 더 구체화할 필요가 있음"],
            missing_points=["정량 결과"],
            answer_evidence=["구체적으로 설명"],
        )


class AnswerEvaluationReliabilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.regression_cases = load_cases(suite="regression")
        cls.holdout_cases = load_cases(suite="final_holdout")

    @staticmethod
    def _quality_counts(cases: list[dict]) -> Counter:
        return Counter(case["reference_outputs"]["quality_label"] for case in cases)

    @staticmethod
    def _type_counts(cases: list[dict]) -> Counter:
        return Counter(case["inputs"]["question_type"] for case in cases)

    def test_regression_dataset_keeps_existing_36_cases(self) -> None:
        self.assertEqual(len(self.regression_cases), 36)
        self.assertEqual(
            self._quality_counts(self.regression_cases),
            {"GOOD": 12, "MEDIUM": 12, "POOR": 12},
        )
        self.assertEqual(
            self._type_counts(self.regression_cases),
            {"INITIAL": 12, "NEXT": 12, "FOLLOW_UP": 12},
        )

    def test_final_holdout_has_balanced_margins_and_pairs(self) -> None:
        self.assertEqual(len(self.holdout_cases), 30)
        self.assertEqual(
            self._quality_counts(self.holdout_cases),
            {"GOOD": 10, "MEDIUM": 10, "POOR": 10},
        )
        self.assertEqual(
            self._type_counts(self.holdout_cases),
            {"INITIAL": 10, "NEXT": 10, "FOLLOW_UP": 10},
        )
        pair_counts = Counter(
            (case["reference_outputs"]["quality_label"], case["inputs"]["question_type"])
            for case in self.holdout_cases
        )
        self.assertEqual(len(pair_counts), 9)
        self.assertLessEqual(max(pair_counts.values()) - min(pair_counts.values()), 1)
        self.assertEqual(set(pair_counts.values()), {3, 4})

    def test_holdout_reference_scores_have_review_workflow(self) -> None:
        pending = pending_reference_reviews(self.holdout_cases)
        self.assertLessEqual(len(pending), 30)
        for case in self.holdout_cases:
            scores = case["reference_outputs"]["reference_scores"]
            self.assertEqual(set(scores), set(SCORE_FIELDS))
            self.assertTrue(all(1 <= value <= 5 for value in scores.values()))
            self.assertIn(
                case["metadata"]["reference_review_status"],
                {"pending_owner_review", "approved"},
            )

    def test_common_node_runs_for_regression_cases_with_injected_chain(self) -> None:
        for case in self.regression_cases:
            with self.subTest(case_id=case["metadata"]["case_id"]):
                previous_history_length = len(case["inputs"]["evaluation_history"])
                result = answer_evaluation_node(
                    case["inputs"], chain=FakeAnswerEvaluationChain()
                )
                evaluation = result["current_evaluation"]
                self.assertEqual(evaluation["overall_score"], 60.0)
                self.assertEqual(
                    len(result["evaluation_history"]),
                    previous_history_length + 1,
                )

    def test_exact_reference_scores_produce_zero_mae(self) -> None:
        outputs = []
        references = []
        for case in self.regression_cases:
            reference = case["reference_outputs"]
            scores = reference["reference_scores"]
            output = {
                "scores": scores,
                "overall_score": calculate_overall_score(scores),
            }
            row_metrics = score_agreement_evaluator(
                outputs=output,
                reference_outputs=reference,
            )
            self.assertEqual(
                {metric["key"] for metric in row_metrics},
                {"evaluation_output_valid", "mae_case", "overall_score_consistency"},
            )
            self.assertEqual(row_metrics[0]["score"], 1)
            self.assertEqual(row_metrics[1]["score"], 0.0)
            self.assertEqual(row_metrics[2]["score"], 1)
            outputs.append(output)
            references.append(reference)

        summary = answer_reliability_summary(
            outputs=outputs,
            reference_outputs=references,
        )
        summary_by_key = {metric["key"]: metric["score"] for metric in summary}
        self.assertEqual(summary_by_key, {"mae_overall": 0.0})

        diagnostics = answer_diagnostic_summary(
            outputs=outputs,
            reference_outputs=references,
        )
        by_key = {metric["key"]: metric["score"] for metric in diagnostics}
        self.assertEqual(by_key["evaluation_output_coverage"], 1.0)
        for field in SCORE_FIELDS:
            self.assertEqual(by_key[f"mae_{field}"], 0.0)

    def test_schema_truncates_excess_list_items(self) -> None:
        evaluation = AnswerEvaluationResult(
            summary="목록 제한을 확인하기 위한 충분한 길이의 평가 요약입니다.",
            scores=AnswerEvaluationScores(
                relevance=1,
                specificity=1,
                logical_structure=1,
                role_clarity=1,
                action_clarity=1,
                result_clarity=1,
            ),
            strengths=["1", "2", "3", "4"],
            improvement_points=["1", "2", "3", "4"],
            missing_points=["1", "2", "3", "4"],
            answer_evidence=["1", "2", "3", "4", "5", "6"],
        )
        self.assertEqual(len(evaluation.strengths), 3)
        self.assertEqual(len(evaluation.improvement_points), 3)
        self.assertEqual(len(evaluation.missing_points), 3)
        self.assertEqual(len(evaluation.answer_evidence), 5)

    def test_overall_score_uses_configured_weights(self) -> None:
        scores = {
            "relevance": 5,
            "specificity": 4,
            "logical_structure": 3,
            "role_clarity": 2,
            "action_clarity": 1,
            "result_clarity": 5,
        }
        self.assertEqual(calculate_overall_score(scores), 68.0)

    def test_follow_up_uses_only_previous_answers_for_same_competency(self) -> None:
        chain = FakeAnswerEvaluationChain()
        state = {
            "current_question": "개선 결과를 어떻게 측정했나요?",
            "current_answer": "응답 시간을 다시 측정해 개선을 확인했습니다.",
            "current_competency": "문제 해결 능력",
            "question_type": "FOLLOW_UP",
            "interview_strategy": {
                "competencies": [
                    {"competency": "문제 해결 능력", "verification_points": ["측정 결과"]}
                ]
            },
            "evaluation_history": [
                {
                    "question": "문제를 어떻게 발견했나요?",
                    "answer": "부하 테스트로 병목을 발견했습니다.",
                    "competency": "문제 해결 능력",
                },
                {
                    "question": "협업 경험을 설명해 주세요?",
                    "answer": "기획자와 회의했습니다.",
                    "competency": "협업 능력",
                },
            ],
        }

        answer_evaluation_node(state, chain=chain)

        previous_answers = json.loads(chain.calls[0]["previous_competency_answers"])
        self.assertEqual(len(previous_answers), 1)
        self.assertEqual(previous_answers[0]["answer"], "부하 테스트로 병목을 발견했습니다.")

    def test_invalid_output_is_counted_as_maximum_error(self) -> None:
        reference = self.regression_cases[0]["reference_outputs"]
        valid_scores = reference["reference_scores"]
        outputs = [
            {},
            {
                "scores": valid_scores,
                "overall_score": calculate_overall_score(valid_scores),
            },
        ]
        references = [reference, reference]

        row_metrics = score_agreement_evaluator(
            outputs={}, reference_outputs=reference
        )
        self.assertEqual(row_metrics[0]["key"], "evaluation_output_valid")
        self.assertEqual(row_metrics[0]["score"], 0)

        diagnostics = answer_diagnostic_summary(
            outputs=outputs, reference_outputs=references
        )
        diagnostic_by_key = {
            metric["key"]: metric["score"] for metric in diagnostics
        }
        self.assertEqual(diagnostic_by_key["evaluation_output_coverage"], 0.5)
        for field in SCORE_FIELDS:
            self.assertEqual(diagnostic_by_key[f"mae_{field}"], 2.0)

        core = answer_reliability_summary(
            outputs=outputs, reference_outputs=references
        )
        self.assertEqual(core[0]["key"], "mae_overall")
        self.assertEqual(core[0]["score"], 2.0)


if __name__ == "__main__":
    unittest.main()
