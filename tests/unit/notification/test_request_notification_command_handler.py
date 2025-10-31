# tests/unit/notification/test_request_notification_command_handler.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.notifications.application.commands.request_notification_command import RequestNotificationCommand
from src.notifications.application.commands.request_notification_command_handler import RequestNotificationCommandHandler
from src.notifications.domain.notification import NotificationType
from src.shared.events.domain_events import NotificationRequested
from src.auth.domain.user import User, UserRole

@pytest.fixture
def mock_auth_queries():
    return AsyncMock()

@pytest.fixture
def mock_event_bus():
    return AsyncMock()

@pytest.mark.asyncio
async def test_request_notification_handler_publishes_event(mock_auth_queries, mock_event_bus):
    """Tests that the RequestNotificationCommandHandler correctly enriches and publishes an event."""
    # Arrange
    user_id = str(uuid4())
    user_email = "test@example.com"
    user = User(id=user_id, email=user_email, role=UserRole.USER, hashed_password="")
    mock_auth_queries.get_by_id.return_value = user

    handler = RequestNotificationCommandHandler(
        auth_queries=mock_auth_queries,
        event_bus=mock_event_bus
    )
    command = RequestNotificationCommand(
        user_id=user_id,
        message="Test message",
        notification_type=NotificationType.EMAIL
    )

    # Act
    await handler.handle(command)

    # Assert
    mock_auth_queries.get_by_id.assert_awaited_once_with(user_id)
    mock_event_bus.publish.assert_awaited_once()
    published_event = mock_event_bus.publish.await_args.args[0]
    assert isinstance(published_event, NotificationRequested)
    assert published_event.user_id == user_id
    assert published_event.contact_info["email"] == user_email
