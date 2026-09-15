# Askly AI 면접관 Agent

지원자 서류와 채용공고를 분석해 면접 전략을 세우고, 질문 생성·답변 평가·진행
판단·최종 피드백까지 수행하는 LangGraph 기반 프로젝트입니다.

## 프로젝트 구조

```text
src/
├─ app.py          # Vercel용 FastAPI 진입점
├─ config.py       # 모델명과 질문·재시도 제한
├─ state.py        # 전체 Graph 공유 상태
├─ schemas/        # Pydantic Structured Output
├─ chains/         # Prompt + Model + Structured Output
├─ services/       # PDF 및 채용공고 파싱
├─ nodes/          # 단계별 LangGraph Node
├─ graph/          # 전체 Node 연결과 조건 분기
├─ persistence/    # 메모리/PostgreSQL Checkpointer 선택
└─ api/            # FastAPI 앱, 요청·응답 Schema, 면접 Route
```

Next.js 프론트엔드는 `frontend/`에 분리되어 있으며 FastAPI를 직접 호출합니다.

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

프론트엔드 주소는 `http://localhost:3000`이며, 로컬 FastAPI 주소는
`frontend/.env.local`의 `NEXT_PUBLIC_API_URL`로 설정합니다.

## 테스트와 CI

로컬에서 백엔드 테스트를 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

프론트엔드는 `frontend/`에서 검사합니다.

```powershell
npm.cmd run lint
npm.cmd run build
```

GitHub Actions는 Push와 Pull Request마다 백엔드 `pytest`와 프론트엔드
lint·production build를 자동으로 실행합니다.

[`notebooks/pipeline_v2.ipynb`](notebooks/pipeline_v2.ipynb)는 위 모듈을 불러와
구조와 실행 방법을 확인하는 용도로 사용합니다. 테스트 코드는 `tests/`와
`evals/`에서 관리합니다.

## FastAPI 실행

프로젝트 루트에서 의존성을 설치하고 개발 서버를 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload
```

- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `GET http://127.0.0.1:8000/health`
- 면접 시작: `POST /api/interviews/start`
- 답변 제출: `POST /api/interviews/{session_id}/answers`
- 상태·결과 조회: `GET /api/interviews/{session_id}`

면접 시작 요청은 `multipart/form-data` 형식으로 Resume PDF와
`job_posting_url`을 함께 전송합니다. 업로드 파일은 파싱 후 즉시 삭제됩니다.
`DATABASE_URL`이 없으면 세션은 개발용 메모리 저장소를 사용합니다.

## PostgreSQL 세션 저장

Vercel Marketplace에서 Neon을 연결한 뒤 pooled connection string을
`DATABASE_URL`에 설정합니다. 처음 연결할 때만 체크포인터 테이블을 생성합니다.

```powershell
.\.venv\Scripts\python.exe -m tools.setup_postgres_checkpointer
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload
```

실제 접속 문자열은 `.env`에만 넣고 Git에는 올리지 않습니다.

## 검증 구조

기존 데이터는 삭제하지 않고 **Regression Set**으로 보존하고, 새 데이터는 개발에
사용하지 않는 **Final Holdout Benchmark**로 분리합니다.

| 대상 | Regression | Final Holdout | 반복 | 대표 지표 |
|---|---:|---:|---:|---|
| 질문 생성 | 30 | Route별 10, 총 30 | 3회 | Groundedness / JD Relevance / Personalization |
| 답변 평가 | 36 | 품질별 10, 총 30 | 3회 | Overall MAE |
| Router | 18 | Route별 10, 총 30 | 1회 | Policy Conformance / Boundary Scenario Pass |

질문·답변은 LLM 출력의 변동을 확인하기 위해 Case당 3회 실행합니다. Router는
Python 규칙 기반이라 1회만 실행합니다. Final Holdout 결과를 본 뒤 Prompt나 정책을
수정했다면 그 Dataset은 Regression으로 전환하고 새로운 Holdout을 만들어야 합니다.

자세한 설계와 결과 해석 원칙은 [검증 운영 계획](evals/VALIDATION_PLAN.md)을
참고합니다.

## 검증 실행 방법

프로젝트 루트에서 먼저 API 호출이 없는 로컬 검증을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --suite regression
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --suite regression
.\.venv\Scripts\python.exe -m evals.router.run_eval --suite regression
```

답변 Final Holdout의 Reference Score는 AI 결과를 보기 전에 직접 검토합니다.

```powershell
.\.venv\Scripts\python.exe -m tools.review_answer_holdout
.\.venv\Scripts\python.exe -m tools.review_answer_holdout --status
```

Prompt·Reference·Router 정책을 동결한 다음 Final Holdout을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --suite final_holdout --prompt-version v2 --num-repetitions 3 --include-diagnostics --run-langsmith

.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --suite final_holdout --prompt-version v2 --num-repetitions 3 --include-diagnostics --confirm-reference-reviewed --run-langsmith

.\.venv\Scripts\python.exe -m evals.router.run_eval --suite final_holdout --include-diagnostics --run-langsmith
```

LangSmith 실행에는 `OPENAI_API_KEY`와 `LANGSMITH_API_KEY`가 필요합니다. 모든
평가 데이터는 합성 또는 비식별 정보만 사용합니다.
