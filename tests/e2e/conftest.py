import pytest

BASE_URL = "http://127.0.0.1:8000"

@pytest.fixture(autouse=True)
def disable_lightweight_mode(monkeypatch):
    """Disable lightweight bootstrap for e2e tests."""
    monkeypatch.setenv("LIGHTWEIGHT_BOOTSTRAP", "0")
