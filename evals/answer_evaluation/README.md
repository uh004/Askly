# 답변 평가 신뢰성 검증

동일한 질문과 답변을 Human과 `answer_evaluation_node`가 각각 평가한 뒤
6개 세부 점수의 일치도를 비교한다.

## 구성

- `dataset_v1.jsonl`: GOOD/MEDIUM/POOR 각 6개, 총 18개 Case
- `target.py`: 실제 답변 평가 Node 실행
- `evaluators.py`: 점수 일치도, 근거성 Judge, Dataset 전체 Summary
- `metrics.py`: Within-1, MAE, Spearman 계산
- `rubric.md`: Human Label 기준

## 실행

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --check-langsmith
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --run-langsmith
```

LangSmith에서는 `within1_overall`, `mae_overall`, `spearman_overall`을 먼저 보고,
점수 차이가 큰 Case와 세부 항목을 확인한다.
