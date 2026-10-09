"""Progresso nas perguntas de revisão (revisão espaçada).

Revision ID: d9b3e7a1c4f6
Revises: c4e7a2b9d5f1
Create Date: 2026-10-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d9b3e7a1c4f6"
down_revision: Union[str, None] = "c4e7a2b9d5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("question_key", sa.String(length=64), nullable=False),
        sa.Column("box", sa.Integer(), server_default="1", nullable=False),
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("wrong_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["text_analysis_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "analysis_id", "question_key", name="uq_review_progress_question"),
    )
    op.create_index(op.f("ix_review_progress_user_id"), "review_progress", ["user_id"], unique=False)
    op.create_index(op.f("ix_review_progress_analysis_id"), "review_progress", ["analysis_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_review_progress_analysis_id"), table_name="review_progress")
    op.drop_index(op.f("ix_review_progress_user_id"), table_name="review_progress")
    op.drop_table("review_progress")
