"""initial_schema

Cria a extensão pgvector e as tabelas principais (usuários, mídias,
transcrições, resultados de análise e notificações).

A primeira versão desta revisão estava vazia: tinha sido gerada contra um
banco que já possuía as tabelas. Em uma instalação nova, "alembic upgrade
head" não criava o esquema e a revisão seguinte falhava. Bancos que já estão
na revisão mais recente não são afetados por esta correção.

Revision ID: 969d17cda521
Revises:
Create Date: 2026-01-08 16:25:28.621330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '969d17cda521'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('role', sa.Enum('ADMIN', 'USER', name='userrole'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('media',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('original_file_path', sa.String(), nullable=False),
    sa.Column('filename', sa.String(), nullable=True),
    sa.Column('file_size', sa.BigInteger(), nullable=True),
    sa.Column('mime_type', sa.String(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('media_type', sa.Enum('AUDIO', 'VIDEO', 'TEXT', name='mediatype'), nullable=False),
    sa.Column('status', sa.Enum('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED', name='mediastatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('error_message', sa.String(), nullable=True),
    sa.Column('storage_provider', sa.String(), nullable=False),
    sa.Column('transcription_provider', sa.String(), nullable=True),
    sa.Column('summarization_provider', sa.String(), nullable=True),
    sa.Column('sentiment_provider', sa.String(), nullable=True),
    sa.Column('topic_modeling_provider', sa.String(), nullable=True),
    sa.Column('language', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_status'), 'media', ['status'], unique=False)
    op.create_index(op.f('ix_media_user_id'), 'media', ['user_id'], unique=False)
    op.create_table('transcriptions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('media_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('filename', sa.String(), nullable=True),
    sa.Column('correlation_id', sa.String(), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('language', sa.String(), nullable=True),
    sa.Column('confidence_score', sa.Float(), nullable=True),
    sa.Column('speaker_labels', sa.JSON(), nullable=True),
    sa.Column('segments', sa.JSON(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='transcriptionstatus'), nullable=False),
    sa.Column('provider', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_message', sa.String(), nullable=True),
    sa.Column('result', sa.JSON(), nullable=True),
    sa.Column('speaker_aliases', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['media_id'], ['media.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcriptions_media_id'), 'transcriptions', ['media_id'], unique=True)
    op.create_index(op.f('ix_transcriptions_status'), 'transcriptions', ['status'], unique=False)
    op.create_table('text_analysis_results',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('document_id', sa.String(), nullable=False),
    sa.Column('media_id', sa.Uuid(), nullable=True),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('transcription_id', sa.Uuid(), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_text_analysis_results_media_id'), 'text_analysis_results', ['media_id'], unique=False)
    op.create_index(op.f('ix_text_analysis_results_transcription_id'), 'text_analysis_results', ['transcription_id'], unique=False)
    op.create_index(op.f('ix_text_analysis_results_user_id'), 'text_analysis_results', ['user_id'], unique=False)
    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.Enum('EMAIL', 'SMS', 'PUSH', 'WEBSOCKET', name='notificationtype'), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('priority', sa.Enum('LOW', 'NORMAL', 'HIGH', 'CRITICAL', name='notificationpriority'), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'SENT', 'DELIVERED', 'READ', 'FAILED', name='notificationstatus'), nullable=False),
    sa.Column('template_name', sa.String(), nullable=True),
    sa.Column('variables', sa.JSON(), nullable=True),
    sa.Column('error_message', sa.String(), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('retries', sa.Integer(), nullable=False),
    sa.Column('max_retries', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_status'), 'notifications', ['status'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_notifications_status'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_text_analysis_results_media_id'), table_name='text_analysis_results')
    op.drop_index(op.f('ix_text_analysis_results_transcription_id'), table_name='text_analysis_results')
    op.drop_index(op.f('ix_text_analysis_results_user_id'), table_name='text_analysis_results')
    op.drop_table('text_analysis_results')
    op.drop_index(op.f('ix_transcriptions_media_id'), table_name='transcriptions')
    op.drop_index(op.f('ix_transcriptions_status'), table_name='transcriptions')
    op.drop_table('transcriptions')
    op.drop_index(op.f('ix_media_status'), table_name='media')
    op.drop_index(op.f('ix_media_user_id'), table_name='media')
    op.drop_table('media')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    sa.Enum(name='notificationstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='notificationpriority').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='notificationtype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='transcriptionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='mediastatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='mediatype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)
