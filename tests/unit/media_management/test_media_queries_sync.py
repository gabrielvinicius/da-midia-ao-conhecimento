from uuid import uuid4

from src.media_management.application.queries.media_queries_sync import (
    MediaQueriesSync,
)


class _RepoStub:
    def __init__(self):
        self.called = []

    def get_by_id(self, media_id):
        self.called.append(("get_by_id", media_id))
        return "media"

    def count_all(self):
        self.called.append(("count_all", None))
        return 42


def test_media_queries_sync_delegates_to_repository():
    repo = _RepoStub()
    queries = MediaQueriesSync(media_repository=repo)

    media_id = uuid4()
    result = queries.get_by_id(media_id)
    total = queries.count_all()

    assert result == "media"
    assert total == 42
    assert repo.called[0] == ("get_by_id", media_id)
    assert repo.called[1][0] == "count_all"
