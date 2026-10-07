"""Gênero do conteúdo: o que a mídia é (aula, reunião, documento...).

O resumo de um gênero pede coisas que o de outro não pede: de uma aula, os
conceitos e exemplos; de uma reunião, as decisões e os responsáveis; de um
ensaio opinativo, a tese atribuída a quem fala. Na avaliação, o resumo de um
vídeo opinativo afirmava as opiniões do apresentador como fatos.
"""
from __future__ import annotations

import re
import unicodedata
from enum import Enum
from typing import Optional


class ContentGenre(str, Enum):
    LECTURE = "aula"  # explicação didática de um conteúdo
    TALK = "palestra"  # apresentação para um público, com tese e argumentos
    OPINION = "opiniao"  # ensaio, crítica, comentário: posições de quem fala
    MEETING = "reuniao"  # várias pessoas decidindo e combinando tarefas
    INTERVIEW = "entrevista"  # entrevista, podcast, debate: perguntas e respostas
    TUTORIAL = "tutorial"  # passo a passo prático
    DOCUMENT = "documento"  # texto escrito: apostila, artigo, lei, contrato
    OTHER = "outro"


GENRE_LABELS = {
    ContentGenre.LECTURE: "Aula",
    ContentGenre.TALK: "Palestra",
    ContentGenre.OPINION: "Opinião / ensaio",
    ContentGenre.MEETING: "Reunião",
    ContentGenre.INTERVIEW: "Entrevista / podcast",
    ContentGenre.TUTORIAL: "Tutorial",
    ContentGenre.DOCUMENT: "Documento",
    ContentGenre.OTHER: "Outro",
}


# Radical de cada gênero: o modelo às vezes escreve a palavra com uma letra a
# menos ao tirar o acento (respondeu "opinio" para "opinião").
_STEMS = {
    "aula": ContentGenre.LECTURE,
    "palestr": ContentGenre.TALK,
    "opini": ContentGenre.OPINION,
    "ensaio": ContentGenre.OPINION,
    "reuni": ContentGenre.MEETING,
    "entrevist": ContentGenre.INTERVIEW,
    "podcast": ContentGenre.INTERVIEW,
    "tutorial": ContentGenre.TUTORIAL,
    "document": ContentGenre.DOCUMENT,
    "outro": ContentGenre.OTHER,
}


def parse_genre(answer: Optional[str]) -> Optional[ContentGenre]:
    """O primeiro gênero conhecido na resposta do modelo (sem acentos, sem
    diferença de maiúsculas, pelo radical da palavra); None se nenhum aparecer."""
    text = unicodedata.normalize("NFKD", answer or "").encode("ascii", "ignore").decode().lower()
    found = [
        (match.start(), genre)
        for stem, genre in _STEMS.items()
        for match in [re.search(rf"\b{stem}", text)]
        if match
    ]
    return min(found, key=lambda item: item[0])[1] if found else None


__all__ = ["ContentGenre", "GENRE_LABELS", "parse_genre"]
