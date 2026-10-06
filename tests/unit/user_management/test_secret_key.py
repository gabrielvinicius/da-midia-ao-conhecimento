"""A chave que assina os tokens precisa ser a configurada, e não a de exemplo."""
import pytest

from src.user_management.config.settings import (
    INSECURE_DEFAULT_SECRET,
    UserSettings,
    ensure_secure_secret,
)

STRONG = "k" * 48


def test_secret_key_is_read_from_the_name_used_in_env_example(monkeypatch):
    monkeypatch.delenv("USER_SECRET_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", STRONG)
    assert UserSettings(_env_file=None).secret_key == STRONG


def test_user_prefixed_name_still_works_and_wins(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", STRONG)
    monkeypatch.setenv("USER_SECRET_KEY", "u" * 48)
    assert UserSettings(_env_file=None).secret_key == "u" * 48


@pytest.mark.parametrize(
    "key", [INSECURE_DEFAULT_SECRET, "troque-esta-chave", "curta-demais"]
)
def test_startup_refuses_known_or_short_keys(key):
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        ensure_secure_secret(UserSettings(secret_key=key, _env_file=None))


def test_startup_accepts_a_strong_key():
    ensure_secure_secret(UserSettings(secret_key=STRONG, _env_file=None))
