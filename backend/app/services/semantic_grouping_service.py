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

import logging
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


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

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu"):
        """
        Initialize the semantic grouping service.

        Args:
            model_name: BGE model name (bge-small, bge-base, bge-large)
            device: Device for model inference ('cpu' or 'cuda')
        """
        self.model_name = model_name
        self.device = device
        self._model = None

        logger.info(f"Initializing SemanticGroupingService with model={model_name}, device={device}")

        # TODO Phase 6: Initialize embedding model
        # try:
        #     from sentence_transformers import SentenceTransformer
        #     self._model = SentenceTransformer(model_name, device=device)
        #     logger.info(f"Loaded BGE model: {model_name}")
        # except Exception as e:
        #     logger.warning(f"Failed to load BGE model: {e}, semantic grouping unavailable")

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed (typically headline + first 2-3 paragraphs)

        Returns:
            Embedding vector as numpy array (384-dim for bge-small)

        Implementation Notes (Phase 6):
            1. Truncate text to model's max length (usually 512 tokens)
            2. For story grouping, use:
               - Headline + first 200 words for start of story
               - Last 200 words for end of story (to match continuations)
            3. Call model.encode(text, normalize_embeddings=True)
            4. Return normalized embedding
        """
        if self._model is None:
            raise RuntimeError("BGE model not loaded. Check initialization.")

        raise NotImplementedError(
            "Phase 6: Implement embedding generation using sentence-transformers. "
            "See plan file for detailed implementation guidance."
        )

    def semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1, higher is more similar)

        Implementation:
            return np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )

            Or if embeddings are already normalized:
            return float(np.dot(embedding1, embedding2))
        """
        # If already normalized (which BGE does by default)
        return float(np.dot(embedding1, embedding2))

    def group_stories_enhanced(self, db, edition_id: int) -> int:
        """
        Group stories using hybrid semantic + heuristic approach.

        Args:
            db: Database session
            edition_id: Edition ID to process

        Returns:
            Number of story groups created

        Implementation Notes (Phase 6):
            1. Load all STORY items for edition
            2. Generate embeddings for each item:
               - Start embedding: headline + first 200 words
               - End embedding: last 200 words
            3. For each potential continuation:
               - Calculate semantic similarity (end of story A → start of story B)
               - Calculate token overlap (from existing story_grouping.py)
               - Check explicit references ("Continued on page X")
            4. Compute hybrid score:
               score = 0.4 * semantic + 0.3 * token + 0.3 * explicit
            5. Group items with score > threshold
            6. Create StoryGroup records
            7. Store embeddings in Item.embedding_json for future queries

        Reuse existing logic from:
            backend/app/services/story_grouping.py:
            - _find_explicit_page_references()
            - _calculate_token_overlap()
            - persist_story_groups()
        """
        raise NotImplementedError(
            "Phase 6: Implement hybrid story grouping. "
            "Enhance existing story_grouping.py with semantic similarity. "
            "See plan file for detailed implementation guidance."
        )

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
