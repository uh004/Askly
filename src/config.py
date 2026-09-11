"""Application settings shared by the interview pipeline."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DATABASE_URL = (
    os.getenv("DATABASE_URL", "").strip()
    or os.getenv("POSTGRES_URL", "").strip()
    or None
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_upload_dir(environ: Mapping[str, str] | None = None) -> Path:
    """Return a writable temporary upload directory for each runtime."""

    active_environ = os.environ if environ is None else environ
    configured_path = active_environ.get("UPLOAD_DIR", "").strip()
    if configured_path:
        return Path(configured_path)
    if active_environ.get("VERCEL"):
        return Path("/tmp") / "askly-uploads"
    return PROJECT_ROOT / "data" / "uploads"


UPLOAD_DIR = resolve_upload_dir()
MAX_RESUME_UPLOAD_BYTES = 10 * 1024 * 1024

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

MIN_RESUME_TEXT_LENGTH = 100
MIN_JOB_TEXT_LENGTH = 100
MAX_DOCUMENT_PARSING_ATTEMPTS = 2

MAX_INTERVIEW_STRATEGY_ATTEMPTS = 2
MIN_STRATEGY_EVIDENCE_COVERAGE = 0.65
MAX_QUESTION_GENERATION_ATTEMPTS = 2

MAX_INTERVIEW_QUESTIONS = 10
MAX_FOLLOWUPS_PER_COMPETENCY = 2
MIN_SUFFICIENT_SCORE = 70.0
