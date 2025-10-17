"""
Practical examples of Template Method Pattern usage with integration
"""
from uuid import UUID
from typing import Dict, Any

# Import template decorators
from src.shared.patterns.template_integration import (
    transcription_template, summarization_template, 
    sentiment_analysis_template, video_processing_template
)

# Import traditional decorators
from src.shared.decorators.decorator_factory import read_operation, write_operation, processing_operation


class EnhancedTranscriptionService:
    """Example service with Template Method + Decorator Pattern"""
    
    @transcription_template("whisper_base")
    @processing_operation("transcription", "transcribe_with_template")
    async def transcribe_audio_with_template(
        self,
        audio_data: bytes,
        language: str = "en",
        model_size: str = "base"
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Template Method Pattern.
        
        Template handles:
        - Audio validation and preprocessing
        - Format conversion and normalization
        - Provider-specific transcription logic
        - Post-processing and cleanup
        
        Decorator handles:
        - Performance monitoring
        - Error handling and retry
        - Metrics collection
        """
        # Minimal business logic - template does the heavy lifting
        return {
            "audio_length": len(audio_data),
            "language": language,
            "model_size": model_size,
            "template_processed": True
        }
    
    @transcription_template("fast_whisper_large")
    @processing_operation("transcription", "transcribe_fast")
    async def transcribe_with_fast_whisper(
        self,
        audio_data: bytes,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Fast transcription with optimized template"""
        return {
            "audio_length": len(audio_data),
            "language": language,
            "provider": "fast_whisper"
        }


class EnhancedSummarizationService:
    """Example service with summarization templates"""
    
    @summarization_template("openai_gpt35")
    @processing_operation("summarization", "summarize_with_template")
    async def summarize_with_openai(
        self,
        text: str,
        summary_type: str = "abstractive",
        summary_length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Summarize text using OpenAI template.
        
        Template handles:
        - Text validation and preprocessing
        - Chunking for long texts
        - OpenAI API interaction
        - Summary formatting and validation
        """
        return {
            "text_length": len(text),
            "summary_type": summary_type,
            "summary_length": summary_length,
            "provider": "openai"
        }
    
    @summarization_template("hf_bart_large")
    @processing_operation("summarization", "summarize_hf")
    async def summarize_with_huggingface(
        self,
        text: str,
        max_length: int = 150
    ) -> Dict[str, Any]:
        """Summarize using HuggingFace BART model"""
        return {
            "text_length": len(text),
            "max_length": max_length,
            "provider": "huggingface"
        }


class EnhancedSentimentAnalysisService:
    """Example service with sentiment analysis templates"""
    
    @sentiment_analysis_template("hf_roberta_sentiment")
    @processing_operation("sentiment", "analyze_with_template")
    async def analyze_sentiment_with_template(
        self,
        text: str,
        granularity: str = "document",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze sentiment using Template Method Pattern.
        
        Template handles:
        - Text preprocessing and segmentation
        - Model-specific inference
        - Confidence calibration
        - Result formatting
        """
        return {
            "text_length": len(text),
            "granularity": granularity,
            "language": language,
            "provider": "huggingface"
        }
    
    @sentiment_analysis_template("hf_bert_sentiment")
    @processing_operation("sentiment", "analyze_multilingual")
    async def analyze_multilingual_sentiment(
        self,
        text: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Multilingual sentiment analysis"""
        return {
            "text_length": len(text),
            "language": language,
            "provider": "bert_multilingual"
        }


class EnhancedVideoProcessingService:
    """Example service with video processing templates"""
    
    @video_processing_template("ffmpeg_standard")
    @processing_operation("video", "process_with_template")
    async def process_video_with_template(
        self,
        video_data: bytes,
        operation: str = "transcode",
        input_format: str = "mp4",
        output_format: str = "mp4",
        quality: str = "medium"
    ) -> Dict[str, Any]:
        """
        Process video using Template Method Pattern.
        
        Template handles:
        - Video validation and analysis
        - Temporary file management
        - FFmpeg command execution
        - Output optimization and cleanup
        """
        return {
            "video_size": len(video_data),
            "operation": operation,
            "input_format": input_format,
            "output_format": output_format,
            "quality": quality
        }
    
    @video_processing_template("ffmpeg_standard")
    @processing_operation("video", "extract_audio")
    async def extract_audio_from_video(
        self,
        video_data: bytes,
        output_audio_format: str = "mp3"
    ) -> Dict[str, Any]:
        """Extract audio from video"""
        return {
            "video_size": len(video_data),
            "operation": "extract_audio",
            "output_format": output_audio_format
        }


# Multi-template processing example
class HybridProcessingService:
    """Service combining multiple template methods"""
    
    def __init__(self):
        self.transcription_service = EnhancedTranscriptionService()
        self.summarization_service = EnhancedSummarizationService()
        self.sentiment_service = EnhancedSentimentAnalysisService()
        self.video_service = EnhancedVideoProcessingService()
    
    @processing_operation("hybrid", "process_video_complete")
    async def process_video_complete(
        self,
        video_data: bytes,
        extract_text: bool = True,
        analyze_sentiment: bool = True,
        create_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Complete video processing pipeline using multiple templates:
        1. Extract audio from video (Video Template)
        2. Transcribe audio to text (Transcription Template)
        3. Create summary (Summarization Template)
        4. Analyze sentiment (Sentiment Template)
        """
        results = {}
        
        # Step 1: Extract audio using video processing template
        audio_result = await self.video_service.extract_audio_from_video(
            video_data=video_data,
            output_audio_format="wav"
        )
        results["audio_extraction"] = audio_result
        
        if extract_text:
            # Step 2: Transcribe audio using transcription template
            # Mock audio data for demonstration
            mock_audio_data = b"mock_audio_from_video"
            
            transcription_result = await self.transcription_service.transcribe_audio_with_template(
                audio_data=mock_audio_data,
                language="en"
            )
            results["transcription"] = transcription_result
            
            # Mock extracted text for further processing
            extracted_text = "This is a sample transcribed text from the video."
            
            if create_summary:
                # Step 3: Create summary using summarization template
                summary_result = await self.summarization_service.summarize_with_openai(
                    text=extracted_text,
                    summary_type="abstractive",
                    summary_length="short"
                )
                results["summary"] = summary_result
            
            if analyze_sentiment:
                # Step 4: Analyze sentiment using sentiment template
                sentiment_result = await self.sentiment_service.analyze_sentiment_with_template(
                    text=extracted_text,
                    granularity="document"
                )
                results["sentiment"] = sentiment_result
        
        return {
            "video_size": len(video_data),
            "processing_steps": len(results),
            "results": results,
            "pipeline_completed": True
        }


# Template method factory usage example
class TemplateMethodManager:
    """Manager for dynamic template selection"""
    
    @read_operation("template", "get_available_templates")
    async def get_available_templates(self, category: str = None) -> Dict[str, Any]:
        """Get available template methods"""
        from src.shared.patterns.template_method import TemplateMethodFactory
        
        all_templates = TemplateMethodFactory.get_available_templates()
        
        if category:
            # Filter templates by category
            filtered_templates = [
                template for template in all_templates 
                if category.lower() in template.lower()
            ]
            return {
                "category": category,
                "templates": filtered_templates,
                "count": len(filtered_templates)
            }
        
        return {
            "all_templates": all_templates,
            "count": len(all_templates)
        }
    
    @read_operation("template", "get_template_info")
    async def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get detailed information about a template"""
        from src.shared.patterns.template_method import TemplateMethodFactory
        
        template_info = TemplateMethodFactory.get_template_info(template_name)
        
        if not template_info:
            return {"error": f"Template '{template_name}' not found"}
        
        return template_info
    
    @processing_operation("template", "execute_dynamic_template")
    async def execute_dynamic_template(
        self,
        template_name: str,
        input_data: Any,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute template method dynamically"""
        from src.shared.patterns.template_method import TemplateMethodFactory
        
        try:
            # Create template instance
            template = TemplateMethodFactory.create_template(template_name)
            
            # Execute template
            result = await template.execute(input_data, options or {})
            
            return {
                "template_name": template_name,
                "success": result.success,
                "result": result.result,
                "processing_time": result.processing_time,
                "errors": result.errors if result.errors else None
            }
            
        except Exception as e:
            return {
                "template_name": template_name,
                "success": False,
                "error": str(e)
            }


# Initialize all templates
async def initialize_template_methods():
    """Initialize and register all template methods"""
    
    # Register transcription templates
    from src.transcription.infrastructure.templates.transcription_templates import register_transcription_templates
    register_transcription_templates()
    
    # Register summarization templates
    from src.summarization.infrastructure.templates.summarization_templates import register_summarization_templates
    register_summarization_templates()
    
    # Register sentiment analysis templates
    from src.sentiment_analysis.infrastructure.templates.sentiment_templates import register_sentiment_analysis_templates
    register_sentiment_analysis_templates()
    
    # Register video processing templates
    from src.video_processing.infrastructure.templates.video_templates import register_video_processing_templates
    register_video_processing_templates()
    
    print("✅ All template methods registered successfully")


# Example usage
async def example_template_usage():
    """Example of using template methods"""
    
    # Initialize templates
    await initialize_template_methods()
    
    # Create services
    transcription_service = EnhancedTranscriptionService()
    summarization_service = EnhancedSummarizationService()
    sentiment_service = EnhancedSentimentAnalysisService()
    video_service = EnhancedVideoProcessingService()
    hybrid_service = HybridProcessingService()
    template_manager = TemplateMethodManager()
    
    # Example 1: Transcription with template
    print("🎤 Testing transcription template...")
    try:
        transcription_result = await transcription_service.transcribe_audio_with_template(
            audio_data=b"mock_audio_data",
            language="en"
        )
        print(f"Transcription result: {transcription_result}")
    except Exception as e:
        print(f"Transcription failed: {e}")
    
    # Example 2: Summarization with template
    print("\n📄 Testing summarization template...")
    try:
        summary_result = await summarization_service.summarize_with_openai(
            text="This is a long text that needs to be summarized using the OpenAI template method pattern.",
            summary_type="abstractive"
        )
        print(f"Summary result: {summary_result}")
    except Exception as e:
        print(f"Summarization failed: {e}")
    
    # Example 3: Sentiment analysis with template
    print("\n😊 Testing sentiment analysis template...")
    try:
        sentiment_result = await sentiment_service.analyze_sentiment_with_template(
            text="I love this new template method pattern implementation!",
            granularity="document"
        )
        print(f"Sentiment result: {sentiment_result}")
    except Exception as e:
        print(f"Sentiment analysis failed: {e}")
    
    # Example 4: Video processing with template
    print("\n🎬 Testing video processing template...")
    try:
        video_result = await video_service.process_video_with_template(
            video_data=b"mock_video_data",
            operation="transcode",
            quality="medium"
        )
        print(f"Video processing result: {video_result}")
    except Exception as e:
        print(f"Video processing failed: {e}")
    
    # Example 5: Hybrid processing
    print("\n🔄 Testing hybrid processing...")
    try:
        hybrid_result = await hybrid_service.process_video_complete(
            video_data=b"mock_video_data",
            extract_text=True,
            analyze_sentiment=True,
            create_summary=True
        )
        print(f"Hybrid processing result: {hybrid_result}")
    except Exception as e:
        print(f"Hybrid processing failed: {e}")
    
    # Example 6: Template management
    print("\n📋 Testing template management...")
    available_templates = await template_manager.get_available_templates()
    print(f"Available templates: {available_templates}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_template_usage())