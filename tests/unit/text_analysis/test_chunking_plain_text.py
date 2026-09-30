"""Divisão em trechos de texto sem horários (documentos, OCR)."""
from src.text_analysis.domain import Document
from src.text_analysis.infrastructure.adapters.chunking_simple_adapter import SimpleChunker


def test_long_document_is_split_without_empty_chunks():
    text = " ".join(f"Frase número {i} do documento." for i in range(200))
    chunks = SimpleChunker().chunk(Document.from_payload(text), size=300, overlap=0)

    assert len(chunks) > 1
    assert all(c.text.strip() for c in chunks)
    assert all(c.start is None and c.end is None for c in chunks)
    # nenhum conteúdo se perde na divisão
    assert "Frase número 199 do documento." in chunks[-1].text


def test_short_document_becomes_single_chunk():
    chunks = SimpleChunker().chunk(Document.from_payload("Texto curto."), size=300, overlap=0)
    assert [c.text for c in chunks] == ["Texto curto."]
