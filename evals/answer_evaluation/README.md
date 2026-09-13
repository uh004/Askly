# 답변 평가 신뢰성 검증

동일한 면접 답변을 Human Label과 `answer_evaluation_node`가 각각 평가했을 때
6개 항목의 점수와 답변 전체 품질 순서가 얼마나 일치하는지 검증한다.

## Dataset

- `dataset_v1.jsonl`: 기존 18개
- `dataset_v2_additions.jsonl`: 경계·혼합 품질 Case 18개
- v2 전체: 36개 (`GOOD / MEDIUM / POOR` 각 12개)
- 품질 3종 × 질문 유형 3종의 각 조합: 4개
- v2 dev: 27개(각 조합 3개), Rubric·프롬프트 수정용
- v2 holdout: 9개(각 조합 1개), 최종 일반화 확인용

## 핵심 지표

- `within1_overall`: 6개 항목별 Human-AI 차이가 ±1 이내인 비율
- `mae_overall`: 6개 항목별 평균 절대 오차
- `spearman_overall`: Case별 종합 점수로 계산한 답변 품질 순위 상관

오차 분석에서는 다음 6개 항목별 MAE, Within-1, Spearman을 확인한다.

- `relevance`
- `specificity`
- `logical_structure`
- `role_clarity`
- `action_clarity`
- `result_clarity`

## 실행 순서

로컬 Dataset을 먼저 검증한다.

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --dataset-version v2 --split dev
```

동일한 dev Dataset으로 v1과 v2를 실행한다. 항목별 오차를 남기기 위해 진단
실험을 사용한다.

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --dataset-version v2 --split dev --prompt-version v1 --experiment-prefix answer-evaluation-v1-baseline-dev --include-diagnostics --run-langsmith
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --dataset-version v2 --split dev --prompt-version v2 --experiment-prefix answer-evaluation-v2-improved-dev --include-diagnostics --run-langsmith
```

dev 결과에서 오차가 큰 항목만 수정한 후 holdout을 각각 한 번 실행한다.

```powershell
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --dataset-version v2 --split holdout --prompt-version v1 --experiment-prefix answer-evaluation-v1-baseline-holdout --run-langsmith
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --dataset-version v2 --split holdout --prompt-version v2 --experiment-prefix answer-evaluation-v2-improved-holdout --run-langsmith
```

실제 생성된 두 진단 Experiment 이름으로 전체·항목별 비교표를 출력한다.

```powershell
.\.venv\Scripts\python.exe -m evals.compare_experiments --kind answer --v1 <v1-experiment-name> --v2 <v2-experiment-name> --include-dimensions
```

LangSmith 실행은 Dataset 내용을 외부 서비스로 전송하므로 실제 개인정보 대신
합성 또는 비식별 Case만 사용한다.
