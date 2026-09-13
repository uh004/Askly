# 답변 평가 신뢰성 검증

동일한 질문과 답변을 Human과 `answer_evaluation_node`가 각각 평가한 뒤
6개 세부 점수의 일치도를 비교한다.

## 구성

- `dataset_v1.jsonl`: GOOD/MEDIUM/POOR 각 6개, 총 18개 Case
- `target.py`: 실제 답변 평가 Node 실행
- `evaluators.py`: 핵심 점수 일치도와 실패 분석용 진단 지표
- `metrics.py`: Within-1, MAE, Spearman 계산
- `rubric.md`: Human Label 기준

## 실행

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --check-langsmith
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --run-langsmith
```

기본 실행은 `within1_overall`, `mae_overall`, `spearman_overall`만 Summary 핵심
지표로 기록한다. 항목별 오차, 출력 Coverage, 평가 근거성과 누락 항목 타당성까지
확인하려면 다음과 같이 실행한다.

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --run-langsmith --include-diagnostics
```
