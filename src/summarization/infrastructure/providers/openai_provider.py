# src/summarization/infrastructure/providers/openai_provider.py
"""
OpenAI summarization provider - OCP and SRP compliance.
"""
import asyncio
from typing import Dict, Any, Optional
import openai

class OpenAIConfiguration:
    """Configuration for OpenAI summarization - SRP compliance."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        max_input_length: int = 4000,
        max_output_length: int = 150,
        temperature: float = 0.3
    ):
        self.api_key = api_key
        self.model = model
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length
        self.temperature = temperature
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "model": self.model,
            "max_input_length": self.max_input_length,
            "max_output_length": self.max_output_length,
            "temperature": self.temperature,
            # Don't include API key in config output
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        return (
            bool(self.api_key) and
            bool(self.model) and
            self.max_input_length > 0 and
            self.max_output_length > 0 and
            0.0 <= self.temperature <= 2.0
        )
    
    def get_max_input_length(self) -> int:
        """Get maximum input text length."""
        return self.max_input_length
    
    def get_max_output_length(self) -> int:
        """Get maximum output summary length."""
        return self.max_output_length


class OpenAISummaryProvider(BaseSummaryProvider):
    """
    OpenAI summarization provider.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: OpenAIConfiguration):
        super().__init__(config)
        self._config = config
    
    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return "openai"
    
    def _initialize_provider(self) -> None:
        """Initialize OpenAI client."""
        try:
            openai.api_key = self._config.api_key
            # Test connection with a simple request
            # Note: In production, you might want to make this optional
        except Exception as e:
            raise SummaryProviderError(f"Failed to initialize OpenAI provider: {e}") from e
    
    async def _do_summarize(self, text: str) -> str:
        """Actual summarization implementation using OpenAI."""
        try:
            prompt = self._build_summarization_prompt(text)
            
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self._config.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful assistant that creates concise, accurate summaries."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self._config.max_output_length,
                temperature=self._config.temperature,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
            
        except openai.error.RateLimitError as e:
            raise SummaryProviderError("OpenAI rate limit exceeded") from e
        except openai.error.InvalidRequestError as e:
            raise SummaryProviderError(f"Invalid OpenAI request: {e}") from e
        except openai.error.AuthenticationError as e:
            raise SummaryProviderError("OpenAI authentication failed") from e
        except Exception as e:
            raise SummaryProviderError(f"OpenAI summarization failed: {e}") from e
    
    def _build_summarization_prompt(self, text: str) -> str:
        """Build prompt for summarization."""
        return f"""Please provide a concise summary of the following text. 
The summary should be no more than {self._config.max_output_length} characters 
and should capture the main points and key information:

{text}

Summary:"""
    
    def _supports_chunking(self) -> bool:
        """Whether provider supports text chunking."""
        return True
    
    def _supports_custom_length(self) -> bool:
        """Whether provider supports custom summary length."""
        return True
    
    async def _preprocess_text(self, text: str) -> str:
        """Preprocess text for OpenAI."""
        # Clean and normalize text
        text = await super()._preprocess_text(text)
        
        # Remove excessive whitespace and normalize
        text = " ".join(text.split())
        
        # Escape any special characters if needed
        return text
    
    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get OpenAI-specific capabilities."""
        return {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "supports_chat_format": True,
            "supports_system_prompts": True,
            "max_context_length": self._get_model_context_length()
        }
    
    def _get_model_context_length(self) -> int:
        """Get context length for the model."""
        model_limits = {
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "text-davinci-003": 4097,
            "text-davinci-002": 4097
        }
        return model_limits.get(self._config.model, 4096)
    
    async def _handle_summarization_error(self, text: str, error: Exception) -> None:
        """Handle OpenAI-specific errors."""
        if isinstance(error, openai.error.RateLimitError):
            # Could implement retry logic here
            pass
        elif isinstance(error, openai.error.InvalidRequestError):
            # Could implement text truncation here
            pass