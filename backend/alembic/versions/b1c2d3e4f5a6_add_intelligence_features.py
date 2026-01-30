"""add intelligence features: layout QA, ad detection, salience, entities, topics, threads, alerts, search

Revision ID: b1c2d3e4f5a6
Revises: 4a5b6c7d8e9f
Create Date: 2026-01-30 10:00:00.000000

This migration adds all intelligence features:
- Layout QA metrics to Page
- Ad detection and salience scoring to Item
- Entity tables and extraction
- Topic clustering and trends
- Thread/timeline support
- Alerts v2 with watchlists and triggers
- Full-text search with hybrid retrieval
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "4a5b6c7d8e9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== Page: Layout QA Metrics ====================
    op.add_column('pages', sa.Column('layout_coverage_ratio', sa.Float(), nullable=True))
    op.add_column('pages', sa.Column('num_blocks_total', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('num_blocks_body', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('num_blocks_headline', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('num_blocks_image', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('num_blocks_caption', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('num_blocks_ad', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('column_count_estimate', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('headline_candidates_count', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('layout_quality_score', sa.Float(), nullable=True))
    op.add_column('pages', sa.Column('layout_fallback_used', sa.Boolean(), nullable=True))
    op.add_column('pages', sa.Column('layout_fallback_reason', sa.String(200), nullable=True))

    # ==================== Item: Ad Detection & Salience ====================
    op.add_column('items', sa.Column('ad_candidate_score', sa.Float(), nullable=True))
    op.add_column('items', sa.Column('ad_detection_reasons', sa.JSON(), nullable=True))
    op.add_column('items', sa.Column('salience_score', sa.Float(), nullable=True))
    op.add_column('items', sa.Column('salience_reasons', sa.JSON(), nullable=True))
    op.add_column('items', sa.Column('lede_text', sa.Text(), nullable=True))
    op.add_column('items', sa.Column('key_facts_json', sa.JSON(), nullable=True))

    # Add index for salience_score
    op.create_index('ix_items_salience_score', 'items', ['salience_score'])

    # ==================== Item: Full-Text Search ====================
    # Add tsvector column for PostgreSQL FTS (will be NULL in SQLite)
    op.add_column('items', sa.Column('text_search_vector', sa.String(), nullable=True))

    # Add composite index for search filters
    op.create_index('ix_items_search', 'items', ['item_type', 'created_at'])

    # ==================== Entity Tables ====================
    # Entity table for normalized entity storage
    op.create_table(
        'entities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name_normalized', sa.String(255), nullable=False, index=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(20), nullable=False, index=True),  # PERSON, ORG, GPE, MONEY, DATE
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name_normalized', 'entity_type', name='uq_entity_name_type')
    )
    op.create_index('ix_entities_display_name', 'entities', ['display_name'])

    # Item-Entity junction table
    op.create_table(
        'item_entities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('mention_count', sa.Integer(), nullable=False, default=1),
        sa.Column('context_json', sa.JSON(), nullable=True),  # Context where entity appears
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id', 'entity_id', name='uq_item_entity')
    )

    # ==================== Topic Cluster Tables ====================
    # Topic cluster table
    op.create_table(
        'topic_clusters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('centroid_vector', sa.JSON(), nullable=True),  # Cluster centroid embedding
        sa.Column('cluster_size', sa.Integer(), nullable=False, default=0),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('label', 'window_start', name='uq_topic_window')
    )
    op.create_index('ix_topic_clusters_window', 'topic_clusters', ['window_start', 'window_end'])

    # Item-Topic junction table
    op.create_table(
        'item_topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('topic_cluster_id', sa.Integer(), sa.ForeignKey('topic_clusters.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id', 'topic_cluster_id', name='uq_item_topic')
    )

    # Trend metric table
    op.create_table(
        'trend_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_date', sa.Date(), nullable=False, index=True),
        sa.Column('metric_name', sa.String(50), nullable=False, index=True),  # e.g., 'rising_topics', 'new_entities'
        sa.Column('key', sa.String(255), nullable=False, index=True),  # e.g., topic_id, entity_id
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('previous_value', sa.Float(), nullable=True),
        sa.Column('change_percent', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('metric_date', 'metric_name', 'key', name='uq_trend_key')
    )
    op.create_index('ix_trend_metrics_date_name', 'trend_metrics', ['metric_date', 'metric_name'])

    # ==================== Thread Tables ====================
    # Thread table for cross-edition story tracking
    op.create_table(
        'threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_entities_json', sa.JSON(), nullable=True),  # Top entities in this thread
        sa.Column('topic_cluster_id', sa.Integer(), sa.ForeignKey('topic_clusters.id'), nullable=True),
        sa.Column('item_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_threads_updated', 'threads', ['updated_at'])

    # Thread-Item junction table
    op.create_table(
        'thread_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), sa.ForeignKey('threads.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('order_index', sa.Integer(), nullable=False, default=0),
        sa.Column('score', sa.Float(), nullable=True),  # Relevance score for this item in thread
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id', 'item_id', name='uq_thread_item')
    )

    # ==================== Alerts v2 Tables ====================
    # Add columns to SavedSearch for alert rules
    # Note: user_id added without FK constraint for SQLite compatibility
    # The FK relationship will be maintained in the model layer
    op.add_column('saved_searches', sa.Column('entity_ids_json', sa.JSON(), nullable=True))
    op.add_column('saved_searches', sa.Column('topic_ids_json', sa.JSON(), nullable=True))
    op.add_column('saved_searches', sa.Column('rules_json', sa.JSON(), nullable=True))
    op.add_column('saved_searches', sa.Column('alert_enabled', sa.Boolean(), nullable=False, default=False))
    op.add_column('saved_searches', sa.Column('user_id', sa.Integer(), nullable=True))

    # Alert event table
    op.create_table(
        'alert_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('saved_searches.id'), nullable=False, index=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id'), nullable=False, index=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('payload_json', sa.JSON(), nullable=True),  # Alert details
        sa.Column('delivered', sa.Boolean(), nullable=False, default=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_events_user_rule', 'alert_events', ['user_id', 'rule_id', 'triggered_at'])

    # ==================== Quality Report ====================
    # Add index to ExtractionRun for quality queries
    op.create_index('ix_extraction_runs_edition_status', 'extraction_runs', ['edition_id', 'status'])


def downgrade() -> None:
    # ==================== Quality Report ====================
    op.drop_index('ix_extraction_runs_edition_status', table_name='extraction_runs')

    # ==================== Alerts v2 Tables ====================
    op.drop_index('ix_alert_events_user_rule', table_name='alert_events')
    op.drop_table('alert_events')
    op.drop_column('saved_searches', 'user_id')
    op.drop_column('saved_searches', 'alert_enabled')
    op.drop_column('saved_searches', 'rules_json')
    op.drop_column('saved_searches', 'topic_ids_json')
    op.drop_column('saved_searches', 'entity_ids_json')

    # ==================== Thread Tables ====================
    op.drop_table('thread_items')
    op.drop_table('threads')

    # ==================== Topic Cluster Tables ====================
    op.drop_index('ix_trend_metrics_date_name', table_name='trend_metrics')
    op.drop_table('trend_metrics')
    op.drop_table('item_topics')
    op.drop_index('ix_topic_clusters_window', table_name='topic_clusters')
    op.drop_table('topic_clusters')

    # ==================== Entity Tables ====================
    op.drop_table('item_entities')
    op.drop_index('ix_entities_display_name', table_name='entities')
    op.drop_table('entities')

    # ==================== Item: Full-Text Search ====================
    op.drop_index('ix_items_search', table_name='items')
    op.drop_column('items', 'text_search_vector')

    # ==================== Item: Ad Detection & Salience ====================
    op.drop_index('ix_items_salience_score', table_name='items')
    op.drop_column('items', 'key_facts_json')
    op.drop_column('items', 'lede_text')
    op.drop_column('items', 'salience_reasons')
    op.drop_column('items', 'salience_score')
    op.drop_column('items', 'ad_detection_reasons')
    op.drop_column('items', 'ad_candidate_score')

    # ==================== Page: Layout QA Metrics ====================
    op.drop_column('pages', 'layout_fallback_reason')
    op.drop_column('pages', 'layout_fallback_used')
    op.drop_column('pages', 'layout_quality_score')
    op.drop_column('pages', 'headline_candidates_count')
    op.drop_column('pages', 'column_count_estimate')
    op.drop_column('pages', 'num_blocks_ad')
    op.drop_column('pages', 'num_blocks_caption')
    op.drop_column('pages', 'num_blocks_image')
    op.drop_column('pages', 'num_blocks_headline')
    op.drop_column('pages', 'num_blocks_body')
    op.drop_column('pages', 'num_blocks_total')
    op.drop_column('pages', 'layout_coverage_ratio')
