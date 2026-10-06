"""Intervalos do cabeçalho Range na reprodução."""
import pytest

from src.media_management.application.errors import InvalidRangeError
from src.media_management.application.use_cases.stream_media import byte_range


def test_without_header_the_whole_file_is_sent():
    assert byte_range(None, 100) is None


@pytest.mark.parametrize(
    "header, expected",
    [("bytes=0-9", (0, 9)), ("bytes=90-", (90, 99)), ("bytes=50-500", (50, 99))],
)
def test_requested_interval_is_clamped_to_the_file(header, expected):
    assert byte_range(header, 100) == expected


@pytest.mark.parametrize("header", ["itens=0-9", "bytes=100-", "bytes=abc", "bytes=90-10"])
def test_invalid_intervals_are_rejected(header):
    with pytest.raises(InvalidRangeError):
        byte_range(header, 100)
