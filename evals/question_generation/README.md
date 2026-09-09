# 질문 생성 품질 검증

`question_generation_node`만 독립 실행하여 질문의 근거성, JD 관련성, 개인화,
FOLLOW_UP 적합성, Route 준수 및 근거 없는 가정을 평가한다.

## 구성

- `dataset_v1.jsonl`: INITIAL/FOLLOW_UP/NEXT 각 2개, 총 6개 Case
- `target.py`: 실제 질문 생성 Node 실행 Target
- `evaluators.py`: 코드 기반 Route 평가와 LLM-as-a-Judge
- `rubric.md`: Judge 점수 기준
- `run_eval.py`: 로컬 검증 및 LangSmith Experiment 실행기

## 실행

API 호출 없이 데이터와 Route 기대값만 검증:

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval
```

`.env`에 LangSmith Key를 설정한 뒤 LLM 호출 없이 연결 확인:

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --check-langsmith
```

OpenAI/LangSmith Key가 모두 설정되면 실제 평가 실행:

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --run-langsmith
```

동일한 Dataset 이름이 이미 있으면 기존 Dataset을 재사용한다. 검증셋 내용을
바꾼 경우 `--dataset-name askly-question-generation-v2`처럼 새 버전 이름을 사용한다.
