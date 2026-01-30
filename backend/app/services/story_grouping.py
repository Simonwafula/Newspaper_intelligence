import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Item, StoryGroup, StoryGroupItem
from app.services.semantic_grouping_service import SemanticGroupingService
from app.settings import settings

logger = logging.getLogger(__name__)


CONTINUED_ON_RE = re.compile(r"continued\s+on\s+page\s+(\d+)", re.IGNORECASE)
CONTINUED_FROM_RE = re.compile(r"continued\s+from\s+page\s+(\d+)", re.IGNORECASE)
SEE_PAGE_RE = re.compile(r"(see|turn to)\s+page\s+(\d+)", re.IGNORECASE)
PAGE_CONTINUED_RE = re.compile(r"page\s+(\d+)\s+continued", re.IGNORECASE)
CONTINUED_RE = re.compile(r"continued\s+page\s+(\d+)", re.IGNORECASE)
FROM_PAGE_RE = re.compile(r"from\s+page\s+(\d+)", re.IGNORECASE)


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
    text = re.sub(r"(see|turn to)\s+page\s+\d+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"page\s+\d+\s+continued", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(continued|from)\s+page\s+\d+", "", text, flags=re.IGNORECASE)
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


def _similarity_score(
    a: Item,
    b: Item,
    semantic_service: Optional[SemanticGroupingService] = None,
    embeddings_cache: Optional[dict] = None,
) -> float:
    """
    Compute hybrid similarity score between two items.

    If semantic_service is provided and enabled, uses hybrid scoring:
    - 40% semantic similarity (BGE embeddings)
    - 30% token overlap (cosine)
    - 30% explicit references

    Otherwise falls back to token-based scoring only.
    """
    a_text = _normalize_text((a.title or "") + " " + (a.text or "")[:600])
    b_text = _normalize_text((b.title or "") + " " + (b.text or "")[:600])
    if not a_text or not b_text:
        return 0.0

    # Token-based similarity (existing)
    a_vec = _vectorize(a_text)
    b_vec = _vectorize(b_text)
    token_cosine = _cosine_similarity(a_vec, b_vec)
    title_sim = SequenceMatcher(None, _normalize_text(a.title), _normalize_text(b.title)).ratio()
    token_score = (token_cosine * 0.7) + (title_sim * 0.3)

    # If semantic grouping not available, use token-based only
    if not semantic_service or not semantic_service.is_available():
        return token_score

    # Semantic similarity (Phase 6)
    try:
        # Get or generate embeddings
        if embeddings_cache is not None:
            if a.id not in embeddings_cache:
                embeddings_cache[a.id] = semantic_service.generate_embedding(a.text or "")
            if b.id not in embeddings_cache:
                embeddings_cache[b.id] = semantic_service.generate_embedding(b.text or "")

            a_embedding = embeddings_cache[a.id]
            b_embedding = embeddings_cache[b.id]
        else:
            a_embedding = semantic_service.generate_embedding(a.text or "")
            b_embedding = semantic_service.generate_embedding(b.text or "")

        semantic_score = semantic_service.semantic_similarity(a_embedding, b_embedding)

        # Check for explicit references
        a_full_text = (a.text or "") + "\n" + (a.title or "")
        b_full_text = (b.text or "") + "\n" + (b.title or "")
        has_explicit_ref = (
            str(b.page_number) in _extract_page_refs(a_full_text) or
            str(a.page_number) in _extract_page_refs(b_full_text)
        )
        explicit_score = 1.0 if has_explicit_ref else 0.0

        # Hybrid score with configured weights
        hybrid_score = (
            semantic_service.semantic_weight * semantic_score +
            semantic_service.token_weight * token_score +
            semantic_service.explicit_ref_weight * explicit_score
        )

        logger.debug(
            f"Hybrid score for items {a.id}-{b.id}: "
            f"semantic={semantic_score:.3f}, token={token_score:.3f}, "
            f"explicit={explicit_score:.1f}, hybrid={hybrid_score:.3f}"
        )

        return hybrid_score

    except Exception as e:
        logger.warning(f"Semantic similarity failed: {e}, using token-based score")
        return token_score


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


def _extract_page_refs(text: str | None) -> list[int]:
    if not text:
        return []
    pages: list[int] = []
    for pattern in [CONTINUED_ON_RE, CONTINUED_FROM_RE, SEE_PAGE_RE, PAGE_CONTINUED_RE, CONTINUED_RE, FROM_PAGE_RE]:
        for match in pattern.finditer(text):
            for group in match.groups():
                if group and str(group).isdigit():
                    pages.append(int(group))
    return pages


def _has_explicit_continuation(items: list[Item]) -> bool:
    """
    Check if any item in the group has an explicit continuation reference.

    An explicit continuation is when:
    - Text contains "continued on page X" or similar
    - The referenced page is in the group's pages

    Args:
        items: List of Item objects in the group

    Returns:
        True if explicit continuation found, False otherwise
    """
    if not items:
        return False

    # Get all page numbers in this group
    group_pages = {item.page_number for item in items if item.page_number is not None}

    for item in items:
        text = (item.text or "") + "\n" + (item.title or "")
        page_refs = _extract_page_refs(text)

        # Check if any referenced page is in the group
        for ref_page in page_refs:
            if ref_page in group_pages:
                logger.debug(
                    f"Explicit continuation found: item {item.id} references page {ref_page}"
                )
                return True

    return False


