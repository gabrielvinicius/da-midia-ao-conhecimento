"""Add summary enrichment fields

Revision ID: 0f32d570b4f2
Revises: b0e2a064ae2d
Create Date: 2025-11-26 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0f32d570b4f2"
down_revision: Union[str, None] = "b0e2a064ae2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("summaries", "bullet_points"):
        op.add_column(
            "summaries",
            sa.Column("bullet_points", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    if not _column_exists("summaries", "key_topics"):
        op.add_column(
            "summaries",
            sa.Column("key_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    if not _column_exists("summaries", "strategy"):
        op.add_column("summaries", sa.Column("strategy", sa.String(length=255), nullable=True))
    if not _column_exists("summaries", "confidence_score"):
        op.add_column("summaries", sa.Column("confidence_score", sa.Float(), nullable=True))
    if not _column_exists("summaries", "processing_time"):
        op.add_column("summaries", sa.Column("processing_time", sa.Float(), nullable=True))


def downgrade() -> None:
    if _column_exists("summaries", "processing_time"):
        op.drop_column("summaries", "processing_time")
    if _column_exists("summaries", "confidence_score"):
        op.drop_column("summaries", "confidence_score")
    if _column_exists("summaries", "strategy"):
        op.drop_column("summaries", "strategy")
    if _column_exists("summaries", "key_topics"):
        op.drop_column("summaries", "key_topics")
    if _column_exists("summaries", "bullet_points"):
        op.drop_column("summaries", "bullet_points")
