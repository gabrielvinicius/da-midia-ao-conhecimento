# src/summarization/infrastructure/openai_summarizer.py
import openai
from typing import Dict, Any, Optional

class OpenAISummarizer:
    async def summarize(self, text_content: str, options: Optional[Dict[str, Any]] = None) -> str: # Atualizar assinatura
        # Usar opções se fornecidas, caso contrário, usar defaults
        model = options.get("model", "gpt-4") if options else "gpt-4"
        
        response = await openai.ChatCompletion.acreate(
            model=model,
            messages=[
                {"role": "system", "content": "Resuma o seguinte texto:"},
                {"role": "user", "content": text_content}
            ],
            **options.get("api_params", {}) if options else {} # Passar parâmetros adicionais da API
        )
        return response.choices[0].message["content"].strip()