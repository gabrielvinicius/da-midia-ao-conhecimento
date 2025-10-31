"""Password hashing utilities with bcrypt/PBKDF2 fallback."""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Union

try:  # noqa: SIM105 - bcrypt nem sempre disponível em ambientes de teste
    import bcrypt  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback path
    bcrypt = None  # type: ignore[assignment]


class PasswordHasher:
    """Gerenciador de hash de senhas com fallback robusto."""

    def __init__(self, rounds: int = 12, fallback_iterations: int = 260_000):
        self.rounds = rounds
        self.fallback_iterations = fallback_iterations

    def hash_password(self, password: Union[str, bytes]) -> str:
        password_bytes = self._ensure_bytes(password)

        if bcrypt is not None:
            if len(password_bytes) > 72:
                password_bytes = password_bytes[:72]
            salt = bcrypt.gensalt(rounds=self.rounds)
            hashed = bcrypt.hashpw(password_bytes, salt)
            return hashed.decode("utf-8")

        # Fallback seguro utilizando PBKDF2
        salt = os.urandom(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password_bytes,
            salt,
            self.fallback_iterations,
        )
        encoded_hash = base64.b64encode(derived).decode("utf-8")
        encoded_salt = base64.b64encode(salt).decode("utf-8")
        return f"pbkdf2_sha256${self.fallback_iterations}${encoded_salt}${encoded_hash}"

    def verify_password(self, password: Union[str, bytes], hashed_password: str) -> bool:
        password_bytes = self._ensure_bytes(password)

        if bcrypt is not None and hashed_password.startswith("$2"):
            try:
                hashed_bytes = self._ensure_bytes(hashed_password)
                if len(password_bytes) > 72:
                    password_bytes = password_bytes[:72]
                return bcrypt.checkpw(password_bytes, hashed_bytes)
            except Exception:
                return False

        try:
            algorithm, iterations_str, encoded_salt, encoded_hash = hashed_password.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iterations_str)
            salt = base64.b64decode(encoded_salt.encode("utf-8"))
            expected = base64.b64decode(encoded_hash.encode("utf-8"))
            computed = hashlib.pbkdf2_hmac(
                "sha256",
                password_bytes,
                salt,
                iterations,
            )
            return hashlib.compare_digest(computed, expected)
        except Exception:
            return False

    @staticmethod
    def _ensure_bytes(value: Union[str, bytes]) -> bytes:
        return value.encode("utf-8") if isinstance(value, str) else value


password_hasher = PasswordHasher()


def hash_password(password: Union[str, bytes]) -> str:
    return password_hasher.hash_password(password)


def verify_password(password: Union[str, bytes], hashed_password: str) -> bool:
    return password_hasher.verify_password(password, hashed_password)
