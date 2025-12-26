"""Merge heads after cleanup of deprecated revisions.

Revision ID: 20251218_merge_heads_cleanup
Revises: 20251218_add_media_updated_at
Create Date: 2025-12-18 15:40:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20251218_merge_heads_cleanup"
down_revision: Union[str, Sequence[str], None] = "20251218_add_media_updated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op merge: schema já consolidado nas migrations anteriores.
    pass


def downgrade() -> None:
    # Reverte para head anterior.
    pass
