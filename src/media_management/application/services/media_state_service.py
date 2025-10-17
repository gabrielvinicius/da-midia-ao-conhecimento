# src/media_management/application/services/media_state_service.py
from src.media_management.domain.media import Media, MediaStatus


class MediaStateService:
    @staticmethod
    def reset_for_reprocessing(media: Media) -> Media:
        """
        Validates if the media is in a FAILED state and resets it for reprocessing.

        Args:
            media: The Media entity to reset.

        Returns:
            The modified Media entity.

        Raises:
            ValueError: If the media is not in a FAILED state.
        """
        if media.status != MediaStatus.FAILED:
            raise ValueError(
                f"Media is not in a FAILED state. Current status: {media.status}"
            )

        media.status = MediaStatus.UPLOADED
        media.error_message = None
        return media
