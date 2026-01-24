"""Add processing progress + archiving fields

Revision ID: 8f1c2a9b7e01
Revises: 22c8d210d95c
Create Date: 2025-02-12 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f1c2a9b7e01"
down_revision: Union[str, Sequence[str], None] = "22c8d210d95c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("editions") as batch_op:
        batch_op.add_column(sa.Column("pdf_local_path", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("storage_backend", sa.String(length=20), nullable=False, server_default="local"))
        batch_op.add_column(sa.Column("storage_key", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("total_pages", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("processed_pages", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("current_stage", sa.String(length=20), nullable=False, server_default="QUEUED"))
        batch_op.add_column(sa.Column("last_error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("archive_status", sa.String(length=20), nullable=False, server_default="SCHEDULED"))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("cover_image_path", sa.String(length=500), nullable=True))

    with op.batch_alter_table("pages") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="DONE"))
        batch_op.add_column(sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("ocr_used", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))

    with op.batch_alter_table("extraction_runs") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="SUCCESS"))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))

    op.execute(
        "UPDATE editions SET total_pages = num_pages WHERE total_pages = 0"
    )
    op.execute(
        "UPDATE editions SET processed_pages = pages_processed WHERE processed_pages = 0"
    )
    op.execute(
        "UPDATE editions SET pdf_local_path = file_path WHERE pdf_local_path IS NULL"
    )
    op.execute(
        "UPDATE editions SET storage_key = file_path WHERE storage_key IS NULL"
    )
    op.execute(
        "UPDATE editions SET current_stage = 'DONE' "
        "WHERE status IN ('READY', 'FAILED', 'CANCELLED', 'ARCHIVED')"
    )
    op.execute(
        "UPDATE editions SET current_stage = 'QUEUED' "
        "WHERE status IN ('UPLOADED', 'PROCESSING')"
    )
    op.execute(
        "UPDATE extraction_runs SET status = CASE WHEN success = 1 THEN 'SUCCESS' ELSE 'FAILED' END"
    )
    op.execute(
        "UPDATE extraction_runs SET completed_at = finished_at WHERE completed_at IS NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("extraction_runs") as batch_op:
        batch_op.drop_column("error_message")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("status")

    with op.batch_alter_table("pages") as batch_op:
        batch_op.drop_column("error_message")
        batch_op.drop_column("ocr_used")
        batch_op.drop_column("char_count")
        batch_op.drop_column("status")

    with op.batch_alter_table("editions") as batch_op:
        batch_op.drop_column("cover_image_path")
        batch_op.drop_column("archived_at")
        batch_op.drop_column("archive_status")
        batch_op.drop_column("last_error")
        batch_op.drop_column("current_stage")
        batch_op.drop_column("processed_pages")
        batch_op.drop_column("total_pages")
        batch_op.drop_column("storage_key")
        batch_op.drop_column("storage_backend")
        batch_op.drop_column("pdf_local_path")
