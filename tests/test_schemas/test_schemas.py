"""Tests for Pydantic schema models."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.schemas.analysis import AnalysisReport, FundamentalAnalysis, InvestmentRecommendation
from src.schemas.market import MarketData, MarketOverview, PriceHistory
from src.schemas.news import NewsItem, NewsSentiment
from src.schemas.tokenomics import TokenomicsData, UnlockEvent


class TestFundamentalAnalysis:
    def test_valid_construction(self):
        fa = FundamentalAnalysis(
            summary="Good project", team_score=8.0, product_score=7.5,
            track_score=8.0, tokenomics_score=6.5, sources=["report.md"],
        )
        assert fa.team_score == 8.0

    def test_score_below_min(self):
        with pytest.raises(ValidationError):
            FundamentalAnalysis(summary="x", team_score=0, product_score=7, track_score=7, tokenomics_score=7)

    def test_score_above_max(self):
        with pytest.raises(ValidationError):
            FundamentalAnalysis(summary="x", team_score=11, product_score=7, track_score=7, tokenomics_score=7)


class TestInvestmentRecommendation:
    def test_valid_construction(self):
        rec = InvestmentRecommendation(
            rating="buy", confidence=0.7,
            key_reasons=["reason"], risk_factors=["risk"],
        )
        assert rec.rating == "buy"

    def test_invalid_rating(self):
        with pytest.raises(ValidationError):
            InvestmentRecommendation(rating="moon", confidence=0.5)

    def test_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            InvestmentRecommendation(rating="buy", confidence=1.5)

    def test_negative_confidence(self):
        with pytest.raises(ValidationError):
            InvestmentRecommendation(rating="hold", confidence=-0.1)

    def test_default_disclaimer(self):
        rec = InvestmentRecommendation(rating="hold", confidence=0.5)
        assert len(rec.disclaimer) > 0


class TestAnalysisReport:
    def test_valid_construction(self):
        report = AnalysisReport(project_name="Test", workflow_type="deep_dive")
        assert report.project_name == "Test"
        assert report.analysis_date is not None

    def test_invalid_workflow_type(self):
        with pytest.raises(ValidationError):
            AnalysisReport(project_name="Test", workflow_type="invalid")


class TestMarketData:
    def test_valid_construction(self):
        md = MarketData(
            current_price=1.25, price_change_24h=3.2, price_change_7d=-5.1,
            market_cap=3.2e9, volume_24h=1e8,
        )
        assert md.current_price == 1.25

    def test_empty_indicators(self):
        md = MarketData(
            current_price=1.0, price_change_24h=0, price_change_7d=0,
            market_cap=1e9, volume_24h=1e6,
        )
        assert md.technical_indicators == {}


class TestMarketOverview:
    def test_valid_construction(self):
        mo = MarketOverview(total_market_cap=2.5e12, btc_dominance=52.5, fear_greed_index=65)
        assert mo.btc_dominance == 52.5

    def test_fear_greed_out_of_range(self):
        with pytest.raises(ValidationError):
            MarketOverview(total_market_cap=1e12, btc_dominance=50, fear_greed_index=101)


class TestNewsItem:
    def test_valid_construction(self):
        item = NewsItem(
            title="Test", source="CoinDesk", url="https://example.com",
            published_at=datetime.now(), sentiment="positive",
        )
        assert item.sentiment == "positive"

    def test_invalid_sentiment(self):
        with pytest.raises(ValidationError):
            NewsItem(
                title="Test", source="s", url="u",
                published_at=datetime.now(), sentiment="very_positive",
            )


class TestNewsSentiment:
    def test_valid_construction(self):
        ns = NewsSentiment(overall_sentiment="neutral", sentiment_score=0.0)
        assert ns.overall_sentiment == "neutral"

    def test_score_out_of_range(self):
        with pytest.raises(ValidationError):
            NewsSentiment(overall_sentiment="positive", sentiment_score=1.5)


class TestUnlockEvent:
    def test_valid_construction(self):
        ue = UnlockEvent(
            date=datetime.now(), amount=1000000, percentage=5.0,
            token_name="ARB", category="team",
        )
        assert ue.percentage == 5.0

    def test_percentage_out_of_range(self):
        with pytest.raises(ValidationError):
            UnlockEvent(
                date=datetime.now(), amount=1000, percentage=101,
                token_name="ARB", category="team",
            )


class TestTokenomicsData:
    def test_valid_construction(self):
        td = TokenomicsData(circulating_supply_ratio=0.45, top_holders_concentration=0.2)
        assert td.circulating_supply_ratio == 0.45

    def test_ratio_out_of_range(self):
        with pytest.raises(ValidationError):
            TokenomicsData(circulating_supply_ratio=1.5, top_holders_concentration=0.2)
