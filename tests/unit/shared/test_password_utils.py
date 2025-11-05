
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


def test_pbkdf2_fallback_handles_invalid_env_value(monkeypatch):
    """Non-numeric env configuration should fall back to the default iteration count."""
    monkeypatch.setattr(password_utils, "bcrypt", None)
    monkeypatch.setenv("PASSWORD_FALLBACK_ITERATIONS", "nao-e-numero")

    hasher = password_utils.PasswordHasher()
    hashed = hasher.hash_password("senha-confiavel")

    _, iterations_str, *_ = hashed.split("$", 3)
    iterations = int(iterations_str)
    assert iterations == password_utils.PasswordHasher.DEFAULT_FALLBACK_ITERATIONS
    assert hasher.verify_password("senha-confiavel", hashed)


def test_pbkdf2_fallback_detects_password_mismatch(monkeypatch):
    """Fallback verification must reject senhas diferentes."""
    monkeypatch.setattr(password_utils, "bcrypt", None)

    hasher = password_utils.PasswordHasher()
    hashed = hasher.hash_password("senha-original")

    assert hasher.verify_password("senha-original", hashed) is True
    assert hasher.verify_password("senha-alterada", hashed) is False
