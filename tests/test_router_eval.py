from __future__ import annotations

import unittest
from collections import Counter

from evals.router.dataset import load_cases
from evals.router.evaluators import router_classification_summary
from evals.router.target import router_target
from src.nodes.interview_review import interview_review_node


class RouterEvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_cases()

    def test_dataset_is_balanced(self) -> None:
        counts = Counter(
            case["reference_outputs"]["expected_route"] for case in self.cases
        )
        self.assertEqual(counts, {"FOLLOW_UP": 6, "NEXT": 6, "END": 6})

    def test_every_policy_case_matches_expected_route(self) -> None:
        for case in self.cases:
            with self.subTest(case_id=case["metadata"]["case_id"]):
                output = router_target(case["inputs"])
                self.assertEqual(
                    output["route"],
                    case["reference_outputs"]["expected_route"],
                )

    def test_perfect_predictions_produce_perfect_summary(self) -> None:
        outputs = [router_target(case["inputs"]) for case in self.cases]
        references = [case["reference_outputs"] for case in self.cases]
        summary = router_classification_summary(
            outputs=outputs,
            reference_outputs=references,
        )
        by_key = {metric["key"]: metric["score"] for metric in summary}
        self.assertEqual(by_key["accuracy"], 1.0)
        self.assertEqual(by_key["macro_f1"], 1.0)
        self.assertEqual(by_key["cm_follow_up_to_follow_up"], 6)
        self.assertEqual(by_key["cm_next_to_next"], 6)
        self.assertEqual(by_key["cm_end_to_end"], 6)

    def test_invalid_states_raise_clear_errors(self) -> None:
        valid = dict(self.cases[0]["inputs"])
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


if __name__ == "__main__":
    unittest.main()
