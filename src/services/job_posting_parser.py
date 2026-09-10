"""Supported job-posting URL parsers."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from .text import normalize_text, redact_personal_info


COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}


def extract_saramin_rec_idx(url: str) -> str:
    parsed = urlparse(url)
    rec_idx = parse_qs(parsed.query).get("rec_idx", [None])[0]
    if not rec_idx:
        match = re.search(r"rec_idx=(\d+)", url)
        rec_idx = match.group(1) if match else None
    if not rec_idx or not rec_idx.isdigit():
        raise ValueError("사람인 URL에서 rec_idx 값을 찾을 수 없습니다.")
    return rec_idx


def parse_saramin_job(url: str, timeout: int = 15) -> dict[str, Any]:
    """Parse a Saramin posting, using its mobile page as a fallback."""

    rec_idx = extract_saramin_rec_idx(url)
    main_url = f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rec_idx}"
    detail_url = (
        f"https://www.saramin.co.kr/zf_user/jobs/relay/view-detail?rec_idx={rec_idx}"
    )
    mobile_url = f"https://m.saramin.co.kr/job-search/job-detail?rec_idx={rec_idx}"

    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    session.headers.update({"Referer": main_url})

    company_name = "회사명 미상"
    position = "공고명 미상"
    raw_body = ""
    parsed_from = ""

    try:
        main_response = session.get(main_url, timeout=timeout)
        if main_response.ok:
            main_soup = BeautifulSoup(main_response.text, "html.parser")
            og_title = main_soup.select_one("meta[property='og:title']")
            if og_title and og_title.get("content"):
                title_text = og_title["content"].replace(" - 사람인", "").strip()
                title_match = re.match(r"^\[(.*?)\]\s*(.*)$", title_text)
                if title_match:
                    company_name = title_match.group(1).strip()
                    position = title_match.group(2).strip()
                else:
                    position = title_text
    except requests.RequestException:
        pass

    try:
        detail_response = session.get(detail_url, timeout=timeout)
        if detail_response.ok:
            detail_soup = BeautifulSoup(detail_response.text, "html.parser")
            for tag in detail_soup.select("script, style, iframe, noscript, svg"):
                tag.decompose()
            detail_root = detail_soup.body or detail_soup
            raw_body = normalize_text(detail_root.get_text(separator="\n", strip=True))
            parsed_from = detail_url
    except requests.RequestException:
        raw_body = ""

    if len(raw_body) < 100:
        try:
            mobile_response = session.get(mobile_url, timeout=timeout)
            mobile_response.raise_for_status()
            mobile_soup = BeautifulSoup(mobile_response.text, "html.parser")
            for tag in mobile_soup.select(
                "script, style, iframe, noscript, svg, header, footer, nav, button"
            ):
                tag.decompose()
            mobile_root = (
                mobile_soup.select_one(".detail_area")
                or mobile_soup.select_one(".job_detail")
                or mobile_soup.select_one("main")
            )
            if mobile_root:
                raw_body = normalize_text(
                    mobile_root.get_text(separator="\n", strip=True)
                )
                parsed_from = mobile_url
        except requests.RequestException as exc:
            raise RuntimeError(f"사람인 공고 요청에 실패했습니다: {exc}") from exc

    if len(raw_body) < 100:
        raise ValueError(
            "사람인 공고 본문을 충분히 추출하지 못했습니다. "
            "공고가 종료되었거나 페이지 구조가 변경되었는지 확인하세요."
        )

    full_text = normalize_text(
        f"# [{company_name}] {position}\n\n{redact_personal_info(raw_body)}"
    )
    return {
        "source_type": "URL",
        "platform": "Saramin",
        "source_url": main_url,
        "parsed_from": parsed_from,
        "rec_idx": rec_idx,
        "company_name": company_name,
        "position": position,
        "text_length": len(full_text),
        "text": full_text,
    }


def extract_wanted_job_id(url: str) -> str:
    match = re.search(r"/wd/(\d+)", urlparse(url).path)
    if not match:
        raise ValueError("원티드 URL에서 공고 ID를 찾을 수 없습니다.")
    return match.group(1)


def _tag_titles(tags: list[Any]) -> list[str]:
    titles: list[str] = []
    for tag in tags or []:
        if isinstance(tag, str):
            title = tag
        elif isinstance(tag, dict):
            title = tag.get("title") or tag.get("name")
        else:
            title = None
        if title:
            titles.append(str(title).strip())
    return titles


def parse_wanted_job(url: str, timeout: int = 15) -> dict[str, Any]:
    """Parse a Wanted posting from its API and public page."""

    job_id = extract_wanted_job_id(url)
    api_url = f"https://www.wanted.co.kr/api/v4/jobs/{job_id}"
    web_url = f"https://www.wanted.co.kr/wd/{job_id}"

    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    try:
        api_response = session.get(api_url, timeout=timeout)
        api_response.raise_for_status()
        payload = api_response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"원티드 API 호출에 실패했습니다: {exc}") from exc

    job_data = payload.get("job", payload)
    detail = job_data.get("detail") or {}
    company = job_data.get("company") or {}
    company_name = company.get("name") or "회사명 미상"
    position = job_data.get("position") or "공고명 미상"
    skills = _tag_titles(job_data.get("skill_tags") or [])
    company_tags = _tag_titles(job_data.get("company_tags") or [])

    address_data = job_data.get("address") or {}
    if isinstance(address_data, dict):
        address = address_data.get("full_location") or address_data.get("location") or ""
    else:
        address = str(address_data)

    extra_guide = ""
    try:
        web_response = session.get(web_url, timeout=timeout)
        if web_response.ok:
            web_soup = BeautifulSoup(web_response.text, "html.parser")
            for tag in web_soup.select(
                "header, footer, nav, script, style, iframe, noscript, svg, button"
            ):
                tag.decompose()
            page_text = normalize_text(web_soup.get_text(separator="\n", strip=True))
            start_positions = [
                page_text.find(keyword)
                for keyword in ("채용 전형", "꼭 확인해 주세요", "서류 작성 팁")
                if page_text.find(keyword) >= 0
            ]
            if start_positions:
                sliced_text = page_text[min(start_positions) :]
                end_positions = [
                    sliced_text.find(keyword)
                    for keyword in ("이 포지션을 찾고 계셨나요", "비슷한 포지션", "원티드랩", "©")
                    if sliced_text.find(keyword) >= 0
                ]
                end_position = min(end_positions) if end_positions else len(sliced_text)
                extra_guide = sliced_text[:end_position].strip()
    except requests.RequestException:
        pass

    full_text = f"""# [{company_name}] {position}

