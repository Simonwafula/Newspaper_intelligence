import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.models import Item


CONTINUED_ON_RE = re.compile(r"continued\s+on\s+page\s+(\d+)", re.IGNORECASE)
CONTINUED_FROM_RE = re.compile(r"continued\s+from\s+page\s+(\d+)", re.IGNORECASE)


@dataclass
class StoryGroup:
    group_id: int
    edition_id: int
    title: str | None
    pages: list[int]
    item_ids: list[int]
    items: list[Item]

    @property
    def full_text(self) -> str | None:
        if not self.items:
            return None
        parts = []
        for item in self.items:
            if item.text:
                parts.append(item.text)
        if not parts:
            return None
        return "\n\n".join(parts)

    @property
    def excerpt(self) -> str | None:
        text = self.full_text or ""
        if not text:
            return None
        return text[:200] + ("..." if len(text) > 200 else "")


class _UnionFind:
    def __init__(self, items: list[int]):
        self.parent = {item_id: item_id for item_id in items}

    def find(self, item_id: int) -> int:
        root = self.parent[item_id]
        if root != item_id:
            root = self.find(root)
            self.parent[item_id] = root
        return root

    def union(self, a: int, b: int) -> None:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a != root_b:
            self.parent[root_b] = root_a


def _normalize_title(text: str | None) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"continued\s+(from|on)\s+page\s+\d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _best_match(target: Item, candidates: list[Item]) -> Item | None:
    target_title = _normalize_title(target.title or target.text or "")
    if not candidates:
        return None

    best_item = None
    best_score = 0.0
    for candidate in candidates:
        cand_title = _normalize_title(candidate.title or candidate.text or "")
        if not cand_title:
            continue
        score = SequenceMatcher(None, target_title, cand_title).ratio() if target_title else 0.0
        if score > best_score:
            best_score = score
            best_item = candidate

    if best_item and best_score >= 0.3:
        return best_item
    if len(candidates) == 1:
        return candidates[0]
    return None


def build_story_groups(items: list[Item]) -> list[StoryGroup]:
    story_items = [item for item in items if item.item_type == "STORY"]
    if not story_items:
        return []

    story_items.sort(key=lambda item: (item.page_number or 0, item.id))
    uf = _UnionFind([item.id for item in story_items])
    items_by_page: dict[int, list[Item]] = {}
    for item in story_items:
        items_by_page.setdefault(item.page_number, []).append(item)

    for item in story_items:
        text = (item.text or "") + "\n" + (item.title or "")
        on_match = CONTINUED_ON_RE.search(text)
        if on_match:
            target_page = int(on_match.group(1))
            candidate = _best_match(item, items_by_page.get(target_page, []))
            if candidate:
                uf.union(item.id, candidate.id)

        from_match = CONTINUED_FROM_RE.search(text)
        if from_match:
            source_page = int(from_match.group(1))
            candidate = _best_match(item, items_by_page.get(source_page, []))
            if candidate:
                uf.union(item.id, candidate.id)

    groups: dict[int, list[Item]] = {}
    for item in story_items:
        root = uf.find(item.id)
        groups.setdefault(root, []).append(item)

    story_groups: list[StoryGroup] = []
    for root, group_items in groups.items():
        group_items.sort(key=lambda item: (item.page_number or 0, item.id))
        pages = sorted({item.page_number for item in group_items if item.page_number is not None})
        item_ids = [item.id for item in group_items]
        title = group_items[0].title or (group_items[0].text or "").split("\n")[0] or None
        story_groups.append(
            StoryGroup(
                group_id=min(item_ids),
                edition_id=group_items[0].edition_id,
                title=title,
                pages=pages,
                item_ids=item_ids,
                items=group_items,
            )
        )

    story_groups.sort(key=lambda group: (group.pages[0] if group.pages else 0, group.group_id))
    return story_groups
