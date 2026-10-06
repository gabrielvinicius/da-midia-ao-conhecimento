"""Regras sobre o perfil de um conteúdo analisado: tom, peso dos temas e
tamanho do resumo.

Ficavam espalhadas na etapa de síntese, misturadas com a montagem do prompt;
aqui não dependem de modelo nem de formato de texto.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from src.text_analysis.domain.entities.sentiment import Sentiment, SentimentLabel, TextChunk
from src.text_analysis.domain.entities.topic import Topic

# Tamanho do resumo, proporcional à transcrição: cerca de 12% das palavras,
# entre 120 e 900. Até 200 palavras, formato curto (sem seções): um resumo
# com título, seções e pontos-chave ficava do tamanho de uma fala curta.
SUMMARY_RATIO = 0.12
SUMMARY_MIN_WORDS = 120
SUMMARY_MAX_WORDS = 900
SHORT_SUMMARY_WORDS = 200

# Parcela mínima de trechos com o mesmo rótulo para o tom ser "predominante".
TONE_MAJORITY = 0.6

OUTLIER_TOPIC_ID = -1  # trechos que o BERTopic não pôs em nenhum tema


def summary_target_words(source_words: int) -> int:
    return max(SUMMARY_MIN_WORDS, min(SUMMARY_MAX_WORDS, round(source_words * SUMMARY_RATIO)))


def is_short_summary(target_words: int) -> bool:
    return target_words <= SHORT_SUMMARY_WORDS


def overall_sentiment(sentiments: Sequence[Sentiment]) -> Optional[SentimentLabel]:
    """Sentimento do conteúdo: o rótulo com a maior soma de confianças.

    A soma pondera pela frequência; com a média, um único trecho positivo
    com confiança alta vencia dezenas de trechos neutros.
    """
    if not sentiments:
        return None
    totals = {label: 0.0 for label in SentimentLabel}
    for sentiment in sentiments:
        totals[sentiment.label] += float(sentiment.score)
    return max(totals, key=totals.get)


def sentiment_distribution(sentiments: Sequence[Sentiment]) -> dict[str, int]:
    return {label.value: sum(1 for s in sentiments if s.label == label) for label in SentimentLabel}


@dataclass(frozen=True)
class Tone:
    """Tom de um conjunto de trechos. ``label`` é None quando nenhum rótulo
    chega à maioria (tom misto)."""

    label: Optional[SentimentLabel]
    count: int
    total: int


def predominant_tone(labels: Sequence[SentimentLabel]) -> Optional[Tone]:
    if not labels:
        return None
    counts = {label: list(labels).count(label) for label in SentimentLabel}
    label, count = max(counts.items(), key=lambda item: item[1])
    if count / len(labels) < TONE_MAJORITY:
        return Tone(None, count, len(labels))
    return Tone(label, count, len(labels))


def chunk_tones(chunks: Sequence[TextChunk], sentiments: Sequence[Sentiment]) -> dict[int, SentimentLabel]:
    """Rótulo de sentimento de cada trecho, pela posição do trecho."""
    by_id = {s.chunk_id: SentimentLabel.normalize(getattr(s.label, "value", s.label)) for s in sentiments}
    return {i: by_id[c.id] for i, c in enumerate(chunks) if c.id in by_id}


@dataclass(frozen=True)
class TopicProfile:
    topic: Topic
    share_percent: int  # parcela do conteúdo (em caracteres), no mínimo 1
    start: Optional[float]  # momento em que o tema começa, em gravações
    tone: Optional[Tone]


def main_topics(topics: Sequence[Topic]) -> list[Topic]:
    return [t for t in topics if t.id != OUTLIER_TOPIC_ID]


def topic_profiles(
    topics: Sequence[Topic], chunks: Sequence[TextChunk], sentiments: Sequence[Sentiment] = ()
) -> Optional[list[TopicProfile]]:
    """Temas na ordem em que aparecem, com peso, início e tom.

    None quando os pesos não podem ser calculados: temas de análises antigas
    não guardavam os trechos de cada tema.
    """
    total = sum(len(c.text) for c in chunks)

    def members(topic: Topic) -> list[int]:
        return [i for i in (topic.chunk_indices or []) if 0 <= i < len(chunks)]

    selected = main_topics(topics)
    if not total or not all(members(t) for t in selected):
        return None
    tones = chunk_tones(chunks, sentiments)
    profiles = []
    for topic in sorted(selected, key=lambda t: min(members(t))):
        indices = members(topic)
        share = round(100 * sum(len(chunks[i].text) for i in indices) / total)
        starts = [chunks[i].start for i in indices if chunks[i].start is not None]
        profiles.append(
            TopicProfile(
                topic=topic,
                share_percent=max(share, 1),
                start=min(starts) if starts else None,
                tone=predominant_tone([tones[i] for i in indices if i in tones]),
            )
        )
    return profiles


__all__ = [
    "SHORT_SUMMARY_WORDS",
    "SUMMARY_MAX_WORDS",
    "Tone",
    "TopicProfile",
    "chunk_tones",
    "is_short_summary",
    "main_topics",
    "overall_sentiment",
    "predominant_tone",
    "sentiment_distribution",
    "summary_target_words",
    "topic_profiles",
]