## 회사 및 팀 소개
{detail.get('intro') or '정보 없음'}

## 주요 업무
{detail.get('main_tasks') or '정보 없음'}

## 자격 요건
{detail.get('requirements') or '정보 없음'}

## 우대 사항
{detail.get('preferred_points') or '정보 없음'}

## 혜택 및 복지
{detail.get('benefits') or '정보 없음'}

## 채용 전형 및 서류 작성 팁
{extra_guide or '별도 상세 안내 없음'}

## 기업 및 기술 태그
- 요구/관련 스킬: {', '.join(skills) if skills else '정보 없음'}
- 기업 복지/문화 태그: {', '.join(company_tags) if company_tags else '정보 없음'}
- 근무 지역: {address or '정보 없음'}
"""
    full_text = redact_personal_info(normalize_text(full_text))
    if len(full_text) < 100:
        raise ValueError("원티드 공고 본문을 충분히 추출하지 못했습니다.")

    return {
        "source_type": "URL",
        "platform": "Wanted",
        "source_url": web_url,
        "parsed_from": api_url,
        "job_id": job_id,
        "company_name": company_name,
        "position": position,
        "text_length": len(full_text),
        "text": full_text,
    }


def parse_job_posting(url: str, timeout: int = 15) -> dict[str, Any]:
    hostname = (urlparse(url).hostname or "").lower()
    if hostname.endswith("saramin.co.kr"):
        return parse_saramin_job(url, timeout=timeout)
    if hostname.endswith("wanted.co.kr"):
        return parse_wanted_job(url, timeout=timeout)
    raise ValueError("현재 지원하는 채용공고 URL은 사람인과 원티드입니다.")

