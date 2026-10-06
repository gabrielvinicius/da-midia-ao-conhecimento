"""Remove transcriptions.speaker_labels.

A coluna nunca foi preenchida: nenhum adaptador identifica quem fala. Os
apelidos de locutor (speaker_aliases) ficam, para quando houver essa etapa.

Revision ID: a4e7c2b9d531
Revises: f2c8a4d6b1e3
Create Date: 2026-10-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4e7c2b9d531"
down_revision: Union[str, None] = "f2c8a4d6b1e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("transcriptions", "speaker_labels")


def downgrade() -> None:
    op.add_column("transcriptions", sa.Column("speaker_labels", sa.JSON(), nullable=True))
