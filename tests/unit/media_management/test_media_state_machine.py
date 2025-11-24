from uuid import uuid4

import pytest

from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media_state import DEFAULT_MEDIA_STATE_MACHINE


def test_media_state_machine_allows_expected_transitions():
    assert DEFAULT_MEDIA_STATE_MACHINE.can_transition(MediaStatus.UPLOADED, MediaStatus.PROCESSING)
    assert DEFAULT_MEDIA_STATE_MACHINE.can_transition(MediaStatus.PROCESSING, MediaStatus.COMPLETED)
    assert DEFAULT_MEDIA_STATE_MACHINE.can_transition(MediaStatus.PROCESSING, MediaStatus.FAILED)
    assert DEFAULT_MEDIA_STATE_MACHINE.can_transition(MediaStatus.FAILED, MediaStatus.PROCESSING)
    assert DEFAULT_MEDIA_STATE_MACHINE.can_transition(MediaStatus.COMPLETED, MediaStatus.PROCESSING)


def test_media_state_machine_blocks_invalid_transition():
    with pytest.raises(ValueError):
        DEFAULT_MEDIA_STATE_MACHINE.assert_transition(MediaStatus.UPLOADED, MediaStatus.COMPLETED)
