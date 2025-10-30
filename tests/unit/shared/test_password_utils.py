import pytest

from src.shared.utils import password_utils


def test_pbkdf2_fallback_enforces_iteration_floor(monkeypatch):
    """Ensure fallback hashing clamps to the minimum allowed iterations."""

    monkeypatch.setattr(password_utils, "bcrypt", None)
    monkeypatch.setenv("PASSWORD_FALLBACK_ITERATIONS", "1000")

    hasher = password_utils.PasswordHasher()
    hashed = hasher.hash_password("segredo-super")

    assert hashed.startswith("pbkdf2_sha256$")

    _, iterations_str, encoded_salt, encoded_hash = hashed.split("$", 3)
    iterations = int(iterations_str)
    assert iterations >= password_utils.PasswordHasher.MIN_FALLBACK_ITERATIONS

    assert hasher.verify_password("segredo-super", hashed)

    # Ensure the generated salt has sufficient entropy (base64 length 24 -> 16 bytes)
    assert len(encoded_salt) == 24
    assert len(encoded_hash) > 0
