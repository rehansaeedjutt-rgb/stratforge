"""Backtest configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BacktestConfig(BaseModel):
    """Configuration for a single backtest run.

    Fees and slippage are expressed in basis points (1 bps = 0.01%).
    Modeling them explicitly prevents the most common backtest lie:
    "my strategy returns 40% a year" - before costs.
    """

    initial_capital: float = Field(default=10_000.0, gt=0)
    fee_bps: float = Field(default=10.0, ge=0, description="Round-trip fee in bps.")
    slippage_bps: float = Field(default=5.0, ge=0, description="Adverse slippage in bps.")
    allow_short: bool = False
    max_position_pct: float = Field(
        default=1.0,
        gt=0,
        le=1.0,
        description="Max fraction of capital per position.",
    )

    @property
    def fee_rate(self) -> float:
        """Fee as a decimal fraction (e.g. 10 bps -> 0.001)."""
        return self.fee_bps / 10_000.0

    @property
    def slippage_rate(self) -> float:
        """Slippage as a decimal fraction."""
        return self.slippage_bps / 10_000.0
