# src/sentiment_analysis/application/commands/analyze_sentiment_command.py
from dataclasses import dataclass

@dataclass(frozen=True)
class AnalyzeSentimentCommand:
    media_id: str
    text_content: str
    provider: str # To allow for future dynamic providers
