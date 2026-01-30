# Intelligence Upgrades Implementation Summary

This document summarizes all changes made to implement the intelligence features for the Newspaper PDF Intelligence system.

## Overview

Implemented database schema, models, services, and feature flags for the following intelligence upgrades:
1. Layout QA + Smart Fallback
2. Multi-Signal Ad Detection
3. Grouping Safeguards
4. Salience + Dive Mode
5. Entity Extraction (NER)
6. Topic Clustering + Trends
7. Thread/Timelines
8. Alerts v2
9. Hybrid Search (schema ready)
10. Quality Report (schema ready)

## Changes Summary

### 1. Database Migration (`b1c2d3e4f5a6_add_intelligence_features.py`)

**New Page columns (Layout QA):**
- `layout_coverage_ratio` - Fraction of page area covered by blocks
- `num_blocks_total`, `num_blocks_body`, `num_blocks_headline`
- `num_blocks_image`, `num_blocks_caption`, `num_blocks_ad`
- `column_count_estimate` - Heuristic column detection
- `headline_candidates_count` - Blocks that look like headlines
- `layout_quality_score` - Overall quality (0-1)
- `layout_fallback_used` - Whether fallback was triggered
- `layout_fallback_reason` - Reason for fallback

**New Item columns (Ad Detection + Salience):**
- `ad_candidate_score` - Ad likelihood (0-1)
- `ad_detection_reasons` - JSON list of reasons
- `salience_score` - Attention ranking (0-1)
- `salience_reasons` - JSON list of reasons
- `lede_text` - First 1-3 sentences (dive mode)
- `key_facts_json` - Who/what/where/when + numbers + dates
- `text_search_vector` - tsvector for PostgreSQL FTS

**New Tables:**
- `entities` - Normalized entity storage (PERSON, ORG, GPE, MONEY, DATE)
- `item_entities` - Junction table with confidence and mention count
- `topic_clusters` - Semantic topic clusters with centroids
- `item_topics` - Junction table for item-topic association
- `trend_metrics` - Daily trend data (rising topics, new entities)
- `threads` - Cross-edition story threads
- `thread_items` - Junction table with chronological ordering
- `alert_events` - Triggered alert events for users
- New indexes on `items.salience_score`, `items.item_type`, `items.created_at`
- Index on `extraction_runs(edition_id, status)`

### 2. Models Updates (`backend/app/models/__init__.py`)

**New Model Classes:**
- `Entity` - Named entity with normalization
- `ItemEntity` - Item-entity relationship with metadata
- `TopicCluster` - Topic cluster with centroid embedding
- `ItemTopic` - Item-topic relationship
- `TrendMetric` - Trend data point
- `Thread` - Cross-edition story thread
- `ThreadItem` - Thread-item with ordering
- `AlertEvent` - Alert trigger event

**Model Updates:**
- `Page` - Added 12 new layout QA columns
- `Item` - Added 7 new columns (ad, salience, lede, key_facts, search_vector)
- `SavedSearch` - Added `entity_ids_json`, `topic_ids_json`, `rules_json`, `alert_enabled`, `user_id`
- `User` - Added `alert_events` relationship
- `SavedSearch` - Added `alert_events` relationship
- `Item` - Added relationships to `ItemEntity`, `ItemTopic`, `ThreadItem`, `AlertEvent`

### 3. Settings Configuration (`backend/app/settings.py`)

