# src/text_processing/application/services/text_processor.py
"""
Text processing service implementation - SRP compliance.
"""
import re
from typing import List, Dict, Any
from datetime import datetime

from src.text_processing.domain.interfaces import TextProcessor


class DefaultTextProcessor(TextProcessor):
    """
    Default implementation of text processing.
    Follows SRP - only responsible for text processing and cleaning.
    """
    
    def __init__(
        self,
        normalize_whitespace: bool = True,
        remove_extra_punctuation: bool = True,
        preserve_structure: bool = True,
        min_paragraph_length: int = 50
    ):
        self.normalize_whitespace = normalize_whitespace
        self.remove_extra_punctuation = remove_extra_punctuation
        self.preserve_structure = preserve_structure
        self.min_paragraph_length = min_paragraph_length
    
    async def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text or not text.strip():
            return ""
        
        cleaned_text = text
        
        # Basic cleaning steps
        cleaned_text = self._remove_unwanted_characters(cleaned_text)
        
        if self.normalize_whitespace:
            cleaned_text = self._normalize_whitespace(cleaned_text)
        
        if self.remove_extra_punctuation:
            cleaned_text = self._clean_punctuation(cleaned_text)
        
        if self.preserve_structure:
            cleaned_text = self._preserve_text_structure(cleaned_text)
        else:
            cleaned_text = self._flatten_text(cleaned_text)
        
        # Final cleanup
        cleaned_text = self._final_cleanup(cleaned_text)
        
        return cleaned_text.strip()
    
    async def extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract metadata from text."""
        return {
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "character_count": len(text),
            "word_count": len(text.split()),
            "paragraph_count": len(self._split_into_paragraphs(text)),
            "sentence_count": len(self._split_into_sentences(text)),
            "has_tables": self._detect_tables(text),
            "has_lists": self._detect_lists(text),
            "has_headers": self._detect_headers(text),
            "language_hints": self._extract_language_hints(text),
            "encoding_info": self._get_encoding_info(text)
        }
    
    async def chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks of specified size."""
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        
        # Try to split by paragraphs first
        paragraphs = self._split_into_paragraphs(text)
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) + 1 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # If paragraph itself is too long, split by sentences
                if len(paragraph) > chunk_size:
                    sentence_chunks = self._chunk_by_sentences(paragraph, chunk_size)
                    chunks.extend(sentence_chunks)
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _remove_unwanted_characters(self, text: str) -> str:
        """Remove unwanted characters and artifacts."""
        # Remove null bytes and other control characters (except newlines, tabs)
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remove zero-width characters
        text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
        
        # Replace different types of quotes with standard ones
        text = re.sub(r'[""''‚„]', '"', text)
        text = re.sub(r'[''`]', "'", text)
        
        # Replace different types of dashes
        text = re.sub(r'[–—]', '-', text)
        
        # Replace different types of ellipsis
        text = re.sub(r'…', '...', text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple tabs with single space
        text = re.sub(r'\t+', ' ', text)
        
        # Normalize line breaks (handle different OS line endings)
        text = re.sub(r'\r\n|\r', '\n', text)
        
        # Replace multiple line breaks with double line break
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing spaces from lines
        text = re.sub(r' +\n', '\n', text)
        
        return text
    
    def _clean_punctuation(self, text: str) -> str:
        """Clean excessive punctuation."""
        # Multiple question marks
        text = re.sub(r'\?{2,}', '?', text)
        
        # Multiple exclamation marks
        text = re.sub(r'!{2,}', '!', text)
        
        # Multiple periods (but preserve ellipsis)
        text = re.sub(r'\.{4,}', '...', text)
        
        # Multiple commas
        text = re.sub(r',{2,}', ',', text)
        
        # Remove spaces before punctuation
        text = re.sub(r' +([,.!?;:])', r'\1', text)
        
        # Add space after punctuation if missing
        text = re.sub(r'([,.!?;:])([a-zA-Z])', r'\1 \2', text)
        
        return text
    
    def _preserve_text_structure(self, text: str) -> str:
        """Preserve text structure (paragraphs, lists, etc.)."""
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                processed_lines.append(line)
            else:
                # Preserve empty lines as paragraph breaks
                if processed_lines and processed_lines[-1] != "":
                    processed_lines.append("")
        
        return '\n'.join(processed_lines)
    
    def _flatten_text(self, text: str) -> str:
        """Flatten text into continuous paragraphs."""
        # Replace single line breaks with spaces
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        
        # Clean up multiple spaces
        text = re.sub(r' +', ' ', text)
        
        return text
    
    def _final_cleanup(self, text: str) -> str:
        """Final cleanup steps."""
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        
        # Remove empty lines at start and end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        
        return '\n'.join(lines)
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+(?:\s|$)', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _chunk_by_sentences(self, text: str, chunk_size: int) -> List[str]:
        """Chunk text by sentences when paragraphs are too long."""
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) + 1 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # If sentence itself is too long, split by words
                if len(sentence) > chunk_size:
                    word_chunks = self._chunk_by_words(sentence, chunk_size)
                    chunks.extend(word_chunks)
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _chunk_by_words(self, text: str, chunk_size: int) -> List[str]:
        """Chunk text by words as last resort."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _detect_tables(self, text: str) -> bool:
        """Detect if text contains tables."""
        # Look for table markers or structured data
        table_indicators = [
            r'\[TABLE\]',
            r'\|.*\|.*\|',  # Pipe-separated columns
            r'\t.*\t.*\t',  # Tab-separated columns
        ]
        
        for pattern in table_indicators:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_lists(self, text: str) -> bool:
        """Detect if text contains lists."""
        # Look for list markers
        list_patterns = [
            r'^\s*[-*+]\s+',  # Bullet lists
            r'^\s*\d+\.\s+',  # Numbered lists
            r'^\s*[a-zA-Z]\.\s+',  # Lettered lists
        ]
        
        for pattern in list_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        
        return False
    
    def _detect_headers(self, text: str) -> bool:
        """Detect if text contains headers."""
        # Look for header patterns
        header_patterns = [
            r'^\s*#{1,6}\s+',  # Markdown headers
            r'^\s*[A-Z][A-Z\s]+$',  # ALL CAPS headers
            r'\[HEADER\]',  # Explicit header markers
        ]
        
        for pattern in header_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        
        return False
    
    def _extract_language_hints(self, text: str) -> List[str]:
        """Extract language hints from text."""
        hints = []
        
        # Look for common language-specific patterns
        if re.search(r'\b(the|and|or|but|in|on|at|to|for|of|with|by)\b', text, re.IGNORECASE):
            hints.append("english")
        
        if re.search(r'\b(el|la|los|las|un|una|de|en|con|por|para)\b', text, re.IGNORECASE):
            hints.append("spanish")
        
        if re.search(r'\b(le|la|les|un|une|de|du|des|et|ou|avec|pour)\b', text, re.IGNORECASE):
            hints.append("french")
        
        return hints
    
    def _get_encoding_info(self, text: str) -> Dict[str, Any]:
        """Get encoding information about text."""
        return {
            "has_unicode": any(ord(char) > 127 for char in text),
            "has_emoji": bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', text)),
            "has_special_chars": bool(re.search(r'[^\w\s\.,!?;:\-\'"()]', text)),
        }