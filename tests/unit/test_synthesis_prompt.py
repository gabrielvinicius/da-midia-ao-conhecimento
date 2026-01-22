import pytest
from unittest.mock import AsyncMock, MagicMock
from src.text_analysis.application.pipeline.steps import SynthesisStep
from src.text_analysis.domain import Analysis, Topic

@pytest.mark.asyncio
async def test_synthesis_step_prompt_structure():
    # Mock TextGeneration
    mock_text_gen = AsyncMock()
    mock_text_gen.summarize_topic.return_value = "# Resumo Gerado com Sucesso"
    
    # Step
    step = SynthesisStep(mock_text_gen, language="pt-BR")
    
    # Mock Analysis with Topics
    analysis = MagicMock(spec=Analysis)
    analysis.topics = [
        Topic(
            id=0, 
            title="Topic A", 
            keywords=["key1", "key2"],
            snippets=["Evidence 1", "Evidence 2", "Evidence 3"],
            summary="Draft Summary A"
        ),
        Topic(
            id=1, 
            title="Topic B", 
            keywords=["key3", "key4"],
            snippets=["Evidence 4"],
            summary="Draft Summary B"
        ),
        Topic(
            id=-1, 
            title="Noise", 
            keywords=[], 
            snippets=["Noise 1", "Noise 2"],
            summary=None
        )
    ]
    
    # Run
    await step.process(analysis)
    
    # Verify Prompt content
    call_args = mock_text_gen.summarize_topic.call_args
    assert call_args is not None
    
    prompt_sent = call_args[0][1] # arg 1 is prompt
    
    # Check Structure requirements
    assert "Você é um Analista Sênior de Tecnologia" in prompt_sent
    assert "Wired" in prompt_sent or "The Verge" in prompt_sent
    assert "CAUSALIDADE" in prompt_sent
    assert "<main_topics>" in prompt_sent
    assert "<topic id='0'>" in prompt_sent
    assert "## A Crise e o Contexto (Análise Narrativa)" in prompt_sent
    assert "## Insights Estratégicos" in prompt_sent
    
    print("\nPrompt Validation Passed!")
    print("-" * 20)
    print(prompt_sent[:500] + "...") 
