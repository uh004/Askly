"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import interviews_router
from src.api.schemas import HealthResponse
from src.config import CORS_ORIGINS


app = FastAPI(
    title="Askly Interview API",
    version="0.1.0",
    description="지원자 서류와 채용공고를 기반으로 모의면접을 진행하는 API",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(interviews_router, prefix="/api")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    return HealthResponse()