def _named_entity_overlap(a: Item, b: Item) -> float | None:
    a_text = f"{a.title or ''} {a.text or ''}"
    b_text = f"{b.title or ''} {b.text or ''}"
    a_set = set(re.findall(r"\\b[A-Z][a-z]{2,}\\b", a_text))
    b_set = set(re.findall(r"\\b[A-Z][a-z]{2,}\\b", b_text))
    if not a_set or not b_set:
        return None
    return len(a_set & b_set) / len(a_set | b_set)


def build_story_groups(
    items: list[Item],
    semantic_service: Optional[SemanticGroupingService] = None,
) -> list[StoryGroupCluster]:
    """
    Build story groups using hybrid semantic + heuristic approach.

    Args:
        items: List of Item objects to group
        semantic_service: Optional SemanticGroupingService for semantic similarity

    Returns:
        List of StoryGroupCluster objects

    Safeguards (Intelligence upgrade):
        - Only groups STORY items by default (configurable via grouping_allow_classified)
        - Never creates groups > grouping_max_pages_story (unless explicit continuation)
        - Explicit "continued on page X" + matching headline allows larger groups
    """
    # Filter by item type based on settings
    if settings.grouping_allow_classified:
        # Include both STORY and CLASSIFIED items
        story_items = [item for item in items if item.item_type in ["STORY", "CLASSIFIED"]]
    else:
        # Only STORY items (default)
        story_items = [item for item in items if item.item_type == "STORY"]

    if not story_items:
        return []

    story_items.sort(key=lambda item: (item.page_number or 0, item.id))
    uf = _UnionFind([item.id for item in story_items])
    items_by_page: dict[int, list[Item]] = {}
    for item in story_items:
        items_by_page.setdefault(item.page_number, []).append(item)

    # Pre-generate embeddings if semantic grouping is enabled
    embeddings_cache = {}
    if semantic_service and semantic_service.is_available():
        logger.info(f"Generating embeddings for {len(story_items)} stories...")
        for item in story_items:
            if item.text:
                embeddings_cache[item.id] = semantic_service.generate_embedding(item.text)
        logger.info(f"Generated {len(embeddings_cache)} embeddings")

    for item in story_items:
        text = (item.text or "") + "\n" + (item.title or "")
        for page_ref in _extract_page_refs(text):
            candidate = _best_match(item, items_by_page.get(page_ref, []))
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
                entity_overlap = _named_entity_overlap(item, candidate)
                if entity_overlap is not None and entity_overlap < 0.2:
                    continue
                score = _similarity_score(
                    item,
                    candidate,
                    semantic_service=semantic_service,
                    embeddings_cache=embeddings_cache,
                )
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

        # Safeguard: Check if group exceeds max pages (Intelligence upgrade)
        max_pages = settings.grouping_max_pages_story
        if len(pages) > max_pages:
            # Check if this is an explicit continuation (allowed to exceed max)
            has_explicit_continuation = _has_explicit_continuation(group_items)

            if not has_explicit_continuation:
                logger.warning(
                    f"Grouping rejected: {len(pages)} pages exceeds max {max_pages} "
                    f"without explicit continuation. Group item_ids: {item_ids[:10]}..."
                )
                # Skip this group (items will remain ungrouped)
                continue
            else:
                logger.info(
                    f"Grouping allowed: {len(pages)} pages with explicit continuation. "
                    f"Group item_ids: {item_ids[:10]}..."
                )

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
    """
    Persist story groups for an edition using hybrid semantic + heuristic grouping.

    Args:
        db: Database session
        edition_id: Edition ID to process

    Returns:
        Number of story groups created
    """
    items = (
        db.query(Item)
        .filter(Item.edition_id == edition_id, Item.item_type == "STORY")
        .order_by(Item.page_number, Item.id)
        .all()
    )

    # Initialize semantic grouping service if enabled
    semantic_service = None
    if settings.semantic_grouping_enabled:
        try:
            semantic_service = SemanticGroupingService(
                model_name=settings.semantic_model_name,
                device=settings.semantic_model_device,
                semantic_weight=settings.semantic_weight,
                token_weight=settings.token_weight,
                explicit_ref_weight=settings.explicit_ref_weight,
            )
            if semantic_service.is_available():
                logger.info("Using semantic grouping with BGE embeddings")
            else:
                logger.info("Semantic grouping unavailable, using token-based only")
                semantic_service = None
        except Exception as e:
            logger.warning(f"Failed to initialize semantic grouping: {e}, using token-based")
            semantic_service = None

    groups = build_story_groups(items, semantic_service=semantic_service)

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

    # Cleanup semantic service resources
    if semantic_service:
        try:
            semantic_service.cleanup()
        except Exception as e:
            logger.warning(f"Failed to cleanup semantic service: {e}")

    return inserted
