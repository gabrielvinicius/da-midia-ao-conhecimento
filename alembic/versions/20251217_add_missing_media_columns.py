"""Add missing media columns (filename, providers, language, duration)

Revision ID: 20251217_add_media_cols
Revises: c5b7f64c5f1c
Create Date: 2025-12-17 21:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251217_add_media_cols"
# Aplica após a última migration ativa (d2e4c9c1d8ac) para evitar múltiplos heads.
down_revision: Union[str, None] = "d2e4c9c1d8ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use IF NOT EXISTS to be idempotent across environments already migrated
    op.execute(
        """
        ALTER TABLE media
        ADD COLUMN IF NOT EXISTS filename VARCHAR NULL,
        ADD COLUMN IF NOT EXISTS mime_type VARCHAR NULL,
        ADD COLUMN IF NOT EXISTS file_size BIGINT NULL,
        ADD COLUMN IF NOT EXISTS duration INTEGER NULL,
        ADD COLUMN IF NOT EXISTS storage_provider VARCHAR NULL,
        ADD COLUMN IF NOT EXISTS transcription_provider VARCHAR NULL,
        ADD COLUMN IF NOT EXISTS summarization_provider VARCHAR NULL,
        ADD COLUMN IF NOT EXISTS sentiment_provider VARCHAR NULL,
        ADD COLUMN IF NOT EXISTS topic_modeling_provider VARCHAR NULL,
        ADD COLUMN IF NOT EXISTS language VARCHAR NULL;
        """
    )


def downgrade() -> None:
    # Safe rollback: drop columns if they exist
    for col in [
        "language",
        "topic_modeling_provider",
        "sentiment_provider",
        "summarization_provider",
        "transcription_provider",
        "storage_provider",
        "duration",
        "file_size",
        "mime_type",
        "filename",
    ]:
        op.execute(f"ALTER TABLE media DROP COLUMN IF EXISTS {col};")
