"""
Semantic Grouping Service - Phase 6 Implementation

This service uses BGE (BAAI General Embedding) models to perform semantic
story grouping across pages using embeddings and cosine similarity.

Advantages over token-based grouping:
- Understands semantic meaning, not just word overlap
- Detects paraphrasing and continuations
- Better handles rewording between pages
- Works across languages (with multilingual BGE)

Hybrid approach combines:
- Semantic similarity (40%): BGE embeddings + cosine similarity
- Token overlap (30%): Existing TF-IDF approach
- Explicit references (30%): "Continued on page X" patterns
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
SENTENCE_TRANSFORMERS_AVAILABLE = False
SentenceTransformer = None
np = None

try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
    import numpy as np
    SentenceTransformer = _SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"sentence-transformers not available: {e}. Install with: pip install sentence-transformers")


class SemanticGroupingService:
    """
    Service for semantic story grouping using embeddings.

    Uses BGE (BAAI General Embedding) models to understand story continuations
    across pages through semantic similarity.

    Usage:
        service = SemanticGroupingService(model_name="BAAI/bge-small-en-v1.5")
        groups = service.group_stories_enhanced(items_list)
        for group in groups:
            print(f"Group has {len(group.item_ids)} items across pages {group.pages}")
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        device: str = "cpu",
        semantic_weight: float = 0.4,
        token_weight: float = 0.3,
        explicit_ref_weight: float = 0.3,
    ):
        """
        Initialize the semantic grouping service.

        Args:
            model_name: BGE model name (bge-small, bge-base, bge-large)
            device: Device for model inference ('cpu' or 'cuda')
            semantic_weight: Weight for semantic similarity (default: 0.4)
            token_weight: Weight for token overlap (default: 0.3)
            explicit_ref_weight: Weight for explicit references (default: 0.3)
        """
        self.model_name = model_name
        self.device = device
        self.semantic_weight = semantic_weight
        self.token_weight = token_weight
        self.explicit_ref_weight = explicit_ref_weight
        self._model: Optional["SentenceTransformer"] = None

        logger.info(
            f"Initializing SemanticGroupingService with model={model_name}, "
            f"device={device}, weights=(s:{semantic_weight}, t:{token_weight}, e:{explicit_ref_weight})"
        )

        # Initialize embedding model if available
        if SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer is not None:
            try:
                self._model = SentenceTransformer(model_name, device=device)
                logger.info(f"Loaded BGE model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load BGE model: {e}, semantic grouping unavailable")
                self._model = None
        else:
            logger.warning("sentence-transformers not available, using token-based grouping only")

    def is_available(self) -> bool:
        """Check if semantic grouping is available."""
        return self._model is not None

    def generate_embedding(self, text: str) -> Optional["np.ndarray"]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed (typically headline + first 2-3 paragraphs)

        Returns:
            Embedding vector as numpy array (384-dim for bge-small), or None if unavailable
        """
        if not self.is_available() or not text.strip():
            return None

        try:
            # Generate normalized embedding
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return None

    def semantic_similarity(self, embedding1: Optional["np.ndarray"], embedding2: Optional["np.ndarray"]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector (or None)
            embedding2: Second embedding vector (or None)

        Returns:
            Similarity score (0-1, higher is more similar), or 0.0 if either embedding is None
        """
        if embedding1 is None or embedding2 is None or np is None:
            return 0.0

        try:
            # Embeddings are already normalized by BGE
            similarity = float(np.dot(embedding1, embedding2))
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
        except Exception as e:
            logger.warning(f"Failed to compute similarity: {e}")
            return 0.0

    def group_stories_enhanced(
        self,
        items: List[dict],
        similarity_threshold: float = 0.65,
        page_window: int = 2,
    ) -> List[List[int]]:
        """
        Group stories using hybrid semantic + heuristic approach.

        Args:
            items: List of item dictionaries with 'id', 'text', 'page_number' keys
            similarity_threshold: Minimum hybrid score to group items (default: 0.65)
            page_window: Max page distance to consider for grouping (default: 2)

        Returns:
            List of groups, where each group is a list of item IDs

        Note: This method provides semantic similarity scores. The actual story
        grouping logic should integrate this into the existing story_grouping.py
        service to combine with token-based and explicit reference detection.
        """
        if not items:
            return []

        # Generate embeddings for all items (if available)
        item_embeddings = {}
        if self.is_available():
            for item in items:
                text = item.get("text", "")
                if text:
                    # Generate embedding for the start of the story
                    start_text = self._prepare_text_for_embedding(text, mode="start")
                    embedding = self.generate_embedding(start_text)
                    if embedding is not None:
                        item_embeddings[item["id"]] = embedding

        # Build similarity graph
        groups = []
        used_items = set()

        # Sort items by page number
        sorted_items = sorted(items, key=lambda x: x["page_number"])

        for i, item1 in enumerate(sorted_items):
            if item1["id"] in used_items:
                continue

            # Start a new group
            group = [item1["id"]]
            used_items.add(item1["id"])

            # Look for continuations in subsequent pages
            for item2 in sorted_items[i + 1 :]:
                if item2["id"] in used_items:
                    continue

                # Check page window
                page_diff = item2["page_number"] - item1["page_number"]
                if page_diff > page_window:
                    break

                # Compute hybrid similarity
                semantic_score = 0.0
                if item1["id"] in item_embeddings and item2["id"] in item_embeddings:
                    semantic_score = self.semantic_similarity(
                        item_embeddings[item1["id"]], item_embeddings[item2["id"]]
                    )

                # For full implementation, would also compute:
                # - token_score = _calculate_token_overlap(item1["text"], item2["text"])
                # - explicit_score = _detect_explicit_reference(item2["text"], item1["page_number"])
                # - hybrid_score = self._calculate_hybrid_score(semantic_score, token_score, explicit_score)

                # For now, use semantic score as threshold
                if semantic_score >= similarity_threshold:
                    group.append(item2["id"])
                    used_items.add(item2["id"])

            if len(group) > 1:
                groups.append(group)

        return groups

    def _calculate_hybrid_score(
        self,
        semantic_sim: float,
        token_overlap: float,
        explicit_ref: bool,
        semantic_weight: float = 0.4,
        token_weight: float = 0.3,
        explicit_weight: float = 0.3,
    ) -> float:
        """
        Calculate hybrid grouping score.

        Args:
            semantic_sim: Semantic similarity (0-1)
            token_overlap: Token overlap score (0-1)
            explicit_ref: Whether explicit page reference found
            semantic_weight: Weight for semantic component
            token_weight: Weight for token component
            explicit_weight: Weight for explicit reference

        Returns:
            Combined score (0-1)

        Implementation:
            explicit_score = 1.0 if explicit_ref else 0.0
            return (
                semantic_weight * semantic_sim +
                token_weight * token_overlap +
                explicit_weight * explicit_score
            )
        """
        explicit_score = 1.0 if explicit_ref else 0.0
        return (
            semantic_weight * semantic_sim
            + token_weight * token_overlap
            + explicit_weight * explicit_score
        )

    def _prepare_text_for_embedding(self, text: str, mode: str = "start") -> str:
        """
        Prepare text for embedding generation.

        Args:
            text: Full item text
            mode: 'start' (first N words) or 'end' (last N words)

        Returns:
            Truncated text suitable for embedding

        Implementation Notes:
            - For 'start': Take first 200 words
            - For 'end': Take last 200 words
            - This helps match story endings with continuations
        """
        words = text.split()
        if mode == "start":
            return " ".join(words[:200])
        else:  # mode == "end"
            return " ".join(words[-200:]) if len(words) > 200 else text

    def cleanup(self):
        """Release model resources."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Semantic grouping model cleaned up")
