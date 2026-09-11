# Askly Frontend

Askly FastAPI와 연결되는 Next.js App Router 프론트엔드입니다.

## 로컬 실행

먼저 프로젝트 루트에서 FastAPI를 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload
```

다른 터미널에서 프론트엔드를 실행합니다.

```powershell
cd frontend
npm.cmd run dev
```

- 프론트엔드: `http://localhost:3000`
- FastAPI 문서: `http://127.0.0.1:8000/docs`

FastAPI 주소가 다르면 `.env.local`의 `NEXT_PUBLIC_API_URL`을 변경합니다.

## 화면 경로

- `/`: 대시보드
- `/interviews/new`: 새 모의면접
- `/interviews/[sessionId]`: 면접 진행
- `/interviews/[sessionId]/result`: 결과 리포트
