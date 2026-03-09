"""Schema definitions for market data, price history, and market overview."""

from datetime import datetime

from pydantic import BaseModel, Field


class MarketData(BaseModel):
    """Real-time market data for a cryptocurrency."""

    current_price: float = Field(description="Current price in USD")
    price_change_24h: float = Field(description="24-hour price change percentage")
    price_change_7d: float = Field(description="7-day price change percentage")
    market_cap: float = Field(description="Market capitalization in USD")
    volume_24h: float = Field(description="24-hour trading volume in USD")
    technical_indicators: dict = Field(
        default_factory=dict, description="Technical indicators (e.g., RSI, MA)"
    )


class PriceHistory(BaseModel):
    """Historical price data for a cryptocurrency."""

    coin_id: str = Field(description="Coin identifier (e.g., 'bitcoin')")
    dates: list[str] = Field(default_factory=list, description="List of date strings")
    prices: list[float] = Field(default_factory=list, description="List of prices")
    currency: str = Field(default="usd", description="Price currency")


class MarketOverview(BaseModel):
    """Overall crypto market overview."""

    total_market_cap: float = Field(description="Total crypto market capitalization in USD")
    btc_dominance: float = Field(description="Bitcoin dominance percentage")
    fear_greed_index: int = Field(
        ge=0, le=100, description="Fear & Greed Index (0=Extreme Fear, 100=Extreme Greed)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Data timestamp"
    )