**New Feature Flags:**
```python
# Layout QA
layout_qa_enabled = False
layout_fallback_enabled = True
layout_confidence_min = 0.4
layout_coverage_min = 0.1

# Ad Detection
ad_detection_enabled = True
ad_candidate_threshold = 0.6
ad_cta_keywords = ["Call", "WhatsApp", "Visit", "Offer", "Discount", ...]
ad_price_patterns = ["KSh", "KES", "/=", "%", "Sh", ...]

# Grouping Safeguards
grouping_max_pages_story = 5
grouping_allow_classified = False

# Salience
salience_enabled = True
salience_lede_sentences = 2
salience_front_page_boost = 0.2

# Entity Extraction
entity_extraction_enabled = False
entity_model_name = "stanfordnlp/stanza/en"
entity_confidence_threshold = 0.7

# Topic Clustering
topic_clustering_enabled = False
topic_clustering_days = 7
topic_model_clustering = "hdbscan"
topic_trends_enabled = False
topic_trends_days = 30

# Threading
threading_enabled = False
threading_similarity_threshold = 0.7
threading_max_days_apart = 7

# Alerts
alerts_enabled = False
alerts_webhook_enabled = False

# Hybrid Search
search_hybrid_enabled = False
search_fts_weight = 0.5
search_vector_weight = 0.5

# Quality Report
quality_report_enabled = True
```

### 4. New Services

**`layout_qa_service.py` (Full implementation):**
- `compute_layout_qa_metrics()` - Page-level quality assessment
  - Coverage ratio, block counts, column estimate, headline count
  - Overall `layout_quality_score` (0-1)
- `should_use_fallback()` - Fallback triggers
  - Low layout confidence
  - Low page coverage
  - Suspicious block distribution
  - No headline candidates
  - Low quality score

**`ad_detection_service.py` (Full implementation):**
- `compute_ad_candidate_score()` - Multi-signal scoring
  - Image area ratio (20%)
  - CTA keyword density (25%)
  - Contact density (20%)
  - Brand-like tokens (15%)
  - Price density (10%)
  - Length penalty (5%)
  - Layout AD boost (5%)
- `should_classify_as_ad()` - Threshold-based classification
  - Protects CLASSIFIED subtypes from mislabeling
  - Configurable threshold (`ad_candidate_threshold`)

**`salience_service.py` (Full implementation):**
- `compute_salience_score()` - Scan mode attention ranking
  - Headline importance (25%)
  - Image importance (20%)
  - Placement (top-of-page) (15%)
  - Length (optimal is best) (15%)
  - Section keywords (15%)
  - Front page boost (5%)
  - Type boost (5%)
- `extract_lede_text()` - First N sentences (dive mode)
- `extract_key_facts()` - Structured facts
  - who: people/organizations
  - what: story summary
  - where: locations
  - when: dates
  - numbers: key figures

**`entity_extraction_service.py` (Stub):**
- `extract_entities()` - Regex-based NER (PERSON, ORG, DATE)
  - Production should use spacy/stanza
  - Mention counts and confidence filtering

**`topic_clustering_service.py` (Stub):**
- `cluster_topics()` - Semantic topic discovery
  - Production should use HDBSCAN/k-means
- `compute_trends()` - Trend tracking

**`thread_service.py` (Stub):**
- `create_threads()` - Cross-edition threading
  - Production should use entity + topic + semantic similarity

**`alerts_service.py` (Stub):**
- `evaluate_alerts()` - Alert evaluation on new editions
  - Production should support entity/topic watchlists, numeric triggers, deadlines

### 5. Story Grouping Updates (`backend/app/services/story_grouping.py`)

**New Safeguards:**
- Type-based filtering: Only STORY items grouped by default
  - Configurable via `grouping_allow_classified`
- Max pages safeguard: Never create groups > `grouping_max_pages_story`
  - Unless explicit "continued on page X" + matching headline
- Added `_has_explicit_continuation()` helper
- Detailed logging for rejected/allowed large groups

## Validation Checklist

To validate the implementation:

### 1. Database Migration
```bash
cd backend
PYTHONPATH=$PWD alembic upgrade head
# Should reach: b1c2d3e4f5a6
```

### 2. Feature Flags
```bash
# In backend/.env
# Enable features progressively
SALIENCE_ENABLED=true
AD_DETECTION_ENABLED=true
GROUPING_ALLOW_CLASSIFIED=false
GROUPING_MAX_PAGES_STORY=5
```

