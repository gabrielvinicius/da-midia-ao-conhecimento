"""Remove da mídia os provedores de resumo, sentimento e temas.

Eram aceitos no envio e gravados, mas a análise nunca os lia: o resumo, o
sentimento e os temas usam sempre os modelos configurados no servidor.

Revision ID: d7a3c5e1f9b2
Revises: c4f1e2a9b7d3
Create Date: 2026-10-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7a3c5e1f9b2"
down_revision: Union[str, None] = "c4f1e2a9b7d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("summarization_provider", "sentiment_provider", "topic_modeling_provider")


def upgrade() -> None:
    for column in _COLUMNS:
        op.drop_column("media", column)


def downgrade() -> None:
    for column in _COLUMNS:
        op.add_column("media", sa.Column(column, sa.String(), nullable=True))
