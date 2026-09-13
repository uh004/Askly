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
| 질문 생성 | 서류·JD에 근거한 개인화 질문인지, 흐름과 Route를 지키는지 확인 | `INITIAL / FOLLOW_UP / NEXT` 각 2개, 총 6개 | Groundedness, JD Relevance, Personalization, Route Compliance |
| 답변 평가 | AI 점수가 Human 평가와 유사한지 확인 | `GOOD / MEDIUM / POOR` 각 6개, 총 18개 | Within-1 Agreement, MAE, Spearman Correlation |
| Router | 답변 점수와 진행 상태에 따라 `FOLLOW_UP / NEXT / END`를 정책대로 선택하는지 확인 | Route별 6개, 총 18개 경계값 Case | Accuracy, Macro F1, Confusion Matrix |

## 1. 질문 생성 품질 검증

### 검증 목적

- 지원자 서류와 채용공고에 근거한 개인화 질문을 생성하는지 검증
- 면접 상태에 따라 `INITIAL / FOLLOW_UP / NEXT` 흐름에 맞는 질문을 생성하는지 확인

### 검증 방법

- `INITIAL / FOLLOW_UP / NEXT` Case를 각 2개씩 균형 있게 구성
- 지원자 정보, JD, 이전 질문·답변, 현재 Route를 입력하여 질문 생성 Node만 독립 실행
- 질문의 의미 품질은 LangSmith LLM-as-a-Judge로 평가
- 생성된 질문 유형과 평가 역량이 기대값과 일치하는지는 코드로 비교
- 점수가 낮은 Case는 근거 없는 가정, 질문 중복, 부적절한 꼬리질문 여부를 추가 분석

### 평가지표

| 지표 | 쉽게 말하면 | 기준 |
|---|---|---:|
| Groundedness | 질문이 실제 서류·답변 내용에 근거하는가 | 4점 이상 |
| JD Relevance | 채용 직무와 확인하려는 역량에 관련되는가 | 4점 이상 |
| Personalization | 지원자의 구체적인 경험을 반영했는가 | 4점 이상 |
| Route Compliance | 질문 유형과 역량이 기대값과 일치하는가 | 1.0 |

FOLLOW_UP 적합성과 근거 없는 가정 여부는 점수가 낮은 Case의 진단 지표로
유지하며, FOLLOW_UP 근거성과 문서에 없는 사실의 전제 여부는 Groundedness
Rubric에도 포함합니다.

폴더: [`evals/question_generation`](evals/question_generation/README.md)

## 2. 답변 평가 신뢰성 검증

### 검증 목적

- AI가 동일한 기준으로 답변을 일관되게 평가하는지 검증
- AI 평가 결과가 사람이 같은 Rubric으로 평가한 결과와 유사한지 확인

### 검증 방법

- 좋은 답변, 보통 답변, 부족한 답변 Case를 각 6개씩 균형 있게 구성
- Human과 AI가 `relevance`, `specificity`, `logical_structure`, `role_clarity`,
  `action_clarity`, `result_clarity`의 동일한 6개 기준으로 답변을 평가
- AI 결과를 확인하기 전에 작성한 Human Score를 정답값으로 사용
- Human Score와 AI Score의 차이와 품질 순위를 코드로 계산
- 점수 차이가 큰 Case는 답변에 없는 근거 사용과 누락 항목 판단 오류를 추가 분석

### 평가지표

| 지표 | 쉽게 말하면 | 초기 목표 |
|---|---|---:|
| Within-1 Agreement | Human과 AI 점수 차이가 1점 이내인 비율 | 0.80 이상 |
| MAE | Human과 AI 점수가 평균적으로 몇 점 차이 나는가 | 1.00 이하 |
| Spearman Correlation | Human이 높게 평가한 답변을 AI도 높게 평가하는가 | 0.70 이상 |

Within-1과 MAE는 낮거나 높은 답변 하나가 아닌 전체 일치도를 보고, Spearman은
답변 품질의 순위를 비슷하게 판단하는지 확인합니다. 항목별 오차, 평가 근거성과
누락 항목 타당성은 점수 차이가 큰 실패 Case의 진단 지표로 사용합니다.

폴더: [`evals/answer_evaluation`](evals/answer_evaluation/README.md)

## 3. Router 판단 성능 검증

### 검증 목적

- 답변 평가 결과와 면접 진행 상태에 따라 Router가 정책대로 판단하는지 검증
- `FOLLOW_UP / NEXT / END` 전환이 정확하게 이루어지는지 확인

### 검증 방법

- `FOLLOW_UP / NEXT / END` Case를 각 6개씩 균형 있게 구성
- 사람이 Router 정책표에 따라 각 Case의 `expected_route`를 사전에 지정
- 답변 점수, 누락 항목, 질문 수, 꼬리질문 수와 남은 역량을 Router에 입력
- 실제 Route와 `expected_route`를 코드로 비교
- 점수 69·70점, 질문 9·10개, 꼬리질문 1·2개와 남은 질문 슬롯 등의 경계 Case 포함

### 평가지표

| 지표 | 쉽게 말하면 | 기준 |
|---|---|---:|
| Accuracy | 전체 Route를 맞힌 비율 | 1.0 |
| Macro F1 | 세 Route 중 특정 Route에 치우치지 않고 모두 맞히는가 | 1.0 |
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

기존 상세 지표까지 실패 Case 분석에 사용하려면 각 명령에
`--include-diagnostics`를 추가합니다. 기본 실행은 위 표의 핵심 지표만 기록합니다.

각 실행은 서로 다른 LangSmith Dataset을 만들지만 모든 Trace는
`askly-agent-eval` Project에서 함께 관리합니다.