### 3. Expected Behavior After Processing

**Layout QA:**
- Each Page has `layout_quality_score` (0-1)
- `layout_fallback_used` indicates if heuristic fallback was used
- Log shows: "Low layout confidence (0.31 < 0.4)" or similar

**Ad Detection:**
- Items with `ad_candidate_score >= 0.6` marked as AD
- `ad_detection_reasons` populated with explainable reasons
- Ads no longer 0% on realistic newspapers

**Grouping:**
- StoryGroup never > 5 pages (unless continued story)
- CLASSIFIED items not grouped (default)
- 28-page classified sections remain separate

**Salience:**
- Items have `salience_score` (0-1) for scan mode ranking
- `lede_text` populated with first 2 sentences
- `key_facts_json` contains who/what/where/when

**Entities:**
- Entity table populated with PERSON, ORG, DATE entities
- Item-Entity junction with mention counts
- (When `entity_extraction_enabled=True`)

## Rollout Plan

### Phase 1: Safe Features (Immediate)
1. **Enable Layout QA** - Set `layout_qa_enabled=True`
   - Provides visibility into layout quality
   - Doesn't change behavior yet (fallback default on)

2. **Enable Ad Detection** - Already enabled by default
   - Review ad detection accuracy
   - Adjust threshold if needed

3. **Enable Salience** - Already enabled by default
   - Review salience scores for scan mode
   - Verify lede extraction quality

### Phase 2: Safeguards (After 1 week)
1. **Enable Grouping Safeguards** - Already active by default
   - Verify mega-grouping prevented
   - Check logs for rejected groups

### Phase 3: Production-Ready Services (After validation)
1. **Entity Extraction** - Requires spacy/stanza installation
2. **Topic Clustering** - Requires HDBSCAN/k-means setup
3. **Threading** - Requires entity + topic + semantic integration
4. **Alerts** - Requires watchlist UI and webhook setup

### Phase 4: Search Upgrade (PostgreSQL only)
1. **Enable Hybrid Search** - Requires pgvector extension
2. **FTS Indexes** - Requires PostgreSQL tsvector

## Remaining Work

### Full Implementation Required:
- Entity extraction: Replace regex with spacy/stanza
- Topic clustering: Implement HDBSCAN/k-means with BGE embeddings
- Threading: Implement entity+topic+semantic similarity
- Alerts: Implement full rule evaluation (watchlists, triggers, deadlines)
- Search hybrid: Implement FTS + vector ranking (PostgreSQL only)

### API Endpoints to Add:
- `GET /api/editions/{id}/quality-report` - Quality metrics
- `GET /api/items/{id}/entities` - Item entities
- `GET /api/entities/{id}/timeline` - Entity timeline
- `GET /api/analytics/trends/topics` - Topic trends
- `GET /api/analytics/trends/entities` - Entity trends
- `GET /api/topics/{id}` - Topic details
- `GET /api/topics/{id}/items` - Topic items
- `GET /api/threads/` - List threads
- `GET /api/threads/{id}` - Thread details
- `GET /api/items/{id}/thread` - Item's thread
- `GET /api/alerts/events` - Alert events
- `POST /api/alerts/test-run` - Test alert rules

### Backfill Jobs to Implement:
- Entity extraction for last N editions
- Topic clustering for last 7-14 days
- Threading for last N days
- Trend computation jobs (daily/weekly)

### UI Components to Add:
- Quality report panel for admins
- Entity viewer for items
- Topic browser
- Thread/timeline viewer
- Alert configuration UI (watchlists, triggers)
- Hybrid search results page

## Commands

```bash
# View changes
git log --oneline --graph feature/intelligence-upgrades

# Switch to branch
git checkout feature/intelligence-upgrades

# Revert changes
git checkout main

# Run tests
make test-backend
```

## Contact

For questions or issues with this implementation, please open an issue on GitHub or contact the development team.
