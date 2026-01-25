"""add story groups

Revision ID: 3f8c2d1b9a2a
Revises: 8f1c2a9b7e01
Create Date: 2026-01-25 14:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3f8c2d1b9a2a"
down_revision: Union[str, Sequence[str], None] = "8f1c2a9b7e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "story_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("edition_id", sa.Integer(), sa.ForeignKey("editions.id"), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("pages_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_story_groups_edition_id"), "story_groups", ["edition_id"], unique=False)

    op.create_table(
        "story_group_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("story_group_id", sa.Integer(), sa.ForeignKey("story_groups.id"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(op.f("ix_story_group_items_story_group_id"), "story_group_items", ["story_group_id"], unique=False)
    op.create_index(op.f("ix_story_group_items_item_id"), "story_group_items", ["item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_story_group_items_item_id"), table_name="story_group_items")
    op.drop_index(op.f("ix_story_group_items_story_group_id"), table_name="story_group_items")
    op.drop_table("story_group_items")
    op.drop_index(op.f("ix_story_groups_edition_id"), table_name="story_groups")
    op.drop_table("story_groups")
