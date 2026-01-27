from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .schemas import Page, Story


def load_pages(path: str) -> List[Page]:
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and "pages" in data:
        items = data["pages"]
    else:
        items = data
    return [Page.from_dict(item) for item in items]


def save_stories(path: str, stories: Iterable[Story]) -> None:
    payload = [s.to_dict() for s in stories]
    Path(path).write_text(json.dumps(payload, indent=2))
