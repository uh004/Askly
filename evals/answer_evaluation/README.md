# 답변 평가 신뢰성 검증

같은 답변에 대해 미리 확정한 6개 Reference Score와
`answer_evaluation_node`의 점수 차이를 검증한다.

## Dataset

| Suite | Case 수 | 구성 | 용도 |
|---|---:|---|---|
| `regression` | 36 | 품질·질문 유형 각 12 | Prompt 수정과 회귀 확인 |
| `final_holdout` | 30 | GOOD/MEDIUM/POOR 각 10, 질문 유형 각 10 | 최종 일반화 확인 |

Final Holdout은 품질×질문 유형 9개 조합을 각 3~4건으로 구성했다. 답변 길이만
달리하지 않고 관련성, 구체성, 역할, 행동, 결과 중 특정 요소만 약한 사례와 질문에서
벗어난 사례를 포함한다.

## 지표

대표 지표는 `mae_overall` 하나다. 6개 항목에서 Reference와 AI 점수의 절대 차이를
모두 평균하며 낮을수록 좋다.

진단용으로 다음 6개 항목별 MAE와 출력 성공률을 확인한다.

- `relevance`
- `specificity`
- `logical_structure`
- `role_clarity`
- `action_clarity`
- `result_clarity`

잘못된 Structured Output은 제외하지 않고 4점 오차로 계산한다.

## Reference 검토

Final Holdout의 초기 점수는 Rubric으로 작성한 초안이다. AI 평가를 실행하기 전에
아래 명령으로 30건을 읽고, 그대로 승인하거나 점수를 고친다.

```powershell
.\.venv\Scripts\python.exe -m tools.review_answer_holdout
```

진행 상태만 확인하려면:

```powershell
.\.venv\Scripts\python.exe -m tools.review_answer_holdout --status
```

`a`는 현재 점수 승인, `e`는 수정 후 승인, `s`는 건너뛰기, `q`는 저장 후
종료다. 모든 Case가 승인되지 않으면 Final Holdout 실행기는 중단된다.

## 실행

로컬 구조 확인:

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --suite regression
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --suite final_holdout
```

개발 중 Regression 실험:

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --suite regression --prompt-version v2 --num-repetitions 3 --include-diagnostics --run-langsmith
```

Reference 승인과 Prompt 동결 후 Final Holdout:

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --suite final_holdout --prompt-version v2 --num-repetitions 3 --include-diagnostics --confirm-reference-reviewed --run-langsmith
```
