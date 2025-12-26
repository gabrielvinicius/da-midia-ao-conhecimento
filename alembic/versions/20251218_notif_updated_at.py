"""Add updated_at column to notifications (if missing).

Revision ID: 20251218_notif_upd_at
Revises: 20251218_merge_heads_cleanup
Create Date: 2025-12-18 19:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20251218_notif_upd_at"
down_revision: Union[str, None] = "20251218_merge_heads_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(col["name"] == column for col in insp.get_columns(table))


def upgrade() -> None:
    if not _has_column("notifications", "updated_at"):
        op.add_column(
            "notifications",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        op.execute(
            """
            UPDATE notifications
            SET updated_at = created_at
            WHERE updated_at IS NULL
            """
        )


def downgrade() -> None:
    if _has_column("notifications", "updated_at"):
        op.drop_column("notifications", "updated_at")
