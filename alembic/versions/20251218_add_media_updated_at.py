"""Add updated_at column to media.

Revision ID: 20251218_add_media_updated_at
Revises: 20251217_add_media_cols
Create Date: 2025-12-18 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20251218_add_media_updated_at"
down_revision: Union[str, None] = "20251217_add_media_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("media", "updated_at"):
        op.add_column("media", sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.execute("UPDATE media SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    # Downgrade is intentionally conservative; only drop if column exists.
    if _column_exists("media", "updated_at"):
        op.drop_column("media", "updated_at")

