import pytest

from src.notifications.application.event_handlers import handle_notification_requested
from src.shared.events.domain_events import NotificationRequested


class DummyCeleryTask:
    def __init__(self) -> None:
        self.calls = []

    def delay(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


@pytest.mark.asyncio
async def test_handle_notification_requested_enqueues(monkeypatch):
    dummy_task = DummyCeleryTask()
    monkeypatch.setattr(
        "src.notifications.application.event_handlers.send_notification_task",
        dummy_task,
    )

    event = NotificationRequested(
        user_id="user-123",
        message="Hello",
        notification_type="EMAIL",
        contact_info={"email": "demo@example.com"},
    )

    await handle_notification_requested(event)

    assert dummy_task.calls == [
        (
            (),
            {
                "user_id": "user-123",
                "message": "Hello",
                "notification_type": "EMAIL",
                "contact_info": {"email": "demo@example.com"},
            },
        )
    ]
