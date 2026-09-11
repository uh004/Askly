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
.\.venv\Scripts\python.exe -m pytest
```

프론트엔드는 `frontend/`에서 검사합니다.

```powershell
npm.cmd run lint
npm.cmd run build
```

GitHub Actions는 Push와 Pull Request마다 백엔드 `pytest`와 프론트엔드
lint·production build를 자동으로 실행합니다.

[`notebooks/pipeline_v2.ipynb`](notebooks/pipeline_v2.ipynb)는 위 모듈을 불러와
구조와 실행 방법을 확인하는 용도로 사용합니다. 테스트 코드는 노트북에서 실행하지
않고 `tests/`와 `evals/`에서 관리합니다. FastAPI와 Next.js는 이 구조 위에 다음
단계로 연결합니다.

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

면접 시작 요청은 `multipart/form-data` 형식으로 `resume_file` PDF와
`job_posting_url`을 함께 전송합니다. 업로드 파일은 파싱 후 즉시 삭제됩니다.
로컬에서는 `data/uploads`, Vercel에서는 쓰기 가능한 `/tmp/askly-uploads`를
임시 경로로 사용합니다.
`DATABASE_URL`이 없으면 세션 상태는 개발용 `InMemorySaver`에 저장되어 서버를
재시작하면 사라집니다. Neon 등 PostgreSQL을 연결하면 세션 상태가 영구 저장됩니다.

## PostgreSQL 세션 저장

Vercel Marketplace에서 Neon을 연결한 뒤 발급된 pooled connection string을
`DATABASE_URL`에 설정합니다. 처음 연결할 때만 체크포인터 테이블을 생성합니다.

```powershell
.\.venv\Scripts\python.exe -m tools.setup_postgres_checkpointer
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload
```

로컬 개발이나 CI처럼 `DATABASE_URL`이 없는 환경은 별도 설정 없이 메모리 저장소를
사용합니다. 실제 접속 문자열은 `.env`에만 넣고 Git에는 올리지 않습니다.

## 검증 구조 한눈에 보기

세 검증은 같은 LangSmith Project를 사용하고 Dataset과 Experiment 이름으로 구분합니다.

```env
LANGSMITH_PROJECT=askly-agent-eval
```

| 검증 대상 | 검증 목적 | 검증셋 | 핵심 지표 |
|---|---|---|---|
| 질문 생성 | 서류·JD에 근거한 개인화 질문인지, 흐름과 Route를 지키는지 확인 | `INITIAL / FOLLOW_UP / NEXT` 각 2개, 총 6개 | Groundedness, JD Relevance, Personalization, Follow-up Relevance, Route Compliance, Unsupported Assumption Free |
| 답변 평가 | AI 점수가 Human 평가와 비슷하고 답변에 있는 사실만 근거로 삼는지 확인 | `GOOD / MEDIUM / POOR` 각 6개, 총 18개 | Within-1 Agreement, MAE, Spearman Correlation, Evidence Groundedness, Missing Point Validity |
| Router | 답변 점수와 진행 상태에 따라 `FOLLOW_UP / NEXT / END`를 정책대로 선택하는지 확인 | Route별 6개, 총 18개 경계값 Case | Accuracy, Macro F1, 클래스별 F1, Confusion Matrix |

## 1. 질문 생성 품질 검증

### 검증 목적과 검증셋

| 구분 | 내용 |
|---|---|
| 목적 | 지원자 서류, 채용공고, 이전 답변에 근거한 개인화 질문인지 확인 |
| 검증셋 | `candidate_profile`, `jd_analysis`, `interview_strategy`, `route`, `current_competency`, `current_evaluation`, `interview_history`, 근거 자료 |
| Case 구성 | `INITIAL`, `FOLLOW_UP`, `NEXT` 각 2개 |
| 평가 방식 | 의미 품질은 LLM-as-a-Judge, Route 일치는 코드로 평가 |

### 핵심 지표

| 지표 | 쉽게 말하면 | 기준 |
|---|---|---:|
| Groundedness | 질문이 실제 서류·답변 내용에 근거하는가 | 4점 이상 |
| JD Relevance | 채용 직무와 확인하려는 역량에 관련되는가 | 4점 이상 |
| Personalization | 지원자의 구체적인 경험을 반영했는가 | 4점 이상 |
| Follow-up Relevance | 꼬리질문이 직전 답변의 부족한 부분을 확인하는가 | FOLLOW_UP에서 4점 이상 |
| Route Compliance | 질문 유형과 역량이 기대값과 일치하는가 | 1.0 |
| Unsupported Assumption Free | 문서에 없는 경험을 사실처럼 가정하지 않았는가 | 1.0 |

폴더: [`evals/question_generation`](evals/question_generation/README.md)

## 2. 답변 평가 신뢰성 검증

### 검증 목적과 검증셋

| 구분 | 내용 |
|---|---|
| 목적 | AI가 정해진 기준으로 일관되게 평가하고 Human 점수와 유사한지 확인 |
| 검증셋 | 질문, 답변, 역량, 질문 유형, 면접 전략, Human 6개 항목 점수 |
| Case 구성 | 좋은 답변, 보통 답변, 부족한 답변 각 6개 |
| Human 점수 | `relevance`, `specificity`, `logical_structure`, `role_clarity`, `action_clarity`, `result_clarity` |
| 평가 방식 | Human-AI 점수는 코드 비교, 근거성과 누락 판단은 LLM-as-a-Judge |

### 핵심 지표

| 지표 | 쉽게 말하면 | 초기 목표 |
|---|---|---:|
| Within-1 Agreement | Human과 AI 점수 차이가 1점 이내인 비율 | 0.80 이상 |
| MAE | Human과 AI 점수가 평균적으로 몇 점 차이 나는가 | 1.00 이하 |
| Spearman Correlation | Human이 높게 평가한 답변을 AI도 높게 평가하는가 | 0.70 이상 |
| Evidence Groundedness | AI의 평가 근거가 실제 답변에 존재하는가 | 4점 이상 |
| Missing Point Validity | AI가 지적한 부족한 점이 질문 의도에 비추어 타당한가 | 4점 이상 |

Within-1과 MAE는 낮거나 높은 답변 하나가 아닌 전체 일치도를 보고, Spearman은
답변 품질의 순위를 비슷하게 판단하는지 확인합니다. 세 지표는 6개 평가 항목별과
전체 평균으로 모두 계산합니다.

폴더: [`evals/answer_evaluation`](evals/answer_evaluation/README.md)

## 3. Router 판단 성능 검증

### 검증 목적과 검증셋

| 구분 | 내용 |
|---|---|
| 목적 | 답변 평가와 진행 횟수에 따라 다음 Route를 정책대로 선택하는지 확인 |
| 검증셋 | `current_evaluation`, 현재/목표 역량, 면접 기록, 질문 수, 꼬리질문 수, `expected_route` |
| Case 구성 | `FOLLOW_UP`, `NEXT`, `END` 각 6개 |
| 경계값 | 점수 69·70점, 질문 9·10개, 역량별 꼬리질문 1·2개, 남은 질문 슬롯 |
| 평가 방식 | 실제 Route와 사람이 정책표에 따라 지정한 Route를 코드로 비교 |

### 핵심 지표

| 지표 | 쉽게 말하면 | 기준 |
|---|---|---:|
| Accuracy | 전체 Route를 맞힌 비율 | 1.0 |
| Macro F1 | 세 Route 중 특정 Route에 치우치지 않고 모두 맞히는가 | 1.0 |
| 클래스별 F1 | FOLLOW_UP, NEXT, END 각각의 정확성 | 각 1.0 |
| Confusion Matrix | 어떤 Route를 다른 Route로 잘못 판단했는가 | 대각선 외 0건 |

Router는 LLM이 아닌 결정 규칙이므로 현재 고정 검증셋에서는 모든 Case가 통과해야
합니다. 정책 변경 시 Dataset의 기대값을 먼저 검토하고 새 버전으로 실행합니다.

폴더: [`evals/router`](evals/router/README.md)

## 실행 방법

프로젝트 루트 `C:\Users\USER\Desktop\Askly`에서 실행합니다.

```powershell
# API 호출 없는 로컬 구조·정책 검증
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval
.\.venv\Scripts\python.exe -m evals.router.run_eval

# LangSmith Experiment 실행
.\.venv\Scripts\python.exe -m evals.question_generation.run_eval --run-langsmith
.\.venv\Scripts\python.exe -m evals.answer_evaluation.run_eval --run-langsmith
.\.venv\Scripts\python.exe -m evals.router.run_eval --run-langsmith
```

각 실행은 서로 다른 LangSmith Dataset을 만들지만 모든 Trace는
`askly-agent-eval` Project에서 함께 관리합니다.
