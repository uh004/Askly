# 질문 생성 품질 검증

지원자 서류, 채용공고와 면접 문맥을 입력해 `question_generation_node`만 실행하고
질문 문장 자체의 품질을 평가한다.

## Dataset

| Suite | Case 수 | 용도 |
|---|---:|---|
| `regression` | 30, Route별 10 | Prompt 수정과 회귀 확인 |
| `final_holdout` | 30, Route별 10 | 최종 일반화 확인 |

Final Holdout에는 일반 사례, 서류-JD 약한 일치, 서류 정보 부족, FOLLOW_UP의 여러
누락 항목, 지원자가 쓰지 않은 기술을 사용했다고 전제할 위험을 포함한다.

## 지표

포트폴리오 대표 지표는 LLM-as-a-Judge의 다음 세 가지다.

- `groundedness`: 서류·JD·이전 답변에 근거했는가
- `jd_relevance`: 실제 채용공고의 업무·역량과 관련 있는가
- `personalization`: 특정 지원자의 경험이 질문 문장에 드러나는가

`route_compliance`는 코드 검증으로 항상 함께 기록한다.
`followup_relevance`, `unsupported_assumption_free`는 실패 분석용이다.

생성 모델과 Judge 모델은 가능하면 다르게 설정한다. 같은 모델을 쓰면 자기평가
편향 가능성을 결과의 한계로 적는다.

## 실행

API를 호출하지 않고 Dataset과 질문 유형 선택만 확인한다.

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --suite regression
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --suite final_holdout
```

개발 중 Regression 실험:

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --suite regression --prompt-version v2 --num-repetitions 3 --include-diagnostics --run-langsmith
```

Prompt를 동결한 뒤 한 번만 실행할 Final Holdout:

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --suite final_holdout --prompt-version v2 --num-repetitions 3 --include-diagnostics --run-langsmith
```

실행에는 `OPENAI_API_KEY`와 `LANGSMITH_API_KEY`가 필요하다. Dataset은 외부
서비스로 전송되므로 합성 또는 비식별 사례만 사용한다.
