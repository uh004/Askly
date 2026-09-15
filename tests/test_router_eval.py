from __future__ import annotations

import unittest
from collections import Counter

from evals.dataset_utils import dataset_content_hash
from evals.router.dataset import load_cases
from evals.router.evaluators import (
    policy_conformance_evaluator,
    router_diagnostic_summary,
    router_policy_summary,
)
from evals.router.run_eval import evaluate_locally
from evals.router.target import router_target
from src.nodes.interview_review import interview_review_node


class RouterEvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.regression_cases = load_cases(suite="regression")
        cls.holdout_cases = load_cases(suite="final_holdout")

    @staticmethod
    def _route_counts(cases: list[dict]) -> Counter:
        return Counter(
            case["reference_outputs"]["expected_route"] for case in cases
        )

    def test_regression_dataset_keeps_existing_18_cases(self) -> None:
        self.assertEqual(len(self.regression_cases), 18)
        self.assertEqual(
            self._route_counts(self.regression_cases),
            {"FOLLOW_UP": 6, "NEXT": 6, "END": 6},
        )

    def test_final_holdout_has_30_balanced_unique_cases(self) -> None:
        self.assertEqual(len(self.holdout_cases), 30)
        self.assertEqual(
            self._route_counts(self.holdout_cases),
            {"FOLLOW_UP": 10, "NEXT": 10, "END": 10},
        )
        ids = [case["metadata"]["case_id"] for case in self.holdout_cases]
        scenarios = [case["reference_outputs"]["scenario"] for case in self.holdout_cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(scenarios), len(set(scenarios)))
        self.assertGreaterEqual(
            sum(case["reference_outputs"]["is_boundary"] for case in self.holdout_cases),
            15,
        )

    def test_langsmith_managed_split_does_not_change_dataset_hash(self) -> None:
        case = self.holdout_cases[0]
        remote_case = {
            **case,
            "metadata": {**case["metadata"], "dataset_split": ["base"]},
        }
        self.assertEqual(
            dataset_content_hash([case]),
            dataset_content_hash([remote_case]),
        )

    def test_every_policy_case_matches_expected_route(self) -> None:
        for case in self.regression_cases + self.holdout_cases:
            with self.subTest(case_id=case["metadata"]["case_id"]):
                output = router_target(case["inputs"])
                evaluation = policy_conformance_evaluator(
                    outputs=output,
                    reference_outputs=case["reference_outputs"],
                )
                self.assertEqual(evaluation["score"], 1, evaluation["comment"])

    def test_perfect_predictions_produce_perfect_policy_metrics(self) -> None:
        outputs = [router_target(case["inputs"]) for case in self.holdout_cases]
        references = [case["reference_outputs"] for case in self.holdout_cases]
        summary = router_policy_summary(
            outputs=outputs,
            reference_outputs=references,
        )
        by_key = {metric["key"]: metric["score"] for metric in summary}
        self.assertEqual(by_key["policy_conformance_rate"], 1.0)
        self.assertEqual(by_key["boundary_scenario_pass_rate"], 1.0)

        diagnostics = router_diagnostic_summary(
            outputs=outputs,
            reference_outputs=references,
        )
        diagnostic_by_key = {
            metric["key"]: metric["score"] for metric in diagnostics
        }
        self.assertEqual(diagnostic_by_key["pass_rate_follow_up"], 1.0)
        self.assertEqual(diagnostic_by_key["pass_rate_next"], 1.0)
        self.assertEqual(diagnostic_by_key["pass_rate_end"], 1.0)

    def test_local_evaluation_reports_mismatch_instead_of_aborting(self) -> None:
        case = self.holdout_cases[0]
        mismatched = {
            **case,
            "reference_outputs": {
                **case["reference_outputs"],
                "expected_route": "END",
            },
        }
        summary, failures = evaluate_locally([mismatched])
        by_key = {metric["key"]: metric["score"] for metric in summary}
        self.assertEqual(by_key["policy_conformance_rate"], 0.0)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["case_id"], case["metadata"]["case_id"])

    def test_invalid_states_raise_clear_errors(self) -> None:
        valid = dict(self.regression_cases[0]["inputs"])
        invalid_cases = [
            {**valid, "current_evaluation": {}},
            {**valid, "question_count": -1},
            {
                **valid,
                "interview_history": [
                    {"competency": "문제 해결", "question_type": "FOLLOW_UP"}
                ],
                "followup_count": 0,
            },
        ]
        for state in invalid_cases:
            with self.subTest(state=state):
                with self.assertRaises(ValueError):
                    interview_review_node(state)

    def test_interview_can_end_before_maximum_question_count(self) -> None:
        competencies = ["문제 해결", "협업", "직무 이해"]
        result = interview_review_node(
            {
                "current_evaluation": {"overall_score": 82.0, "missing_points": []},
                "current_competency": competencies[-1],
                "target_competencies": competencies,
                "interview_history": [
                    {"competency": competency, "question_type": "INITIAL"}
                    for competency in competencies
                ],
                "question_count": 3,
                "followup_count": 0,
            }
        )
        self.assertEqual(result["route"], "END")

    def test_second_follow_up_is_allowed_for_same_competency(self) -> None:
        result = interview_review_node(
            {
                "current_evaluation": {
                    "overall_score": 64.0,
                    "missing_points": ["성과 측정 방법"],
                },
                "current_competency": "문제 해결",
                "target_competencies": ["문제 해결", "협업", "직무 이해"],
                "interview_history": [
                    {"competency": "문제 해결", "question_type": "INITIAL"},
                    {"competency": "문제 해결", "question_type": "FOLLOW_UP"},
                ],
                "question_count": 2,
                "followup_count": 1,
            }
        )
        self.assertEqual(result["route"], "FOLLOW_UP")


if __name__ == "__main__":
    unittest.main()
