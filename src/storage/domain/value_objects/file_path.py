from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from src.shared.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class FilePath:
    """Value object representing a normalized storage path."""

    path: PurePosixPath

    @staticmethod
    def from_path(raw: str) -> "FilePath":
        """Caminho relativo à raiz do armazenamento, sem sair dela.

        Antes, só o adaptador local recusava "../", e apenas ao apagar pastas:
        um caminho absoluto ou com ".." lia e gravava fora da raiz (ou outra
        chave no S3). A regra vale agora para qualquer armazenamento.
        """
        if not raw or raw.strip() == "":
            raise ValidationError("caminho", "", "o caminho do arquivo não pode ser vazio")
        path = PurePosixPath(raw.replace("\\", "/"))
        if path.is_absolute() or any(part in ("..", ".") for part in path.parts):
            raise ValidationError("caminho", raw, "o caminho sai da raiz do armazenamento")
        return FilePath(path=path)

    @property
    def value(self) -> str:
        """Return path as POSIX string for adapters that expect `.value`."""
        return str(self.path)

    def to_path(self) -> Path:
        """Return a concrete Path for local filesystem-based adapters."""
        return Path(self.path)

    def __str__(self) -> str:
        return str(self.path)
