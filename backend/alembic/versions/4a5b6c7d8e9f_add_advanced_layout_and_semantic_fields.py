"""add advanced layout and semantic fields

Revision ID: 4a5b6c7d8e9f
Revises: 3f8c2d1b9a2a
Create Date: 2026-01-29 13:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4a5b6c7d8e9f"
down_revision: Union[str, Sequence[str], None] = "3f8c2d1b9a2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add advanced layout fields to Page model
    op.add_column('pages', sa.Column('high_res_image_path', sa.String(500), nullable=True))
    op.add_column('pages', sa.Column('render_dpi', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('render_width_px', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('layout_model_used', sa.String(50), nullable=True))
    op.add_column('pages', sa.Column('layout_confidence', sa.Float(), nullable=True))
    op.add_column('pages', sa.Column('layout_method', sa.String(20), nullable=True))
    op.add_column('pages', sa.Column('ocr_words_json', sa.JSON(), nullable=True))

    # Add block storage and embeddings to Item model
    op.add_column('items', sa.Column('blocks_json', sa.JSON(), nullable=True))
    op.add_column('items', sa.Column('embedding_json', sa.JSON(), nullable=True))

    # Add semantic grouping fields to StoryGroup model
    op.add_column('story_groups', sa.Column('embedding_json', sa.JSON(), nullable=True))
    op.add_column('story_groups', sa.Column('grouping_method', sa.String(20), nullable=True))
    op.add_column('story_groups', sa.Column('similarity_score', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove fields from StoryGroup
    op.drop_column('story_groups', 'similarity_score')
    op.drop_column('story_groups', 'grouping_method')
    op.drop_column('story_groups', 'embedding_json')

    # Remove fields from Item
    op.drop_column('items', 'embedding_json')
    op.drop_column('items', 'blocks_json')

    # Remove fields from Page
    op.drop_column('pages', 'ocr_words_json')
    op.drop_column('pages', 'layout_method')
    op.drop_column('pages', 'layout_confidence')
    op.drop_column('pages', 'layout_model_used')
    op.drop_column('pages', 'render_width_px')
    op.drop_column('pages', 'render_dpi')
    op.drop_column('pages', 'high_res_image_path')
