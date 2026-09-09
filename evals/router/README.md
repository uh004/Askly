# Router 판단 성능 검증

`interview_review_node`만 독립 실행하고 사람이 정책표에 따라 미리 지정한
`expected_route`와 비교한다. LLM Judge는 사용하지 않는다.

## 구성

- `dataset_v1.jsonl`: FOLLOW_UP/NEXT/END 각 6개, 총 18개 경계값 Case
- `target.py`: 실제 Router Node 실행
- `evaluators.py`: Accuracy, Macro F1, 클래스별 F1, Confusion Matrix
- `policy.md`: 현재 Router 정책과 임계값

## 실행

```powershell
.\.venv\Scripts\python.exe -m evals.router.run_eval
.\.venv\Scripts\python.exe -m evals.router.run_eval --check-langsmith
.\.venv\Scripts\python.exe -m evals.router.run_eval --run-langsmith
```

Router는 결정론적이므로 기준 성능은 `Accuracy=1.0`, `Macro F1=1.0`이다.
