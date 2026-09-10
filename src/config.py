"""Application settings shared by the interview pipeline."""

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

MIN_RESUME_TEXT_LENGTH = 100
MIN_JOB_TEXT_LENGTH = 100
MAX_DOCUMENT_PARSING_ATTEMPTS = 2

MAX_INTERVIEW_STRATEGY_ATTEMPTS = 2
MIN_STRATEGY_EVIDENCE_COVERAGE = 0.65
MAX_QUESTION_GENERATION_ATTEMPTS = 2

MAX_INTERVIEW_QUESTIONS = 10
MAX_FOLLOWUPS_PER_COMPETENCY = 2
MIN_SUFFICIENT_SCORE = 70.0

