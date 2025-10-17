# src/media_management/application/services/media_authorization_service.py
from src.auth.domain.user import User
from src.media_management.domain.media import Media


class MediaAuthorizationService:
    """
    Encapsulates the business logic for authorizing user access to media resources.
    """

    def authorize_media_access(self, media: Media, user: User) -> bool:
        """
        Checks if a user is authorized to access a specific media item.
        
        Authorization Rules:
        - A user can access their own media.
        - An admin user can access any media.
        
        Args:
            media: The media item to be accessed.
            user: The user requesting access.
            
        Returns:
            True if the user is authorized, False otherwise.
        """
        if not media or not user:
            return False
            
        is_owner = str(media.user_id) == str(user.id)
        is_admin = user.role.value == "admin"
        
        return is_owner or is_admin
