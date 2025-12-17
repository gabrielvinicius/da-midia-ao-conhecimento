"""Add sentiment/topic provider columns to media

Revision ID: b0e2a064ae2d
Revises: afdbd95c1bf6
Create Date: 2025-11-17 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b0e2a064ae2d"
# Legacy migration afdbd95c1bf6 was removed; make this the base of the chain.
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("media", "sentiment_provider"):
        op.add_column("media", sa.Column("sentiment_provider", sa.String(), nullable=True))
    if not _column_exists("media", "topic_modeling_provider"):
        op.add_column("media", sa.Column("topic_modeling_provider", sa.String(), nullable=True))


def downgrade() -> None:
    if _column_exists("media", "topic_modeling_provider"):
        op.drop_column("media", "topic_modeling_provider")
    if _column_exists("media", "sentiment_provider"):
        op.drop_column("media", "sentiment_provider")
