"""Resume document parsing services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .text import normalize_text, redact_personal_info


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(file_path: str | Path) -> Path:
    """Resolve a relative path from the project root."""

    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def parse_resume_pdf(file_path: str | Path) -> dict[str, Any]:
    """Extract and normalize text from a text-based resume PDF."""

    path = resolve_project_path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"PDF 파일만 지원합니다: {path.name}")

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise RuntimeError(f"PDF를 열지 못했습니다: {exc}") from exc

    if reader.is_encrypted:
        try:
            decrypt_result = reader.decrypt("")
        except Exception as exc:
            raise ValueError("암호화된 PDF는 파싱할 수 없습니다.") from exc
        if decrypt_result == 0:
            raise ValueError("암호화된 PDF는 파싱할 수 없습니다.")

    page_blocks: list[str] = []
    page_errors: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = normalize_text(page.extract_text() or "")
        except Exception as exc:
            page_errors.append(f"{page_number}페이지: {exc}")
            continue
        if page_text:
            page_blocks.append(f"[PAGE {page_number}]\n{page_text}")

    resume_text = redact_personal_info("\n\n".join(page_blocks))
    if len(resume_text.strip()) < 30:
        raise ValueError(
            "PDF에서 충분한 텍스트를 추출하지 못했습니다. "
            "스캔 PDF라면 OCR 처리가 필요합니다."
        )

    return {
        "source_type": "PDF",
        "file_path": str(path),
        "file_name": path.name,
        "page_count": len(reader.pages),
        "text_length": len(resume_text),
        "page_errors": page_errors,
        "text": resume_text,
    }

