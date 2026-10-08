from __future__ import annotations

from src.shared.domain.errors import TemporarilyUnavailableError
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.config.settings import settings
from src.text_analysis.application.ports.embeddings import EmbeddingServicePort

logger = get_logger(__name__)


class SentenceTransformerEmbeddingAdapter(EmbeddingServicePort):
    def __init__(self, model_name: str, device: str | None = None) -> None:
        self.model_name = model_name
        self.device = device or settings.resolved_device
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            try:  # pragma: no cover
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name, device=self.device)
            except Exception as exc:
                logger.warning(
                    "Embedding model unavailable", error=str(exc)
                )
            self._initialized = True
        return self._model

    def get_model_instance(self):
        """Expose the internal model instance, initializing if necessary."""
        return self._get_model()

    def embed(self, texts: list[str], kind: str = "passage") -> list[list[float]]:
        """Vetores dos textos. Sem o modelo, lança TemporarilyUnavailableError.

        Antes, devolvia vetores de reserva calculados das letras do texto: a
        busca respondia com trechos aleatórios (caso visto com a API sem GPU) e
        a análise indexava vetores sem sentido, sem nenhum aviso.
        """
        model = self._get_model()
        if model is None:
            raise TemporarilyUnavailableError(f"Modelo de vetores indisponível ({self.model_name}).")
        inputs = [self._with_prefix(text, kind) for text in texts]
        vectors = model.encode(inputs, normalize_embeddings=True)
        return [[float(v) for v in vec] for vec in vectors]

    def _with_prefix(self, text: str, kind: str) -> str:
        """Modelos E5 foram treinados com os prefixos "query: " e "passage: "."""
        if "e5" not in self.model_name.lower():
            return text
        prefix = "query: " if kind == "query" else "passage: "
        return text if text.startswith(prefix) else prefix + text
