"""Candidate and job-description analysis chains."""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import OPENAI_MODEL
from src.schemas.analysis import CandidateProfile, JobDescriptionAnalysis


candidate_analysis_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
당신은 이력서와 자기소개서에서 사실만 추출해 구조화하는 분석가입니다.

[공통 원칙]
- 문서에 없는 내용은 추측하거나 지원자를 평가하지 마세요.
- 확인할 수 없는 단일 값은 빈 문자열, 목록 값은 빈 목록으로 반환하세요.
- 모든 결과는 한국어로 작성하세요.

[구조화 기준]
- 프로젝트·경험은 역할, 수행 행동, 사용 기술, 정량/정성 성과를 구분하세요.
- evidence에는 분석 결과를 뒷받침하는 서류 원문의 핵심 사실만 작성하세요.
- evidence는 가능한 사실만 최대 5개까지 작성하며, 근거가 없으면 빈 목록으로 반환하세요.
""".strip(),
        ),
        ("human", "다음 지원자 서류를 구조화하세요.\n\n{resume_text}"),
    ]
)

jd_analysis_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
당신은 채용공고에서 직무 정보를 사실대로 추출해 구조화하는 분석가입니다.

[공통 원칙]
- 지원자와의 적합도, 면접 질문, 평가 방향은 판단하지 마세요.
- 공고에 없는 정보는 추측하지 마세요.
- 확인할 수 없는 단일 값은 빈 문자열, 목록 값은 빈 목록으로 반환하세요.
- 모든 결과는 한국어로 작성하세요.

[자격요건 및 기술 분류]
- 기술은 공고의 섹션 제목과 위치를 기준으로 분류하세요.
- 자격요건 또는 필수요건 섹션에 직접 등장한 기술명만 required_skills에 저장하세요.
- 우대사항 섹션에 직접 등장한 기술명만 preferred_skills에 저장하세요.
- required_skills와 preferred_skills 사이에서 기술을 임의로 옮기지 마세요.
- API 연동 경험, LLM 프로젝트 경험처럼 경험으로 표현되어도 해당 섹션에 기술명이 명시되었다면 기술명만 추출해 해당 skills 목록에 함께 저장하세요.
- skills에는 전체 자격 문장을 복사하지 말고, '사용 경험', '프로젝트 경험', '관심' 등을 제외한 짧은 기술명만 저장하세요.
- required_qualifications와 preferred_qualifications에는 원래 조건 문장을 보존하세요.

[근거]
- evidence에는 분석 결과를 뒷받침하는 공고 원문의 핵심 사실만 작성하세요.
- evidence는 가능한 사실만 최대 5개까지 작성하며, 근거가 없으면 빈 목록으로 반환하세요.
""".strip(),
        ),
        ("human", "다음 채용공고를 구조화하세요.\n\n{job_description_text}"),
    ]
)

_candidate_analysis_chain: Any | None = None
_jd_analysis_chain: Any | None = None


def build_candidate_analysis_chain(model: str | None = None) -> Any:
    llm = ChatOpenAI(model=model or OPENAI_MODEL, temperature=0)
    return candidate_analysis_prompt | llm.with_structured_output(
        CandidateProfile,
        method="function_calling",
        include_raw=False,
    )


def build_jd_analysis_chain(model: str | None = None) -> Any:
    llm = ChatOpenAI(model=model or OPENAI_MODEL, temperature=0)
    return jd_analysis_prompt | llm.with_structured_output(
        JobDescriptionAnalysis,
        method="function_calling",
        include_raw=False,
    )


def get_candidate_analysis_chain() -> Any:
    global _candidate_analysis_chain
    if _candidate_analysis_chain is None:
        _candidate_analysis_chain = build_candidate_analysis_chain()
    return _candidate_analysis_chain


def get_jd_analysis_chain() -> Any:
    global _jd_analysis_chain
    if _jd_analysis_chain is None:
        _jd_analysis_chain = build_jd_analysis_chain()
    return _jd_analysis_chain
