import math
import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models import Item, StoryGroup, StoryGroupItem
from app.settings import settings


CONTINUED_ON_RE = re.compile(r"continued\s+on\s+page\s+(\d+)", re.IGNORECASE)
CONTINUED_FROM_RE = re.compile(r"continued\s+from\s+page\s+(\d+)", re.IGNORECASE)


@dataclass
class StoryGroupCluster:
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


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"continued\s+(from|on)\s+page\s+\d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> list[str]:
    return [token for token in text.split() if len(token) > 2]


def _vectorize(text: str) -> Counter:
    return Counter(_tokenize(text))


def _cosine_similarity(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    intersection = set(a) & set(b)
    numerator = sum(a[t] * b[t] for t in intersection)
    denom = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    if denom == 0:
        return 0.0
    return numerator / denom


def _similarity_score(a: Item, b: Item) -> float:
    a_text = _normalize_text((a.title or "") + " " + (a.text or "")[:600])
    b_text = _normalize_text((b.title or "") + " " + (b.text or "")[:600])
    if not a_text or not b_text:
        return 0.0

    a_vec = _vectorize(a_text)
    b_vec = _vectorize(b_text)
    cosine = _cosine_similarity(a_vec, b_vec)
    title_sim = SequenceMatcher(None, _normalize_text(a.title), _normalize_text(b.title)).ratio()
    return (cosine * 0.7) + (title_sim * 0.3)


def _best_match(target: Item, candidates: list[Item]) -> Item | None:
    target_title = _normalize_text(target.title or target.text or "")
    if not candidates:
        return None

    best_item = None
    best_score = 0.0
    for candidate in candidates:
        cand_title = _normalize_text(candidate.title or candidate.text or "")
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


def build_story_groups(items: list[Item]) -> list[StoryGroupCluster]:
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

    page_window = settings.story_grouping_page_window
    min_tokens = settings.story_grouping_min_shared_tokens
    similarity_threshold = settings.story_grouping_similarity_threshold

    for item in story_items:
        if item.page_number is None:
            continue
        for neighbor_page in range(item.page_number - page_window, item.page_number + page_window + 1):
            if neighbor_page == item.page_number:
                continue
            for candidate in items_by_page.get(neighbor_page, []):
                if candidate.id == item.id:
                    continue
                a_text = _normalize_text((item.title or "") + " " + (item.text or "")[:600])
                b_text = _normalize_text((candidate.title or "") + " " + (candidate.text or "")[:600])
                shared = set(_tokenize(a_text)) & set(_tokenize(b_text))
                if len(shared) < min_tokens:
                    continue
                score = _similarity_score(item, candidate)
                if score >= similarity_threshold:
                    uf.union(item.id, candidate.id)

    groups: dict[int, list[Item]] = {}
    for item in story_items:
        root = uf.find(item.id)
        groups.setdefault(root, []).append(item)

    story_groups: list[StoryGroupCluster] = []
    for root, group_items in groups.items():
        group_items.sort(key=lambda item: (item.page_number or 0, item.id))
        pages = sorted({item.page_number for item in group_items if item.page_number is not None})
        item_ids = [item.id for item in group_items]
        title = group_items[0].title or (group_items[0].text or "").split("\n")[0] or None
        story_groups.append(
            StoryGroupCluster(
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


def persist_story_groups(db: Session, edition_id: int) -> int:
    items = (
        db.query(Item)
        .filter(Item.edition_id == edition_id, Item.item_type == "STORY")
        .order_by(Item.page_number, Item.id)
        .all()
    )
    groups = build_story_groups(items)

    db.query(StoryGroupItem).filter(
        StoryGroupItem.story_group_id.in_(
            db.query(StoryGroup.id).filter(StoryGroup.edition_id == edition_id)
        )
    ).delete(synchronize_session=False)
    db.query(StoryGroup).filter(StoryGroup.edition_id == edition_id).delete(synchronize_session=False)
    db.commit()

    inserted = 0
    for group in groups:
        story_group = StoryGroup(
            edition_id=edition_id,
            title=group.title,
            pages_json=group.pages,
            excerpt=group.excerpt,
            full_text=group.full_text,
        )
        db.add(story_group)
        db.flush()

        for index, item_id in enumerate(group.item_ids):
            db.add(StoryGroupItem(
                story_group_id=story_group.id,
                item_id=item_id,
                order_index=index,
            ))

        inserted += 1

    db.commit()
    return inserted
