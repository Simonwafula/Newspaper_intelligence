from __future__ import annotations

import re
from typing import List, Optional, Tuple

CONTINUATION_PATTERNS = [
    re.compile(r"continued\s+(on|from)\s+page\s+(\d+)", re.IGNORECASE),
    re.compile(r"\(see\s+page\s+(\d+)\)", re.IGNORECASE),
    re.compile(r"see\s+page\s+(\d+)", re.IGNORECASE),
    re.compile(r"page\s+(\d+)\s+continued", re.IGNORECASE),
]


def extract_continuation_page(text: str) -> Optional[int]:
    text = text or ""
    for pattern in CONTINUATION_PATTERNS:
        match = pattern.search(text)
        if match:
            for group in match.groups():
                if group and group.isdigit():
                    return int(group)
    return None


def extract_all_continuations(text: str) -> List[int]:
    pages: List[int] = []
    text = text or ""
    for pattern in CONTINUATION_PATTERNS:
        for match in pattern.finditer(text):
            for group in match.groups():
                if group and group.isdigit():
                    pages.append(int(group))
    return pages


def detect_section_slug(block_texts: List[str]) -> Optional[str]:
    for text in block_texts:
        cleaned = " ".join(text.split()).strip()
        if not cleaned:
            continue
        if cleaned.isupper() and 3 <= len(cleaned) <= 30:
            return cleaned
    return None
