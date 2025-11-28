from src.text_analysis.infrastructure.chunking import SimpleChunker
from src.text_analysis.domain import Document


def test_chunking_splits_long_text():
    text = " ".join(["sentenca"] * 200)
    doc = Document.from_payload(text)
    chunker = SimpleChunker()

    chunks = chunker.chunk(doc, size=100, overlap=20)

    assert len(chunks) > 1
    assert all(chunk.text.strip() for chunk in chunks)

