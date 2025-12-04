from dataclasses import dataclass
from typing import Any

from src.media_management.application.commands.use_cases import (
    CreateMedia,
    DeleteMedia,
    ReprocessMedia,
    CleanupOrphanedFiles,
)
from src.media_management.application.queries.use_cases import (
    GetMedia,
    ListMedia,
    GetMediaStatistics,
)


# Placeholder dependencies for FastAPI overrides
def get_create_media() -> CreateMedia:
    raise NotImplementedError

def get_delete_media() -> DeleteMedia:
    raise NotImplementedError

def get_reprocess_media() -> ReprocessMedia:
    raise NotImplementedError

def get_cleanup_media() -> CleanupOrphanedFiles:
    raise NotImplementedError

def get_get_media() -> GetMedia:
    raise NotImplementedError

def get_list_media() -> ListMedia:
    raise NotImplementedError

def get_get_media_statistics() -> GetMediaStatistics:
    raise NotImplementedError


@dataclass
class MediaDependencies:
    # Kept for backward compatibility if any external module imports it, 
    # but ideally should be removed.
    pass