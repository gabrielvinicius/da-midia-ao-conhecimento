"""Avisos: remove colunas de canais e novas tentativas que nada usava.

Os avisos só saem pelo WebSocket; modelo, mensagem de erro e contagem de
tentativas nunca eram preenchidos.

Revision ID: b8d1f3a6c702
Revises: a4e7c2b9d531
Create Date: 2026-10-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8d1f3a6c702"
down_revision: Union[str, None] = "a4e7c2b9d531"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("template_name", "error_message", "retries", "max_retries")


def upgrade() -> None:
    for column in _COLUMNS:
        op.drop_column("notifications", column)


def downgrade() -> None:
    op.add_column("notifications", sa.Column("template_name", sa.String(), nullable=True))
    op.add_column("notifications", sa.Column("error_message", sa.String(), nullable=True))
    op.add_column("notifications", sa.Column("retries", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("notifications", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"))
