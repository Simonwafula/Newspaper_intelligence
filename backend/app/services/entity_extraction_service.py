"""
Entity Extraction Service - Named Entity Recognition (NER).

This service provides:
- Entity extraction for STORY items (PERSON, ORG, GPE, MONEY, DATE)
- Normalized entity storage with mention counts
- Confidence-based filtering

Note: This is a stub implementation using regex.
Production should use spacy/stanza for better NER.
"""

import logging
import re
from typing import Any, Optional

from app.settings import settings

logger = logging.getLogger(__name__)


# Simple regex patterns (production: use spacy/stanza)
PERSON_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
ORG_RE = re.compile(r"\b(?:Inc|Corp|Ltd|Co|PLC|Company|Group)\b")
DATE_RE = re.compile(r"\b\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b", re.IGNORECASE)


class EntityExtractionService:
    """Service for entity extraction and normalization."""

    def __init__(self):
        self.enabled = settings.entity_extraction_enabled
        self.confidence_threshold = settings.entity_confidence_threshold

    def extract_entities(
        self,
        text: str,
        item_type: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Extract entities from text with types and confidence.

        Args:
            text: Full text content
            item_type: Item type (STORY, AD, CLASSIFIED)

        Returns:
            Dictionary with extracted entities and metadata
        """
        if not self.enabled or not text or not text.strip():
            return {'entities': [], 'metadata': {}}

        entities = []

        # Extract persons
        for match in PERSON_RE.finditer(text):
            name = match.group(1)
            entities.append({
                'name': name,
                'name_normalized': name.upper().strip(),
                'type': 'PERSON',
                'confidence': 0.6,  # Moderate confidence for regex-based
            })

        # Extract organizations (simple patterns)
        for match in ORG_RE.finditer(text):
            org_type = match.group(0)
            entities.append({
                'name': org_type,
                'name_normalized': org_type.upper(),
                'type': 'ORG',
                'confidence': 0.4,
            })

        # Extract dates
        for match in DATE_RE.finditer(text):
            date_str = match.group(0)
            entities.append({
                'name': date_str,
                'name_normalized': date_str.upper().strip(),
                'type': 'DATE',
                'confidence': 0.7,
            })

        # Count mentions
        entity_mentions = {}
        for entity in entities:
            key = (entity['name_normalized'], entity['type'])
            entity_mentions[key] = entity_mentions.get(key, 0) + 1

        # Add mention counts
        for entity in entities:
            key = (entity['name_normalized'], entity['type'])
            entity['mention_count'] = entity_mentions[key]

        # Filter by confidence
        entities = [e for e in entities if e['confidence'] >= self.confidence_threshold]

        # Deduplicate
        seen = set()
        deduped = []
        for entity in entities:
            key = (entity['name_normalized'], entity['type'])
            if key not in seen:
                seen.add(key)
                deduped.append(entity)

        # Sort by mention count
        deduped.sort(key=lambda e: e['mention_count'], reverse=True)

        return {
            'entities': deduped,
            'metadata': {
                'total_entities': len(deduped),
                'total_mentions': sum(e['mention_count'] for e in deduped),
            }
        }


def create_entity_extraction_service() -> EntityExtractionService:
    """Factory function to create EntityExtractionService instance."""
    return EntityExtractionService()
