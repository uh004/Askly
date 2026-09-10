"""Text cleanup helpers shared by document and job-posting parsers."""

from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph boundaries."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ").replace("\u200b", "")

    cleaned_lines: list[str] = []
    previous_blank = False
    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            cleaned_lines.append(line)
            previous_blank = False
        elif cleaned_lines and not previous_blank:
            cleaned_lines.append("")
            previous_blank = True

    return "\n".join(cleaned_lines).strip()


def redact_personal_info(text: str) -> str:
    """Mask email addresses and Korean mobile-phone numbers."""

    text = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "[이메일 제거]",
        text,
    )
    return re.sub(
        r"(?<!\d)01[016789][- .]?\d{3,4}[- .]?\d{4}(?!\d)",
        "[전화번호 제거]",
        text,
    )

