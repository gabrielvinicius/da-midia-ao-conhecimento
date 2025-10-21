"""
Simplified topic modeling bootstrap using unified components
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.shared.bootstrap.unified_bootstrap import create_unified_bootstrap
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository

def bootstrap_topic_modeling_module(db_session: AsyncSession, **kwargs) -> Dict[str, Any]:
    """Simplified topic modeling bootstrap - 90% less code"""
    
    bootstrap = create_unified_bootstrap(db_session)
    
    return bootstrap.bootstrap_media_module(
        module_name="topic_modeling",
        repository_class=TopicModelingRepository
    )