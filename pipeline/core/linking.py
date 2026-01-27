from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .continuation import detect_section_slug, extract_all_continuations
from .ordering import BODY_TYPES, TOP_TYPES
from .schemas import Block, Page, Story


HEADLINE_TYPES = {"headline", "title"}
BYLINE_TYPES = {"byline"}
SECTION_TYPES = {"section", "section_label"}
AD_TYPES = {"ad", "advert", "advertisement"}


@dataclass
class StorySeed:
    id: str
    page: int
    headline: str
    section: Optional[str]
    byline: Optional[str]
    blocks: List[Block]

    @property
    def text(self) -> str:
        parts = [b.text.strip() for b in self.blocks if b.text.strip()]
        return "\n".join(parts).strip()


class UnionFind:
    def __init__(self):
        self.parent: Dict[str, str] = {}

    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def is_text_block(block: Block) -> bool:
    if block.type in AD_TYPES:
        return False
    if block.type in {"image", "photo", "graphic"}:
        return False
    return True


def build_story_seeds(pages: Iterable[Page]) -> List[StorySeed]:
    seeds: List[StorySeed] = []
    for page in pages:
        section = section_for_page(page.blocks)
        headlines = [b for b in page.blocks if b.type in HEADLINE_TYPES]
        for h in headlines:
            blocks = collect_story_blocks(page.blocks, h)
            byline = first_text_of_type(blocks, BYLINE_TYPES)
            seed = StorySeed(
                id=f"p{page.number}_{h.id}",
                page=page.number,
                headline=h.text.strip(),
                section=section,
                byline=byline,
                blocks=blocks,
            )
            seeds.append(seed)
    return seeds


def collect_story_blocks(blocks: List[Block], headline: Block) -> List[Block]:
    col = headline.column
    ordered = [b for b in blocks if b.column == col] if col is not None else list(blocks)
    ordered.sort(key=lambda b: b.bbox.y1)

    collected: List[Block] = []
    found = False
    for b in ordered:
        if b.id == headline.id:
            found = True
            collected.append(b)
            continue
        if not found:
            continue
        if b.type in HEADLINE_TYPES and b.bbox.y1 > headline.bbox.y1:
            break
        if not is_text_block(b):
            continue
        if b.type in SECTION_TYPES:
            continue
        collected.append(b)
    return collected


def first_text_of_type(blocks: List[Block], types: Iterable[str]) -> Optional[str]:
    type_set = set(types)
    for b in blocks:
        if b.type in type_set and b.text.strip():
            return b.text.strip()
    return None


def section_for_page(blocks: List[Block]) -> Optional[str]:
    section_blocks = [b for b in blocks if b.type in SECTION_TYPES]
    if not section_blocks:
        return detect_section_slug([b.text for b in blocks])
    section_blocks.sort(key=lambda b: b.bbox.y1)
    return section_blocks[0].text.strip() or detect_section_slug([b.text for b in blocks])


def rule_based_links(seeds: List[StorySeed]) -> List[Tuple[str, str]]:
    links: List[Tuple[str, str]] = []
    by_page: Dict[int, List[StorySeed]] = {}
    for seed in seeds:
        by_page.setdefault(seed.page, []).append(seed)

    for seed in seeds:
        pages = extract_all_continuations(seed.text)
        if not pages:
            continue
        for target_page in pages:
            candidates = by_page.get(target_page, [])
            if not candidates:
                continue
            best = pick_best_candidate(seed, candidates)
            if best:
                links.append((seed.id, best.id))
    return links


def pick_best_candidate(seed: StorySeed, candidates: List[StorySeed]) -> Optional[StorySeed]:
    filtered = [c for c in candidates if not seed.section or not c.section or seed.section == c.section]
    if not filtered:
        filtered = candidates
    seed_tokens = token_set(seed.headline)
    best = None
    best_score = 0.0
    for cand in filtered:
        score = jaccard(seed_tokens, token_set(cand.headline))
        if score > best_score:
            best_score = score
            best = cand
    return best


def embedding_links(seeds: List[StorySeed], min_similarity: float = 0.32) -> List[Tuple[str, str]]:
    embeddings = compute_embeddings(seeds)
    if not embeddings:
        return []

    links: List[Tuple[str, str]] = []
    by_page: Dict[int, List[StorySeed]] = {}
    for seed in seeds:
        by_page.setdefault(seed.page, []).append(seed)

    for seed in seeds:
        seed_emb = embeddings.get(seed.id)
        if seed_emb is None:
            continue
        linked = False
        for page_num, candidates in by_page.items():
            if page_num <= seed.page:
                continue
            for cand in candidates:
                if seed.section and cand.section and seed.section != cand.section:
                    continue
                cand_emb = embeddings.get(cand.id)
                if cand_emb is None:
                    continue
                sim = cosine_similarity(seed_emb, cand_emb)
                if sim < min_similarity:
                    continue
                if named_entity_overlap(seed.text, cand.text) < 0.2:
                    continue
                links.append((seed.id, cand.id))
                linked = True
                break
            if linked:
                break
    return links


def compute_embeddings(seeds: List[StorySeed]) -> Dict[str, List[float]]:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return {}

    model = SentenceTransformer("BAAI/bge-base-en-v1.5")
    texts = [signature_text(seed) for seed in seeds]
    ids = [seed.id for seed in seeds]
    vecs = model.encode(texts, normalize_embeddings=True)
    return {seed_id: vec.tolist() for seed_id, vec in zip(ids, vecs)}


def signature_text(seed: StorySeed) -> str:
    parts = []
    if seed.headline:
        parts.append(seed.headline)
    body = seed.text
    if body:
        parts.append(" ".join(body.split()[:120]))
    return "\n".join(parts).strip()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def token_set(text: str) -> set:
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    return set(tokens)


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def named_entity_overlap(a: str, b: str) -> float:
    a_set = set(re.findall(r"\b[A-Z][a-z]{2,}\b", a or ""))
    b_set = set(re.findall(r"\b[A-Z][a-z]{2,}\b", b or ""))
    if not a_set and not b_set:
        return 1.0
    if not a_set or not b_set:
        return 0.0
    return len(a_set & b_set) / len(a_set | b_set)


def merge_stories(seeds: List[StorySeed], links: List[Tuple[str, str]]) -> List[Story]:
    uf = UnionFind()
    for a, b in links:
        uf.union(a, b)

    groups: Dict[str, List[StorySeed]] = {}
    for seed in seeds:
        root = uf.find(seed.id)
        groups.setdefault(root, []).append(seed)

    stories: List[Story] = []
    for root, group in groups.items():
        group.sort(key=lambda s: s.page)
        headline = group[0].headline
        section = group[0].section
        byline = group[0].byline
        pages = [s.page for s in group]
        blocks: List[Block] = []
        for s in group:
            blocks.extend(s.blocks)
        text = "\n\n".join(s.text for s in group if s.text.strip())
        block_ids = [b.id for b in blocks]
        stories.append(
            Story(
                id=root,
                headline=headline,
                section=section,
                byline=byline,
                text=text,
                pages=pages,
                block_ids=block_ids,
                blocks=blocks,
                meta={},
            )
        )
    return stories
