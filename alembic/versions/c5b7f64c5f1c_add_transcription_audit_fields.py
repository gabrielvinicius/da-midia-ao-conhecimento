"""Add audit fields to transcriptions (user, filename, correlation).

Revision ID: c5b7f64c5f1c
Revises: bc2700b46d2f
Create Date: 2025-12-12 03:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c5b7f64c5f1c"
down_revision: Union[str, None] = "bc2700b46d2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transcriptions", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column("transcriptions", sa.Column("filename", sa.String(), nullable=True))
    op.add_column("transcriptions", sa.Column("correlation_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_transcriptions_user_id"), "transcriptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_transcriptions_correlation_id"), "transcriptions", ["correlation_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transcriptions_correlation_id"), table_name="transcriptions")
    op.drop_index(op.f("ix_transcriptions_user_id"), table_name="transcriptions")
    op.drop_column("transcriptions", "correlation_id")
    op.drop_column("transcriptions", "filename")
    op.drop_column("transcriptions", "user_id")

