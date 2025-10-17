"""
Summarization Template Methods using Template Method Pattern
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import re

from src.shared.patterns.template_method import TemplateMethodBase, ProcessingResult, TemplateMethodFactory
from src.summarization.domain.summary import Summary


class SummaryType(str, Enum):
    """Types of summaries"""
    EXTRACTIVE = "extractive"  # Extract key sentences
    ABSTRACTIVE = "abstractive"  # Generate new text
    BULLET_POINTS = "bullet_points"  # Key points format
    HEADLINE = "headline"  # Single sentence summary


class SummaryLength(str, Enum):
    """Summary length categories"""
    SHORT = "short"  # 1-2 sentences
    MEDIUM = "medium"  # 3-5 sentences  
    LONG = "long"  # 1-2 paragraphs
    CUSTOM = "custom"  # User-defined length


@dataclass
class SummarizationInput:
    """Input data for summarization template methods"""
    text: str
    language: str = "en"
    summary_type: SummaryType = SummaryType.ABSTRACTIVE
    summary_length: SummaryLength = SummaryLength.MEDIUM
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    custom_instructions: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseSummarizationTemplate(TemplateMethodBase[SummarizationInput, Summary]):
    """
    Base template for all summarization algorithms.
    Defines the common structure for text summarization processing.
    """
    
    def __init__(self, provider_name: str, model_name: str = None):
        super().__init__(f"{provider_name}SummarizationTemplate")
        self.provider_name = provider_name
        self.model_name = model_name or "default"
        self.processed_text = None
        self.summary_result = None
        self.text_chunks = []
    
    async def _initialize(self, input_data: SummarizationInput, options: Dict[str, Any]) -> Any:
        """Initialize summarization session"""
        self.processing_result.add_metadata("provider", self.provider_name)
        self.processing_result.add_metadata("model", self.model_name)
        self.processing_result.add_metadata("language", input_data.language)
        self.processing_result.add_metadata("summary_type", input_data.summary_type.value)
        self.processing_result.add_metadata("summary_length", input_data.summary_length.value)
        
        # Initialize provider-specific resources
        await self._initialize_provider(input_data, options)
        
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "session_id": f"{self.provider_name}_{hash(input_data.text) % 10000}"
        }
    
    async def _validate(self, input_data: SummarizationInput, options: Dict[str, Any]) -> bool:
        """Validate text input"""
        
        # Check text content
        if not input_data.text or len(input_data.text.strip()) == 0:
            self.processing_result.add_error("Text content is empty")
            return False
        
        # Check text length limits
        min_text_length = options.get("min_text_length", 100)
        max_text_length = options.get("max_text_length", 1000000)
        
        text_length = len(input_data.text)
        if text_length < min_text_length:
            self.processing_result.add_error(
                f"Text too short: {text_length} chars (minimum: {min_text_length})"
            )
            return False
        
        if text_length > max_text_length:
            self.processing_result.add_error(
                f"Text too long: {text_length} chars (maximum: {max_text_length})"
            )
            return False
        
        # Check language support
        supported_languages = await self._get_supported_languages()
        if input_data.language not in supported_languages:
            self.processing_result.add_error(
                f"Language '{input_data.language}' not supported. "
                f"Supported: {', '.join(supported_languages)}"
            )
            return False
        
        # Validate summary length constraints
        if not await self._validate_length_constraints(input_data, options):
            return False
        
        # Provider-specific validation
        return await self._validate_provider_specific(input_data, options)
    
    async def _preprocess(self, input_data: SummarizationInput, options: Dict[str, Any]) -> Any:
        """Preprocess text for summarization"""
        
        # Clean and normalize text
        cleaned_text = await self._clean_text(input_data.text, options)
        
        # Extract key information
        extracted_info = await self._extract_key_information(cleaned_text, options)
        
        # Split into chunks if text is too long
        self.text_chunks = await self._chunk_text(cleaned_text, options)
        
        # Apply text preprocessing specific to summary type
        self.processed_text = await self._preprocess_for_summary_type(
            cleaned_text, 
            input_data.summary_type, 
            options
        )
        
        self.processing_result.add_metadata("preprocessing", {
            "original_length": len(input_data.text),
            "cleaned_length": len(cleaned_text),
            "processed_length": len(self.processed_text),
            "chunks_created": len(self.text_chunks),
            "key_info_extracted": bool(extracted_info)
        })
        
        return self.processed_text
    
    async def _process(self, input_data: SummarizationInput, options: Dict[str, Any]) -> Summary:
        """Core summarization processing"""
        
        # Use processed text
        text_to_summarize = self.processed_text or input_data.text
        
        # Generate summary based on type
        if input_data.summary_type == SummaryType.EXTRACTIVE:
            summary_text = await self._generate_extractive_summary(
                text_to_summarize, input_data, options
            )
        elif input_data.summary_type == SummaryType.ABSTRACTIVE:
            summary_text = await self._generate_abstractive_summary(
                text_to_summarize, input_data, options
            )
        elif input_data.summary_type == SummaryType.BULLET_POINTS:
            summary_text = await self._generate_bullet_points_summary(
                text_to_summarize, input_data, options
            )
        elif input_data.summary_type == SummaryType.HEADLINE:
            summary_text = await self._generate_headline_summary(
                text_to_summarize, input_data, options
            )
        else:
            raise ValueError(f"Unsupported summary type: {input_data.summary_type}")
        
        # Create summary object
        self.summary_result = Summary(
            text=summary_text,
            original_text=input_data.text,
            summary_type=input_data.summary_type.value,
            language=input_data.language,
            provider=self.provider_name,
            model=self.model_name,
            metadata=input_data.metadata
        )
        
        return self.summary_result
    
    async def _postprocess(self, input_data: SummarizationInput, options: Dict[str, Any]) -> Any:
        """Post-process summary results"""
        
        if not self.summary_result:
            return None
        
        # Apply summary formatting
        formatted_summary = await self._format_summary(
            self.summary_result.text,
            input_data.summary_type,
            options
        )
        
        # Extract key metrics
        metrics = await self._calculate_summary_metrics(
            self.summary_result,
            input_data,
            options
        )
        
        # Validate summary quality
        quality_score = await self._assess_summary_quality(
            self.summary_result,
            input_data,
            options
        )
        
        # Update summary with post-processed data
        self.summary_result.text = formatted_summary
        self.summary_result.metrics = metrics
        self.summary_result.quality_score = quality_score
        
        self.processing_result.add_metadata("postprocessing", {
            "formatted": formatted_summary != self.summary_result.text,
            "metrics_calculated": bool(metrics),
            "quality_score": quality_score
        })
        
        return self.summary_result
    
    async def _finalize(self, input_data: SummarizationInput, options: Dict[str, Any]) -> Summary:
        """Finalize summary and cleanup"""
        
        if not self.summary_result:
            raise ValueError("No summary result available")
        
        # Add final metadata
        self.summary_result.processing_metadata = {
            "provider": self.provider_name,
            "model": self.model_name,
            "processing_time": self.processing_result.processing_time,
            "compression_ratio": len(self.summary_result.text) / len(input_data.text),
            "word_count_original": len(input_data.text.split()),
            "word_count_summary": len(self.summary_result.text.split())
        }
        
        # Cleanup provider resources
        await self._cleanup_provider()
        
        # Set final result
        self.processing_result.result = self.summary_result
        
        return self.summary_result
    
    def _should_preprocess(self) -> bool:
        """Enable preprocessing by default"""
        return True
    
    def _should_postprocess(self) -> bool:
        """Enable postprocessing by default"""
        return True
    
    # Abstract methods for provider-specific implementation
    
    async def _initialize_provider(self, input_data: SummarizationInput, options: Dict[str, Any]) -> None:
        """Initialize provider-specific resources. Override in subclasses."""
        pass
    
    async def _get_supported_languages(self) -> List[str]:
        """Get supported languages. Override in subclasses."""
        return ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]
    
    async def _validate_provider_specific(self, input_data: SummarizationInput, options: Dict[str, Any]) -> bool:
        """Provider-specific validation. Override in subclasses."""
        return True
    
    async def _generate_abstractive_summary(
        self, 
        text: str, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> str:
        """Generate abstractive summary. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _generate_abstractive_summary")
    
    async def _cleanup_provider(self) -> None:
        """Cleanup provider resources. Override in subclasses."""
        pass
    
    # Helper methods with default implementations
    
    async def _validate_length_constraints(self, input_data: SummarizationInput, options: Dict[str, Any]) -> bool:
        """Validate summary length constraints"""
        
        if input_data.summary_length == SummaryLength.CUSTOM:
            if not input_data.max_length:
                self.processing_result.add_error("max_length required for custom summary length")
                return False
            
            if input_data.min_length and input_data.min_length > input_data.max_length:
                self.processing_result.add_error("min_length cannot be greater than max_length")
                return False
        
        return True
    
    async def _clean_text(self, text: str, options: Dict[str, Any]) -> str:
        """Clean and normalize text"""
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text)
        
        # Remove special characters if requested
        if options.get("remove_special_chars", False):
            cleaned = re.sub(r'[^\w\s\.\,\!\?\;\:]', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove URLs
        cleaned = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned)
        
        return cleaned.strip()
    
    async def _extract_key_information(self, text: str, options: Dict[str, Any]) -> Optional[Dict]:
        """Extract key information from text"""
        
        if not options.get("extract_key_info", False):
            return None
        
        # Extract sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Extract potential headings (lines in ALL CAPS or starting with numbers)
        headings = []
        for sentence in sentences:
            if sentence.isupper() or re.match(r'^\d+\.?\s', sentence):
                headings.append(sentence)
        
        return {
            "sentence_count": len(sentences),
            "headings": headings,
            "avg_sentence_length": sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        }
    
    async def _chunk_text(self, text: str, options: Dict[str, Any]) -> List[str]:
        """Split text into manageable chunks"""
        
        max_chunk_size = options.get("max_chunk_size", 2000)
        
        if len(text) <= max_chunk_size:
            return [text]
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= max_chunk_size:
                current_chunk += paragraph + '\n\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + '\n\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def _preprocess_for_summary_type(
        self, 
        text: str, 
        summary_type: SummaryType, 
        options: Dict[str, Any]
    ) -> str:
        """Apply preprocessing specific to summary type"""
        
        if summary_type == SummaryType.BULLET_POINTS:
            # For bullet points, emphasize sentence boundaries
            return re.sub(r'\.', '.\n', text)
        elif summary_type == SummaryType.HEADLINE:
            # For headlines, focus on the beginning
            sentences = re.split(r'[.!?]+', text)
            return '. '.join(sentences[:3]) if sentences else text
        else:
            return text
    
    async def _generate_extractive_summary(
        self, 
        text: str, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> str:
        """Generate extractive summary by selecting key sentences"""
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return "No content to summarize."
        
        # Simple scoring: prefer sentences with more words (indicating more content)
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = len(sentence.split())
            # Boost score for sentences at the beginning
            if i < 3:
                score *= 1.5
            scored_sentences.append((score, sentence))
        
        # Sort by score and select top sentences
        scored_sentences.sort(reverse=True)
        
        # Determine number of sentences based on length
        target_sentences = self._get_target_sentence_count(input_data.summary_length)
        selected_sentences = [s[1] for s in scored_sentences[:target_sentences]]
        
        # Reorder sentences to maintain original order
        original_order = []
        for sentence in sentences:
            if sentence in selected_sentences:
                original_order.append(sentence)
        
        return '. '.join(original_order) + '.'
    
    async def _generate_bullet_points_summary(
        self, 
        text: str, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> str:
        """Generate bullet points summary"""
        
        # Use extractive approach but format as bullet points
        extractive_summary = await self._generate_extractive_summary(text, input_data, options)
        sentences = re.split(r'[.!?]+', extractive_summary)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        bullet_points = []
        for sentence in sentences[:5]:  # Limit to 5 bullet points
            if sentence:
                bullet_points.append(f"• {sentence}")
        
        return '\n'.join(bullet_points)
    
    async def _generate_headline_summary(
        self, 
        text: str, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> str:
        """Generate headline summary"""
        
        # Extract first meaningful sentence or create from key words
        sentences = re.split(r'[.!?]+', text)
        first_sentence = next((s.strip() for s in sentences if len(s.strip()) > 10), "")
        
        if first_sentence:
            # Simplify the first sentence
            words = first_sentence.split()
            if len(words) > 12:
                return ' '.join(words[:12]) + "..."
            return first_sentence
        
        return "Summary not available"
    
    def _get_target_sentence_count(self, summary_length: SummaryLength) -> int:
        """Get target number of sentences based on length"""
        
        mapping = {
            SummaryLength.SHORT: 2,
            SummaryLength.MEDIUM: 4,
            SummaryLength.LONG: 8,
            SummaryLength.CUSTOM: 4  # Default for custom
        }
        
        return mapping.get(summary_length, 4)
    
    async def _format_summary(
        self, 
        summary_text: str, 
        summary_type: SummaryType, 
        options: Dict[str, Any]
    ) -> str:
        """Format summary according to type"""
        
        if summary_type == SummaryType.BULLET_POINTS and not summary_text.startswith('•'):
            # Convert to bullet points if not already formatted
            sentences = re.split(r'[.!?]+', summary_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            return '\n'.join(f"• {s}" for s in sentences)
        
        return summary_text
    
    async def _calculate_summary_metrics(
        self, 
        summary: Summary, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate summary quality metrics"""
        
        original_words = len(input_data.text.split())
        summary_words = len(summary.text.split())
        
        return {
            "compression_ratio": summary_words / original_words if original_words > 0 else 0,
            "word_count_reduction": original_words - summary_words,
            "summary_word_count": summary_words,
            "original_word_count": original_words,
            "readability_score": self._calculate_readability(summary.text)
        }
    
    async def _assess_summary_quality(
        self, 
        summary: Summary, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> float:
        """Assess summary quality (0.0 to 1.0)"""
        
        # Simple quality assessment based on various factors
        score = 0.0
        
        # Length appropriateness
        target_sentences = self._get_target_sentence_count(input_data.summary_length)
        actual_sentences = len(re.split(r'[.!?]+', summary.text))
        length_score = 1.0 - abs(actual_sentences - target_sentences) / target_sentences
        score += length_score * 0.3
        
        # Compression ratio appropriateness
        compression = len(summary.text) / len(input_data.text)
        if 0.1 <= compression <= 0.3:  # Good compression range
            score += 0.3
        else:
            score += 0.3 * max(0, 1 - abs(compression - 0.2) / 0.2)
        
        # Content coherence (basic check)
        if summary.text and not summary.text.isspace():
            score += 0.4
        
        return min(1.0, score)
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate basic readability score"""
        
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Simple readability: prefer 10-20 words per sentence
        if 10 <= avg_words_per_sentence <= 20:
            return 1.0
        elif avg_words_per_sentence < 10:
            return avg_words_per_sentence / 10
        else:
            return max(0.0, 1.0 - (avg_words_per_sentence - 20) / 20)


class OpenAISummarizationTemplate(BaseSummarizationTemplate):
    """OpenAI-specific summarization template"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        super().__init__("openai", model_name)
        self.openai_client = None
    
    async def _initialize_provider(self, input_data: SummarizationInput, options: Dict[str, Any]) -> None:
        """Initialize OpenAI client"""
        try:
            # In practice, initialize actual OpenAI client
            self.openai_client = f"openai_client_{self.model_name}"
            self.processing_result.add_metadata("openai_model_loaded", True)
        except Exception as e:
            self.processing_result.add_error(f"Failed to initialize OpenAI client: {e}")
    
    async def _generate_abstractive_summary(
        self, 
        text: str, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> str:
        """Generate abstractive summary using OpenAI"""
        
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        # Build prompt based on summary type and length
        prompt = self._build_openai_prompt(text, input_data, options)
        
        # In practice, call actual OpenAI API
        summary_text = f"[OpenAI {self.model_name}] Generated summary for text of {len(text)} characters"
        
        self.processing_result.add_metadata("openai_processing", {
            "model": self.model_name,
            "prompt_length": len(prompt),
            "summary_type": input_data.summary_type.value
        })
        
        return summary_text
    
    def _build_openai_prompt(
        self, 
        text: str, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> str:
        """Build OpenAI prompt for summarization"""
        
        base_prompt = f"Please summarize the following text"
        
        # Add type-specific instructions
        if input_data.summary_type == SummaryType.BULLET_POINTS:
            base_prompt += " in bullet point format"
        elif input_data.summary_type == SummaryType.HEADLINE:
            base_prompt += " in a single headline"
        elif input_data.summary_type == SummaryType.EXTRACTIVE:
            base_prompt += " by extracting the most important sentences"
        
        # Add length instructions
        if input_data.summary_length != SummaryLength.CUSTOM:
            length_map = {
                SummaryLength.SHORT: "in 1-2 sentences",
                SummaryLength.MEDIUM: "in 3-5 sentences", 
                SummaryLength.LONG: "in 1-2 paragraphs"
            }
            base_prompt += f" {length_map[input_data.summary_length]}"
        elif input_data.max_length:
            base_prompt += f" in no more than {input_data.max_length} words"
        
        # Add custom instructions
        if input_data.custom_instructions:
            base_prompt += f". Additional instructions: {input_data.custom_instructions}"
        
        return f"{base_prompt}:\n\n{text}"


class HuggingFaceSummarizationTemplate(BaseSummarizationTemplate):
    """HuggingFace-specific summarization template"""
    
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        super().__init__("huggingface", model_name)
        self.hf_model = None
        self.hf_tokenizer = None
    
    async def _initialize_provider(self, input_data: SummarizationInput, options: Dict[str, Any]) -> None:
        """Initialize HuggingFace model"""
        try:
            # In practice, load actual HuggingFace model
            self.hf_model = f"hf_model_{self.model_name}"
            self.hf_tokenizer = f"hf_tokenizer_{self.model_name}"
            self.processing_result.add_metadata("hf_model_loaded", True)
        except Exception as e:
            self.processing_result.add_error(f"Failed to load HuggingFace model: {e}")
    
    async def _generate_abstractive_summary(
        self, 
        text: str, 
        input_data: SummarizationInput, 
        options: Dict[str, Any]
    ) -> str:
        """Generate abstractive summary using HuggingFace"""
        
        if not self.hf_model:
            raise ValueError("HuggingFace model not initialized")
        
        # HuggingFace-specific processing
        max_length = self._get_hf_max_length(input_data)
        min_length = self._get_hf_min_length(input_data)
        
        summary_text = f"[HuggingFace {self.model_name}] Generated summary (max_len: {max_length})"
        
        self.processing_result.add_metadata("hf_processing", {
            "model_name": self.model_name,
            "max_length": max_length,
            "min_length": min_length,
            "text_length": len(text)
        })
        
        return summary_text
    
    def _get_hf_max_length(self, input_data: SummarizationInput) -> int:
        """Get max length for HuggingFace model"""
        
        if input_data.max_length:
            return input_data.max_length
        
        length_map = {
            SummaryLength.SHORT: 50,
            SummaryLength.MEDIUM: 100,
            SummaryLength.LONG: 200,
            SummaryLength.CUSTOM: input_data.max_length or 100
        }
        
        return length_map[input_data.summary_length]
    
    def _get_hf_min_length(self, input_data: SummarizationInput) -> int:
        """Get min length for HuggingFace model"""
        
        if input_data.min_length:
            return input_data.min_length
        
        max_length = self._get_hf_max_length(input_data)
        return max(10, max_length // 4)


# Register templates in factory
def register_summarization_templates():
    """Register all summarization templates"""
    
    # OpenAI templates
    TemplateMethodFactory.register_template(
        "openai_gpt35", 
        lambda: OpenAISummarizationTemplate("gpt-3.5-turbo")
    )
    TemplateMethodFactory.register_template(
        "openai_gpt4", 
        lambda: OpenAISummarizationTemplate("gpt-4")
    )
    
    # HuggingFace templates
    TemplateMethodFactory.register_template(
        "hf_bart_large", 
        lambda: HuggingFaceSummarizationTemplate("facebook/bart-large-cnn")
    )
    TemplateMethodFactory.register_template(
        "hf_bart_base", 
        lambda: HuggingFaceSummarizationTemplate("facebook/bart-large")
    )
    TemplateMethodFactory.register_template(
        "hf_t5_small", 
        lambda: HuggingFaceSummarizationTemplate("t5-small")
    )
    TemplateMethodFactory.register_template(
        "hf_pegasus", 
        lambda: HuggingFaceSummarizationTemplate("google/pegasus-xsum")
    )