# Router 정책 검증

사람이 현재 정책에 따라 미리 지정한 `expected_route`와 실제
`interview_review_node` 결과를 코드로 비교한다. LLM Judge는 사용하지 않는다.

## Dataset

| Suite | Case 수 | 구성 |
|---|---:|---|
| `regression` | 18 | Route별 6 |
| `final_holdout` | 30 | Route별 10 |

Final Holdout에는 69/70점, 질문 9/10개, 꼬리질문 1/2회, 마지막 역량, 남은 질문
슬롯, END와 FOLLOW_UP 조건이 동시에 충족되는 우선순위 사례를 포함한다.

## 지표

- `policy_conformance_rate`: 전체 정책 기대값을 맞힌 비율
- `boundary_scenario_pass_rate`: 경계 사례만 따로 맞힌 비율

Route별 Pass Rate는 진단 지표다. Router는 결정론적이므로 Case당 한 번만 실행하며
고정 정책에서는 두 대표 지표 모두 1.0이어야 한다. 오류나 불일치가 발생해도 실행을
중단해 숨기지 않고 실패 Case로 기록한다.

## 실행

로컬 정책 검증:

```powershell
.\.venv\Scripts\python.exe -m evals.router.run_eval --suite regression
.\.venv\Scripts\python.exe -m evals.router.run_eval --suite final_holdout
```

LangSmith에 최종 결과 기록:

```powershell
.\.venv\Scripts\python.exe -m evals.router.run_eval --suite final_holdout --include-diagnostics --run-langsmith
```

정책이 바뀌면 Expected Route를 몰래 덮어쓰지 않는다. 기존 Dataset은 Regression으로
남기고 정책 버전과 함께 새 Dataset을 만든다.
