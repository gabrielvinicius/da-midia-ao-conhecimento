"""Palavras vazias usadas na extração de palavras-chave dos temas.

O scikit-learn só traz a lista do inglês (stop_words="english"); passar
"portuguese" gera erro. Sem uma lista, as palavras-chave de uma transcrição
em português saem como "de", "que", "para". A lista inclui também marcas
comuns da fala ("né", "pra", "tá"), frequentes em transcrições.
"""
from __future__ import annotations

PORTUGUESE_STOPWORDS = frozenset(
    """
    a à às ao aos aquela aquelas aquele aqueles aquilo as até com como da das de
    dela delas dele deles depois do dos e é ela elas ele eles em entre era eram
    essa essas esse esses esta estas este estes eu foi foram há isso isto já la
    lá lhe lhes mais mas me mesmo meu meus minha minhas muito muita muitos muitas
    na nas nem no nos nós nossa nossas nosso nossos num numa não o os ou para
    pela pelas pelo pelos por qual quando que quem se sem ser seu seus sua suas
    só também te tem têm tinha tu tua tuas um uma umas uns você vocês vos
    ser sendo sido estar estou está estamos estão esteve estava estavam ter
    tenho temos tinham teve haver houve seja sejam fosse fossem será serão
    faz fazer feito pode podem poder vai vão vou ir indo vamos
    aqui ali aí então agora ainda assim bem bom boa coisa coisas gente onde
    porque porquê pois sobre cada todo toda todos todas outro outra outros outras
    tipo né pra pro pros tá tô ok sim hum ah eh daí dá dar vez vezes
    """.split()
)


def stop_words_for(language: str | None) -> list[str] | None:
    """Lista de palavras vazias para o idioma, ou None se não houver."""
    code = (language or "").lower().replace("_", "-").split("-")[0]
    if code in {"pt", "portuguese", "português", "portugues"}:
        return sorted(PORTUGUESE_STOPWORDS)
    if code in {"en", "english"}:
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

        return sorted(ENGLISH_STOP_WORDS)
    return None


__all__ = ["PORTUGUESE_STOPWORDS", "stop_words_for"]
