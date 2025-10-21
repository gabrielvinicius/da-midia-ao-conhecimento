"""
Simplified summarization bootstrap using unified components
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.shared.bootstrap.unified_bootstrap import create_unified_bootstrap
from src.summarization.infrastructure.summary_repository import SummaryRepository

def bootstrap_summarization_module(db_session: AsyncSession, **kwargs) -> Dict[str, Any]:
    """Simplified summarization bootstrap - 90% less code"""
    
    bootstrap = create_unified_bootstrap(db_session)
    
    return bootstrap.bootstrap_media_module(
        module_name="summarization", 
        repository_class=SummaryRepository
    )