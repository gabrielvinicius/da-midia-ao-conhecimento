"""performance optimization indexes

Revision ID: perf_opt_001
Revises: f2a5b4c3d1e0
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'perf_opt_001'
down_revision = 'f2a5b4c3d1e0'
branch_labels = None
depends_on = None


def upgrade():
    """Adiciona índices para otimização de performance."""
    
    # Índices para tabela de usuários
    op.create_index(
        'idx_users_email',
        'users',
        ['email'],
        unique=True
    )
    
    op.create_index(
        'idx_users_role',
        'users',
        ['role']
    )
    
    # Índices para tabela de mídia
    op.create_index(
        'idx_media_user_id',
        'media',
        ['user_id']
    )
    
    op.create_index(
        'idx_media_status',
        'media',
        ['status']
    )
    
    op.create_index(
        'idx_media_created_at',
        'media',
        ['created_at']
    )
    
    op.create_index(
        'idx_media_user_status',
        'media',
        ['user_id', 'status']
    )
    
    op.create_index(
        'idx_media_type_status',
        'media',
        ['media_type', 'status']
    )
    
    # Índice para busca de texto em caminhos de arquivo
    op.create_index(
        'idx_media_file_path_search',
        'media',
        ['original_file_path'],
        postgresql_using='gin',
        postgresql_ops={'original_file_path': 'gin_trgm_ops'}
    )
    
    # Índices para tabela de transcrições
    op.create_index(
        'idx_transcriptions_media_id',
        'transcriptions',
        ['media_id']
    )
    
    op.create_index(
        'idx_transcriptions_created_at',
        'transcriptions',
        ['created_at']
    )
    
    # Índices para tabela de resumos
    op.create_index(
        'idx_summaries_media_id',
        'summaries',
        ['media_id']
    )
    
    op.create_index(
        'idx_summaries_created_at',
        'summaries',
        ['created_at']
    )
    
    # Índices para tabela de análise de sentimento
    op.create_index(
        'idx_sentiment_analysis_media_id',
        'sentiment_analysis',
        ['media_id']
    )
    
    # Índices para tabela de topic modeling
    op.create_index(
        'idx_topic_modeling_media_id',
        'topic_modeling',
        ['media_id']
    )
    
    # Índices para tabela de notificações
    op.create_index(
        'idx_notifications_user_id',
        'notifications',
        ['user_id']
    )
    
    op.create_index(
        'idx_notifications_read_status',
        'notifications',
        ['is_read']
    )
    
    op.create_index(
        'idx_notifications_created_at',
        'notifications',
        ['created_at']
    )
    
    op.create_index(
        'idx_notifications_user_unread',
        'notifications',
        ['user_id', 'is_read']
    )


def downgrade():
    """Remove os índices criados."""
    
    # Remover índices na ordem reversa
    op.drop_index('idx_notifications_user_unread', table_name='notifications')
    op.drop_index('idx_notifications_created_at', table_name='notifications') 
    op.drop_index('idx_notifications_read_status', table_name='notifications')
    op.drop_index('idx_notifications_user_id', table_name='notifications')
    
    op.drop_index('idx_topic_modeling_media_id', table_name='topic_modeling')
    op.drop_index('idx_sentiment_analysis_media_id', table_name='sentiment_analysis')
    
    op.drop_index('idx_summaries_created_at', table_name='summaries')
    op.drop_index('idx_summaries_media_id', table_name='summaries')
    
    op.drop_index('idx_transcriptions_created_at', table_name='transcriptions')
    op.drop_index('idx_transcriptions_media_id', table_name='transcriptions')
    
    op.drop_index('idx_media_file_path_search', table_name='media')
    op.drop_index('idx_media_type_status', table_name='media')
    op.drop_index('idx_media_user_status', table_name='media')
    op.drop_index('idx_media_created_at', table_name='media')
    op.drop_index('idx_media_status', table_name='media')
    op.drop_index('idx_media_user_id', table_name='media')
    
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index('idx_users_email', table_name='users')