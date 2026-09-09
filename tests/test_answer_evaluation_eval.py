from __future__ import annotations

import unittest
from collections import Counter

from evals.answer_evaluation.dataset import load_cases
from evals.answer_evaluation.evaluators import (
    answer_reliability_summary,
    score_agreement_evaluator,
)
from src.nodes.answer_evaluation import (
    AnswerEvaluationResult,
    AnswerEvaluationScores,
    answer_evaluation_node,
    calculate_overall_score,
)


class FakeAnswerEvaluationChain:
    def invoke(self, _: dict) -> AnswerEvaluationResult:
        return AnswerEvaluationResult(
            summary="질문 의도와 관련된 내용을 일부 구체적으로 설명했습니다.",
            scores=AnswerEvaluationScores(
                relevance=3,
                specificity=3,
                logical_structure=3,
                role_clarity=3,
                action_clarity=3,
                result_clarity=3,
            ),
            strengths=["질문과 관련된 내용을 답변함"],
            improvement_points=["결과를 더 구체화할 필요가 있음"],
            missing_points=["정량 결과"],
            answer_evidence=["구체적으로 설명"],
        )


class AnswerEvaluationReliabilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_cases()

    def test_dataset_balances_quality_and_question_type(self) -> None:
        quality = Counter(
            case["reference_outputs"]["quality_label"] for case in self.cases
        )
        question_types = Counter(case["inputs"]["question_type"] for case in self.cases)
        self.assertEqual(quality, {"GOOD": 6, "MEDIUM": 6, "POOR": 6})
        self.assertEqual(
            question_types,
            {"INITIAL": 6, "NEXT": 6, "FOLLOW_UP": 6},
        )

    def test_common_node_runs_for_every_case_with_injected_chain(self) -> None:
        for case in self.cases:
            with self.subTest(case_id=case["metadata"]["case_id"]):
                result = answer_evaluation_node(
                    case["inputs"], chain=FakeAnswerEvaluationChain()
                )
                evaluation = result["current_evaluation"]
                self.assertEqual(evaluation["overall_score"], 60.0)
                self.assertEqual(len(result["evaluation_history"]), 1)

    def test_exact_human_scores_produce_perfect_metrics(self) -> None:
        outputs = []
        references = []
        for case in self.cases:
            reference = case["reference_outputs"]
            scores = reference["human_scores"]
            output = {
                "scores": scores,
                "overall_score": calculate_overall_score(scores),
            }
            row_metrics = score_agreement_evaluator(
                outputs=output,
                reference_outputs=reference,
            )
            self.assertEqual(row_metrics[0]["score"], 1.0)
            self.assertEqual(row_metrics[1]["score"], 1.0)
            self.assertEqual(row_metrics[2]["score"], 0.0)
            self.assertEqual(row_metrics[3]["score"], 1)
            outputs.append(output)
            references.append(reference)

        summary = answer_reliability_summary(
            outputs=outputs,
            reference_outputs=references,
        )
        summary_by_key = {metric["key"]: metric["score"] for metric in summary}
        self.assertEqual(summary_by_key["within1_overall"], 1.0)
        self.assertEqual(summary_by_key["mae_overall"], 0.0)
        self.assertAlmostEqual(summary_by_key["spearman_overall"], 1.0)

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

    def test_failed_target_output_does_not_crash_evaluators(self) -> None:
        reference = self.cases[0]["reference_outputs"]
        row_metrics = score_agreement_evaluator(
            outputs={},
            reference_outputs=reference,
        )
        self.assertEqual(row_metrics[0]["key"], "evaluation_output_valid")
        self.assertEqual(row_metrics[0]["score"], 0)

        valid_scores = reference["human_scores"]
        summary = answer_reliability_summary(
            outputs=[
                {},
                {
                    "scores": valid_scores,
                    "overall_score": calculate_overall_score(valid_scores),
                },
            ],
            reference_outputs=[reference, reference],
        )
        summary_by_key = {metric["key"]: metric["score"] for metric in summary}
        self.assertEqual(summary_by_key["evaluation_output_coverage"], 0.5)


if __name__ == "__main__":
    unittest.main()
