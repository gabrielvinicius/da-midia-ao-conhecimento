"""Ciclo de vida da mídia: enviada → processando → analisando → concluída."""
from uuid import uuid4

import pytest

from src.media_management.domain import InvalidMediaTransitionError, Media, MediaStatus, MediaType


def _media(status=MediaStatus.UPLOADED):
    media = Media.create(
        media_id=uuid4(), user_id=uuid4(), filename="aula.mp4", file_size_bytes=10,
        media_type=MediaType.VIDEO, storage_provider="local", original_file_path="u/aula.mp4",
    )
    media.status = status
    return media


def test_the_normal_path_ends_after_the_analysis():
    media = _media()
    media.mark_as_processing()
    media.mark_text_ready()
    assert media.status == MediaStatus.ANALYZING
    media.mark_as_completed()
    assert media.status == MediaStatus.COMPLETED


@pytest.mark.parametrize("status", [MediaStatus.UPLOADED, MediaStatus.PROCESSING, MediaStatus.ANALYZING])
def test_any_running_stage_can_fail(status):
    media = _media(status)
    media.mark_as_failed("sem memória")
    assert (media.status, media.error_message) == (MediaStatus.FAILED, "sem memória")


def test_text_ready_is_accepted_even_if_the_start_was_not_recorded():
    media = _media(MediaStatus.UPLOADED)
    media.mark_text_ready()
    assert media.status == MediaStatus.ANALYZING


@pytest.mark.parametrize(
    "status, change",
    [
        (MediaStatus.FAILED, Media.mark_text_ready),  # transcrição depois do prazo
        (MediaStatus.COMPLETED, Media.mark_as_processing),  # tarefa repetida
        (MediaStatus.COMPLETED, lambda m: m.mark_as_failed("atrasado")),
        (MediaStatus.PROCESSING, Media.mark_as_completed),  # pula a análise
    ],
)
def test_out_of_order_changes_are_refused(status, change):
    media = _media(status)
    with pytest.raises(InvalidMediaTransitionError):
        change(media)
    assert media.status == status


def test_repeating_the_current_state_is_accepted():
    media = _media(MediaStatus.ANALYZING)
    media.mark_text_ready()
    assert media.status == MediaStatus.ANALYZING


def test_a_late_analysis_still_completes_a_media_given_up_on_and_clears_the_error():
    media = _media(MediaStatus.ANALYZING)
    media.mark_as_failed("A análise não terminou no prazo.")
    media.mark_as_completed()
    assert (media.status, media.error_message) == (MediaStatus.COMPLETED, None)


def test_reprocessing_restarts_a_failed_media_without_the_old_error():
    media = _media(MediaStatus.FAILED)
    media.error_message = "falhou"
    media.process()
    assert (media.status, media.error_message) == (MediaStatus.PROCESSING, None)
