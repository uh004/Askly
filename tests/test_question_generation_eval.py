from __future__ import annotations

import unittest
from collections import Counter

from evals.question_generation.dataset import load_cases
from evals.question_generation.evaluators import (
    QuestionQualityJudgment,
    route_compliance_evaluator,
)
from src.nodes.question_generation import (
    GeneratedInterviewQuestion,
    question_generation_node,
)


class FakeQuestionChain:
    def invoke(self, payload: dict) -> GeneratedInterviewQuestion:
        return GeneratedInterviewQuestion(
            question=(
                f"{payload['current_competency']} 역량과 관련해 본인이 수행한 "
                "구체적인 행동과 그 결과를 설명해 주시겠습니까? 두 번째 질문?"
            )
        )


class QuestionGenerationEvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_cases()

    def test_dataset_is_balanced(self) -> None:
        counts = Counter(
            case["reference_outputs"]["expected_question_type"]
            for case in self.cases
        )
        self.assertEqual(counts, {"INITIAL": 2, "FOLLOW_UP": 2, "NEXT": 2})

    def test_judge_schema_accepts_empty_assumption_reason(self) -> None:
        judgment = QuestionQualityJudgment.model_validate(
            {
                "groundedness": {"score": 5, "reason": "근거와 직접 연결됨"},
                "jd_relevance": {"score": 5, "reason": "JD와 직접 관련됨"},
                "personalization": {"score": 5, "reason": "지원자 경험을 반영함"},
                "followup_relevance": None,
                "unsupported_assumption": False,
                "unsupported_assumption_reason": "",
            }
        )
        self.assertEqual(judgment.unsupported_assumption_reason, "")

    def test_node_matches_expected_route_for_every_case(self) -> None:
        for case in self.cases:
            with self.subTest(case_id=case["metadata"]["case_id"]):
                result = question_generation_node(
                    case["inputs"],
                    chain=FakeQuestionChain(),
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


if __name__ == "__main__":
    unittest.main()
