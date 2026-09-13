# 질문 생성 품질 검증

`question_generation_node`만 독립 실행하여 생성 질문의 근거성, JD 관련성,
개인화, Route 준수를 검증한다.

## Dataset

- `dataset_v1.jsonl`: 기존 기본 Case 6개
- `dataset_v2_additions.jsonl`: 현실적인 Hard Case 24개
- v2 전체: 30개 (`INITIAL / FOLLOW_UP / NEXT` 각 10개)
- v2 dev: 21개(각 Route 7개), 프롬프트 분석·수정용
- v2 holdout: 9개(각 Route 3개), 최종 일반화 확인용

Hard Case에는 서류와 JD의 약한 일치, 서류 정보 부족, 짧은 답변, 여러
`missing_points`, 근거 없는 기술 가정 위험, 유사 프로젝트 혼동을 포함한다.

## 핵심 지표

- `groundedness`
- `jd_relevance`
- `personalization`
- `route_compliance`

LLM Judge는 질문에 실제로 드러난 정보만 평가한다. 입력에 좋은 정보가 있다는
이유만으로 개인화나 JD 관련성을 높게 주지 않는다. 실패 원인 분석이 필요할 때만
`followup_relevance`, `unsupported_assumption_free`를 진단 지표로 추가한다.

## 실행 순서

로컬 구조와 Route를 먼저 검증한다.

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --dataset-version v2 --split dev
```

같은 dev Dataset에 v1과 v2 프롬프트를 실행한다.

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --dataset-version v2 --split dev --prompt-version v1 --experiment-prefix question-generation-v1-baseline-dev --run-langsmith
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --dataset-version v2 --split dev --prompt-version v2 --experiment-prefix question-generation-v2-improved-dev --run-langsmith
```

dev 개선을 확인한 뒤 holdout을 각각 한 번 실행한다.

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --dataset-version v2 --split holdout --prompt-version v1 --experiment-prefix question-generation-v1-baseline-holdout --run-langsmith
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --dataset-version v2 --split holdout --prompt-version v2 --experiment-prefix question-generation-v2-improved-holdout --run-langsmith
```

실제 생성된 두 Experiment 이름을 넣으면 비교표를 출력할 수 있다.

```powershell
.\.venv\Scripts\python.exe -m evals.compare_experiments --kind question --v1 <v1-experiment-name> --v2 <v2-experiment-name>
```

LangSmith 실행은 Dataset 내용을 외부 서비스로 전송하므로 실제 개인정보 대신
합성 또는 비식별 Case만 사용한다.
