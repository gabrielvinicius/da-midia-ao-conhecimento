"""Erros do processamento que não passam com uma nova tentativa."""
from src.shared.domain.errors import DomainError


class UnsupportedFileTypeError(DomainError):
    def __init__(self, suffix: str):
        super().__init__(f"Tipo de arquivo não suportado para extração de texto: {suffix or 'sem extensão'}.")


class NoTextFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Nenhum texto foi encontrado no arquivo.")


class NoSpeechFoundError(DomainError):
    """Gravação sem fala reconhecível (silêncio, só música): não há o que analisar."""

    def __init__(self) -> None:
        super().__init__("Nenhuma fala foi encontrada na gravação.")
