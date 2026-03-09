"""Schema definitions for tokenomics data, unlock events, and vesting schedules."""

from datetime import datetime

from pydantic import BaseModel, Field


class UnlockEvent(BaseModel):
    """A single token unlock event."""

    date: datetime = Field(description="Unlock date")
    amount: float = Field(description="Number of tokens to be unlocked")
    percentage: float = Field(
        ge=0.0, le=100.0, description="Percentage of total supply being unlocked"
    )
    token_name: str = Field(description="Name of the token")
    category: str = Field(description="Unlock category (e.g., team, investor, ecosystem)")


class TokenomicsData(BaseModel):
    """Comprehensive tokenomics data for a cryptocurrency."""

    next_unlock: UnlockEvent | None = Field(
        default=None, description="Next upcoming unlock event"
    )
    circulating_supply_ratio: float = Field(
        ge=0.0, le=1.0, description="Ratio of circulating supply to total supply"
    )
    top_holders_concentration: float = Field(
        ge=0.0, le=1.0, description="Concentration ratio of top holders"
    )
    unlock_schedule: list[UnlockEvent] = Field(
        default_factory=list, description="Full unlock schedule"
    )
