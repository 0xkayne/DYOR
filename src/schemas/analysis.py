"""Schema definitions for analysis reports and investment recommendations."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FundamentalAnalysis(BaseModel):
    """Fundamental analysis scores and summary for a crypto project."""

    summary: str = Field(description="Overall fundamental analysis summary")
    team_score: float = Field(ge=1, le=10, description="Team quality score (1-10)")
    product_score: float = Field(ge=1, le=10, description="Product maturity score (1-10)")
    track_score: float = Field(ge=1, le=10, description="Track/sector score (1-10)")
    tokenomics_score: float = Field(ge=1, le=10, description="Tokenomics design score (1-10)")
    sources: list[str] = Field(default_factory=list, description="Sources used for analysis")


class InvestmentRecommendation(BaseModel):
    """Investment recommendation with confidence level and reasoning."""

    rating: Literal["strong_buy", "buy", "hold", "sell", "strong_sell"] = Field(
        description="Investment rating"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level (0-1)")
    key_reasons: list[str] = Field(
        default_factory=list, description="Key reasons for the recommendation"
    )
    risk_factors: list[str] = Field(
        default_factory=list, description="Identified risk factors"
    )
    disclaimer: str = Field(
        default="This is not financial advice. Always do your own research.",
        description="Legal disclaimer",
    )


class AnalysisReport(BaseModel):
    """Complete analysis report for a crypto project."""

    project_name: str = Field(description="Name of the analyzed project")
    analysis_date: datetime = Field(
        default_factory=datetime.now, description="Date of the analysis"
    )
    workflow_type: Literal["deep_dive", "compare", "brief", "qa"] = Field(
        description="Type of analysis workflow used"
    )
    fundamental_analysis: FundamentalAnalysis | None = Field(
        default=None, description="Fundamental analysis results"
    )
    market_data: dict | None = Field(default=None, description="Market data snapshot")
    news_sentiment: dict | None = Field(default=None, description="News sentiment analysis")
    tokenomics: dict | None = Field(default=None, description="Tokenomics data")
    investment_recommendation: InvestmentRecommendation | None = Field(
        default=None, description="Final investment recommendation"
    )
