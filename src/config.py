"""Application settings shared by the interview pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
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
