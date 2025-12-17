"""Add notifications table for persistence.

Revision ID: d2e4c9c1d8ac
Revises: c5b7f64c5f1c
Create Date: 2025-12-12 04:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d2e4c9c1d8ac"
down_revision: Union[str, None] = "c5b7f64c5f1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "notifications" in insp.get_table_names():
        return

    # Drop leftover enums if criadas em tentativa anterior sem tabela
    op.execute("DROP TYPE IF EXISTS notificationtype CASCADE")
    op.execute("DROP TYPE IF EXISTS notificationpriority CASCADE")
    op.execute("DROP TYPE IF EXISTS notificationstatus CASCADE")

    notif_type = sa.Enum("email", "sms", "push", "websocket", name="notificationtype")
    notif_priority = sa.Enum("low", "normal", "high", "critical", name="notificationpriority")
    notif_status = sa.Enum("pending", "sent", "delivered", "read", "failed", name="notificationstatus")

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("type", notif_type, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("priority", notif_priority, nullable=False, server_default="normal"),
        sa.Column("status", notif_status, nullable=False, server_default="pending", index=True),
        sa.Column("template_name", sa.String(), nullable=True),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
