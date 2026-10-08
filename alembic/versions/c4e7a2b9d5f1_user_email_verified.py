"""E-mail confirmado no cadastro.

Com o envio de e-mails ligado, a conta só entra depois de confirmar o e-mail.
As contas existentes valem como confirmadas.

Revision ID: c4e7a2b9d5f1
Revises: b8d1f3a6c702
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e7a2b9d5f1"
down_revision: Union[str, None] = "b8d1f3a6c702"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default=sa.true(), nullable=False))


def downgrade() -> None:
    op.drop_column("users", "email_verified")
