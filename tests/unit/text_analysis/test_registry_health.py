import sys

import builtins

from src.text_analysis.bootstrap import _update_registry_availability
from src.text_analysis.infrastructure.dependencies import registry


def test_registry_marks_unavailable_when_imports_fail(monkeypatch):
    real_import = builtins.__import__

    def fail_import(name, *args, **kwargs):
        if name in ("transformers", "bertopic", "sklearn", "numpy"):
            raise ImportError("fail")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_import)

    # force httpx failure
    class _FailClient:
        def __init__(self, *_, **__):
            pass
        def __enter__(self):
            raise RuntimeError("fail")
        def __exit__(self, *exc):
            return False
    monkeypatch.setattr("httpx.Client", _FailClient, raising=False)

    _update_registry_availability()

    assert any(not e.available for e in registry.TEXT_GEN_PROVIDERS if e.name.startswith("hf:"))
    assert any(not e.available for e in registry.TOPIC_PROVIDERS if e.name == "bertopic")
    assert any(not e.available for e in registry.TOPIC_PROVIDERS if e.name == "tfidf")
