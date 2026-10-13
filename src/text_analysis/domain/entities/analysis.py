"""A análise de uma mídia: o que cada etapa produziu e como terminou.

Idioma, descrições da tela, origem do resumo, verificação de fidelidade e o
resultado de cada etapa eram chaves de texto num dicionário livre
(``diagnostics``); um erro de digitação passava sem aviso. Agora são campos;
``diagnostics`` guarda só detalhes técnicos (contagens, dispositivo, tempos
de prompt).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from src.shared.domain.errors import ConflictError, NotFoundError, ValidationError
from src.text_analysis.domain.chapters import Chapter, ReviewQuestion
from src.text_analysis.domain.content_genre import ContentGenre
from src.text_analysis.domain.content_profile import main_topics
from src.text_analysis.domain.entities.document import Document
from src.text_analysis.domain.entities.sentiment import Sentiment, SentimentLabel, TextChunk
from src.text_analysis.domain.entities.topic import Topic
from src.text_analysis.domain.grounding import GroundingReport

STEP_OK = "ok"
_FAILED_PREFIX = "failed"


class SummarySource(str, Enum):
    LLM = "llm"  # modelo principal
    RESERVE = "reserve"  # modelo reserva
    SIMPLIFIED = "simplified"  # sem modelo: temas e palavras-chave


class AnalysisReviewedError(ConflictError):
    """Uma nova análise não pode substituir conteúdo revisado pelo usuário."""


class AnalysisSourceChangedError(ConflictError):
    """O pedido da fila aponta para uma transcrição que já foi substituída."""


@dataclass
class Analysis:
    id: UUID
    document: Document
    media_id: Optional[UUID] = None
    transcription_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    chunks: list[TextChunk] = field(default_factory=list)
    sentiments: list[Sentiment] = field(default_factory=list)
    overall_sentiment: Optional[SentimentLabel] = None
    topics: list[Topic] = field(default_factory=list)
    summary: Optional[str] = None
    summary_source: Optional[SummarySource] = None
    # Idioma detectado na transcrição: palavras vazias e sentimento o seguem.
    language: Optional[str] = None
    # O que aparecia na tela ("[mm:ss] descrição"), vindo do processamento do vídeo.
    visual_context: list[str] = field(default_factory=list)
    grounding: Optional[GroundingReport] = None
    # O que a mídia é (aula, reunião, documento...): orienta o resumo.
    genre: Optional[ContentGenre] = None
    # Capítulos da gravação (cortes pelos temas, títulos pelo modelo) e
    # perguntas de revisão com o momento da resposta.
    chapters: list[Chapter] = field(default_factory=list)
    review_questions: list[ReviewQuestion] = field(default_factory=list)
    # Resultado e duração de cada etapa: "ok" ou "failed: motivo".
    step_status: dict[str, str] = field(default_factory=dict)
    step_seconds: dict[str, float] = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)
    # Vetores dos trechos (mesma ordem de ``chunks``), calculados uma vez e
    # usados pelos temas, pela indexação e pela verificação de fidelidade.
    # Transitório: não é gravado com a análise.
    chunk_embeddings: list = field(default_factory=list, repr=False)
    # Identificador da requisição de envio (logs e eventos). Transitório.
    correlation_id: Optional[str] = field(default=None, repr=False)
    pipeline_completed: bool = False

    def ensure_can_regenerate(self) -> None:
        revised_fields = {"original_ai_summary", "original_ai_chapters", "original_ai_review_questions"}
        if revised_fields.intersection(self.diagnostics) or any(t.original_title is not None for t in self.topics):
            raise AnalysisReviewedError("Esta análise foi revisada. Uma nova análise não pode substituir as correções.")

    @classmethod
    def new(
        cls,
        document: Document,
        *,
        media_id: Optional[UUID] = None,
        transcription_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> "Analysis":
        return cls(
            id=uuid4(),
            document=document,
            media_id=media_id,
            transcription_id=transcription_id,
            user_id=user_id,
        )

    def record_step(self, name: str, seconds: float, error: Optional[str] = None) -> None:
        self.step_status[name] = STEP_OK if error is None else f"{_FAILED_PREFIX}: {error}"
        self.step_seconds[name] = round(seconds, 3)

    def step_succeeded(self, name: str) -> bool:
        return self.step_status.get(name) == STEP_OK

    @property
    def failed_steps(self) -> list[str]:
        return [name for name, status in self.step_status.items() if status.startswith(_FAILED_PREFIX)]

    def set_language(self, language: Optional[str]) -> None:
        """Ignora os valores que não dizem o idioma ("auto", "unknown")."""
        value = (language or "").strip().lower()
        self.language = value if value and value not in ("auto", "unknown") else None

    def language_or(self, default: str) -> str:
        return self.language or default or "pt"

    @property
    def main_topics(self) -> list[Topic]:
        return main_topics(self.topics)

    # --- Revisão humana: a versão da IA fica guardada na primeira correção.

    def rename_topic(self, topic_id: int, title: str) -> None:
        topic = next((t for t in self.topics if t.id == topic_id), None)
        if topic is None:
            raise NotFoundError("Tema não encontrado")
        topic.rename(_required_text(title, "título do tema"))

    def correct_study_aids(self, chapters: list[Chapter], questions: list[ReviewQuestion]) -> None:
        """Capítulos e perguntas revisados pelo usuário (títulos, perguntas,
        respostas, inclusões e exclusões)."""
        for chapter in chapters:
            _required_text(chapter.title, "título do capítulo")
            if chapter.start < 0 or chapter.end < chapter.start:
                raise ValidationError("capítulo", chapter.title, "precisa terminar depois de começar")
        for question in questions:
            _required_text(question.question, "pergunta")
            _required_text(question.answer, "resposta")
        self.diagnostics.setdefault(
            "original_ai_chapters", [{"start": c.start, "end": c.end, "title": c.title} for c in self.chapters]
        )
        self.diagnostics.setdefault(
            "original_ai_review_questions",
            [{"question": q.question, "answer": q.answer, "start": q.start} for q in self.review_questions],
        )
        self.chapters = sorted(chapters, key=lambda c: c.start)
        self.review_questions = list(questions)


def _required_text(value: str, what: str) -> str:
    if not (value or "").strip():
        raise ValidationError(what, value or "", "não pode ficar vazio")
    return value.strip()


__all__ = ["Analysis", "STEP_OK", "SummarySource"]
