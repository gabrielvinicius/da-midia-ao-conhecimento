from uuid import uuid4

import pytest

from src.shared.domain.errors import ValidationError
from src.shared.domain.value_objects.identifiers import parse_id, parse_media_id


def test_text_and_uuid_are_accepted():
    value = uuid4()
    assert parse_id(str(value)) == value
    assert parse_id(value) is value


@pytest.mark.parametrize("empty", [None, ""])
def test_empty_is_none(empty):
    assert parse_id(empty) is None


def test_garbage_is_a_validation_error():
    with pytest.raises(ValidationError):
        parse_id("não-é-uuid")


def test_media_id_is_required():
    with pytest.raises(ValidationError):
        parse_media_id(None)
