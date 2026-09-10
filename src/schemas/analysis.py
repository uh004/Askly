"""Structured outputs for candidate and job-description analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateExperience(BaseModel):
    organization: str = Field(
        description="회사, 학교, 팀 등 경험이 발생한 조직명. 없으면 빈 문자열"
    )
    role: str = Field(description="직책 또는 담당 역할. 없으면 빈 문자열")
    period: str = Field(description="문서에 적힌 활동 기간. 없으면 빈 문자열")
    responsibilities: list[str] = Field(description="문서에 명시된 담당 업무와 행동")
    achievements: list[str] = Field(description="수치나 결과가 명시된 성과")


class CandidateProject(BaseModel):
    name: str = Field(description="문서에 명시된 프로젝트명. 없으면 빈 문자열")
    summary: str = Field(description="프로젝트 목적과 결과를 사실 중심으로 요약")
    role: str = Field(description="지원자의 역할. 없으면 빈 문자열")
    technologies: list[str] = Field(description="프로젝트에서 사용한 기술")
    responsibilities: list[str] = Field(description="직접 수행한 작업")
    achievements: list[str] = Field(description="문서에 명시된 결과와 성과")


class CandidateProfile(BaseModel):
    summary: str = Field(description="지원자 경력과 경험의 사실 기반 요약")
    education: list[str] = Field(description="학력과 교육 이력")
    experiences: list[CandidateExperience] = Field(
        description="경력, 인턴, 동아리 등 주요 경험"
    )
    projects: list[CandidateProject] = Field(description="주요 프로젝트")
    technical_skills: list[str] = Field(
        description="문서에서 확인되는 언어, 프레임워크, 도구, 플랫폼"
    )
    certifications: list[str] = Field(description="자격증과 공인 인증")
    evidence: list[str] = Field(
        max_length=5,
        description=(
            "지원자 분석 결과를 뒷받침하는 원문 속 핵심 사실 3~5개. "
            "서류에 실제로 존재하는 내용만 작성"
        ),
    )


class JobDescriptionAnalysis(BaseModel):
    company_name: str = Field(description="채용 회사명. 없으면 빈 문자열")
    position: str = Field(description="채용 포지션명. 없으면 빈 문자열")
    role_summary: str = Field(description="직무의 목적과 역할을 사실 중심으로 요약")
    main_responsibilities: list[str] = Field(description="주요 업무")
    required_qualifications: list[str] = Field(description="필수 자격요건")
    preferred_qualifications: list[str] = Field(description="우대사항")
    required_skills: list[str] = Field(
        description=(
            "필수 자격요건에 등장하는 기술, 언어, 프레임워크, 도구, 플랫폼명. "
            "활용 경험이나 프로젝트 경험으로 표현되어도 기술명만 추출하고, "
            "명시된 기술이 없으면 빈 목록"
        )
    )
    preferred_skills: list[str] = Field(
        description=(
            "우대사항에 등장하는 기술, 언어, 프레임워크, 도구, 플랫폼명. "
            "사용 경험이나 프로젝트 경험으로 표현되어도 기술명만 추출하고, "
            "명시된 기술이 없으면 빈 목록"
        )
    )
    experience_level: str = Field(description="신입, 경력 등 요구 경력. 없으면 빈 문자열")
    employment_type: str = Field(description="정규직, 인턴 등 고용 형태. 없으면 빈 문자열")
    location: str = Field(description="근무 지역. 없으면 빈 문자열")
    benefits: list[str] = Field(description="혜택과 복지")
    hiring_process: list[str] = Field(description="채용 절차와 제출 안내")
    evidence: list[str] = Field(
        min_length=3,
        max_length=5,
        description=(
            "채용공고 분석 결과를 뒷받침하는 원문 속 핵심 사실 3~5개. "
            "공고에 실제로 존재하는 내용만 작성"
        ),
    )
