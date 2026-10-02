"""Montagem das mensagens do modelo local (Transformers), sem carregar o modelo."""
from src.text_analysis.infrastructure.adapters.text_generation_transformers_adapter import (
    TransformersTextGenerationAdapter,
)

messages = TransformersTextGenerationAdapter._chat_messages


def test_embedded_system_prompt_is_split_out():
    content = "<<<SYSTEM>>>Seja breve.<<<END_SYSTEM>>>\n[TEXTO] aula sobre grafos"
    system, user = messages("Grafos", content, ["grafo"])
    assert system == {"role": "system", "content": "Seja breve."}
    assert user == {"role": "user", "content": "[TEXTO] aula sobre grafos"}


def test_raw_text_gets_the_summary_instruction():
    system, user = messages("Grafos", "aula sobre grafos", ["grafo", "vértice"])
    assert "sumarização" in system["content"]
    assert "tópico 'Grafos'" in user["content"]
    assert "grafo, vértice" in user["content"]
    assert user["content"].endswith("aula sobre grafos")
