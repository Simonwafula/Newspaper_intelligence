"""
Category classification service for automatic topic assignment.
Uses keyword matching with weighted scoring and confidence calculation.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Category, ItemCategory, Item

logger = logging.getLogger(__name__)


class CategoryClassifier:
    """Service for automatically categorizing items based on content analysis."""

    def __init__(self, db: Session):
        self.db = db
        self._categories_cache: Optional[List[Category]] = None

    def _get_categories(self) -> List[Category]:
        """Get all active categories, using cache for performance."""
        if self._categories_cache is None:
            self._categories_cache = (
                self.db.query(Category)
                .filter(Category.is_active == True)
                .order_by(Category.sort_order, Category.name)
                .all()
            )
        return self._categories_cache

    def _calculate_keyword_score(
        self, text: str, keywords: List[str], title_weight: float = 2.0, body_weight: float = 1.0
    ) -> float:
        """
        Calculate keyword match score for text.
        
        Args:
            text: Text to analyze (title + body content)
            keywords: List of keywords to match against
            title_weight: Weight multiplier for title matches
            body_weight: Weight multiplier for body text matches
            
        Returns:
            Confidence score between 0.0 and 100.0
        """
        if not keywords or not text:
            return 0.0

        # Split text into title and first line/paragraph (if possible)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        title = lines[0] if lines else ""
        body = '\n'.join(lines[1:]) if len(lines) > 1 else ""
        
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        title_lower = title.lower()
        body_lower = body.lower()

        total_score = 0.0
        matched_keywords = set()

        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Skip if keyword is empty or just whitespace
            if not keyword_lower.strip():
                continue

            # Count matches in title and body
            title_matches = len(re.findall(r'\b' + re.escape(keyword_lower) + r'\b', title_lower))
            body_matches = len(re.findall(r'\b' + re.escape(keyword_lower) + r'\b', body_lower))

            # Calculate weighted score
            keyword_score = (title_matches * title_weight + body_matches * body_weight)
            
            if keyword_score > 0:
                matched_keywords.add(keyword_lower)
                total_score += keyword_score

        # Normalize score: base score on keyword density and variety
        if not matched_keywords:
            return 0.0

        # Score factors:
        # 1. Number of unique keywords matched (up to 5)
        # 2. Total frequency of matches
        # 3. Text length (longer texts get proportionally lower scores)
        
        unique_bonus = min(len(matched_keywords) * 15, 75)  # Max 75 points for variety
        frequency_bonus = min(total_score * 5, 25)  # Max 25 points for frequency
        
        raw_score = unique_bonus + frequency_bonus
        
        # Apply text length normalization (penalize very short texts)
        text_length = len(text_lower)
        if text_length < 50:  # Very short text
            raw_score *= 0.7
        elif text_length < 200:  # Short text
            raw_score *= 0.85
        
        return min(raw_score, 100.0)

    def classify_item(self, item: Item, confidence_threshold: int = 30) -> List[ItemCategory]:
        """
        Classify an item into categories based on its content.
        
        Args:
            item: Item to classify
            confidence_threshold: Minimum confidence score (0-100) to assign category
            
        Returns:
            List of ItemCategory objects with confidence scores
        """
        categories = self._get_categories()
        if not categories:
            logger.warning("No active categories found for classification")
            return []

        # Combine title and text for analysis
        content = f"{item.title or ''} {item.text or ''}".strip()
        if not content:
            logger.debug(f"Item {item.id} has no content to classify")
            return []

        classifications = []

        for category in categories:
            keywords = category.keywords or []
            if not keywords:
                continue

            try:
                confidence = self._calculate_keyword_score(content, keywords)
                
                if confidence >= confidence_threshold:
                    classifications.append(
                        ItemCategory(
                            item_id=item.id,
                            category_id=category.id,
                            confidence=int(confidence),
                            source="auto"
                        )
                    )
                    logger.debug(
                        f"Item {item.id} matched category '{category.name}' "
                        f"with confidence {confidence:.1f}"
                    )
                    
            except Exception as e:
                logger.error(f"Error classifying item {item.id} for category '{category.name}': {e}")
                continue

        # Sort by confidence (highest first) and limit to top 3 categories
        classifications.sort(key=lambda x: x.confidence, reverse=True)
        return classifications[:3]

    def batch_classify_items(
        self, 
        items: List[Item], 
        confidence_threshold: int = 30,
        clear_existing: bool = True
    ) -> Dict[int, List[ItemCategory]]:
        """
        Classify multiple items in batch.
        
        Args:
            items: List of items to classify
            confidence_threshold: Minimum confidence score
            clear_existing: Whether to remove existing classifications first
            
        Returns:
            Dictionary mapping item_id to list of classifications
        """
        if not items:
            return {}

        results = {}
        
        for item in items:
            try:
                # Clear existing classifications if requested
                if clear_existing:
                    self.db.query(ItemCategory).filter(ItemCategory.item_id == item.id).delete()
                    self.db.commit()

                # Classify the item
                classifications = self.classify_item(item, confidence_threshold)
                
                if classifications:
                    self.db.add_all(classifications)
                    results[item.id] = classifications
                
                # Commit per item to avoid large transactions
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Error classifying item {item.id}: {e}")
                self.db.rollback()
                continue

        logger.info(f"Classified {len(results)} out of {len(items)} items")
        return results

    def get_category_suggestions(self, text: str, limit: int = 5) -> List[Tuple[Category, float]]:
        """
        Get category suggestions for arbitrary text.
        
        Args:
            text: Text to analyze
            limit: Maximum number of suggestions to return
            
        Returns:
            List of (category, confidence) tuples sorted by confidence
        """
        categories = self._get_categories()
        suggestions = []

        for category in categories:
            keywords = category.keywords or []
            if not keywords:
                continue

            confidence = self._calculate_keyword_score(text, keywords)
            if confidence > 0:
                suggestions.append((category, confidence))

        # Sort by confidence and limit
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:limit]

    def reclassify_all_items(self, confidence_threshold: int = 30) -> Dict[str, int]:
        """
        Re-run classification on all items in the database.
        
        Args:
            confidence_threshold: Minimum confidence score
            
        Returns:
            Statistics about the reclassification process
        """
        logger.info("Starting full database reclassification...")
        
        # Clear all existing auto-classifications
        deleted_count = (
            self.db.query(ItemCategory)
            .filter(ItemCategory.source == "auto")
            .delete()
        )
        self.db.commit()
        
        # Get all items
        items = self.db.query(Item).all()
        
        # Batch classify
        results = self.batch_classify_items(items, confidence_threshold, clear_existing=False)
        
        stats = {
            "total_items": len(items),
            "items_classified": len(results),
            "total_classifications": sum(len(classifications) for classifications in results.values()),
            "previous_classifications_removed": deleted_count
        }
        
        logger.info(f"Reclassification complete: {stats}")
        return stats

    def invalidate_cache(self):
        """Invalidate the categories cache when categories are modified."""
        self._categories_cache = None
        logger.debug("Category cache invalidated")