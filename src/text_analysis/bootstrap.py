# src/text_analysis/bootstrap.py
"""
Bootstrap module for the consolidated text analysis service.
"""
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.text_analysis.application.services import TextAnalysisService
# Import routers when they are consolidated
# from src.text_analysis.api.routers import router as text_analysis_router

logger = structlog.get_logger(__name__)


async def build_text_analysis_module(session: AsyncSession) -> SimpleNamespace:
    """
    Builds and configures the text analysis module and its dependencies.
    """
    logger.info("text_analysis.bootstrap.started")

    # Initialize services and repositories
    text_analysis_service = TextAnalysisService()

    logger.info("text_analysis.bootstrap.completed")

    return SimpleNamespace(
        service=text_analysis_service,
        # router=text_analysis_router  # Add router when created
    )
