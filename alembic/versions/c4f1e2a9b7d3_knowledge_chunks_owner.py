"""Dono de cada trecho indexado (busca sem consultar a tabela de mídias).

A busca filtrava os trechos pelo dono consultando a tabela "media", que
pertence a outro módulo. O dono passa a ser gravado no próprio trecho.

Revision ID: c4f1e2a9b7d3
Revises: ade8f6d8a85e
Create Date: 2026-10-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4f1e2a9b7d3"
down_revision: Union[str, None] = "ade8f6d8a85e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_chunks", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_knowledge_chunks_user_id"), "knowledge_chunks", ["user_id"], unique=False)
    # Trechos já indexados herdam o dono da mídia (migração de dados, uma vez).
    op.execute(
        "UPDATE knowledge_chunks AS k SET user_id = m.user_id "
        "FROM media AS m WHERE m.id = k.media_id AND k.user_id IS NULL"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_chunks_user_id"), table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "user_id")
