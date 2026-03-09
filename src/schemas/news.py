"""Schema definitions for news items and sentiment analysis."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """A single news item with sentiment annotation."""

    title: str = Field(description="News headline")
    source: str = Field(description="News source name")
    url: str = Field(description="URL to the original article")
    published_at: datetime = Field(description="Publication timestamp")
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Sentiment classification"
    )
    summary: str = Field(default="", description="Brief summary of the article")


class NewsSentiment(BaseModel):
    """Aggregated news sentiment for a cryptocurrency."""

    overall_sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Overall sentiment across all news"
    )
    key_events: list[NewsItem] = Field(
        default_factory=list, description="Key news events"
    )
    sentiment_score: float = Field(
        ge=-1.0, le=1.0, description="Aggregated sentiment score (-1 to 1)"
    )
