"""Risk-adjusted performance metrics.

All metrics accept equity curves (list of portfolio values over time).
Pure functions, no state, easy to test.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def total_return(equity_curve: Sequence[float]) -> float:
    """Return (final / initial) - 1. Zero if fewer than two points."""
    if len(equity_curve) < 2 or equity_curve[0] == 0:
        return 0.0
    return (equity_curve[-1] / equity_curve[0]) - 1.0


def periodic_returns(equity_curve: Sequence[float]) -> list[float]:
    """Compute simple period-over-period returns."""
    return [
        (equity_curve[i] / equity_curve[i - 1]) - 1.0
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] != 0
    ]


def sharpe_ratio(
    equity_curve: Sequence[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365,
) -> float:
    """Annualized Sharpe ratio from an equity curve.

    ``risk_free_rate`` is annualized. Returns 0.0 on degenerate inputs.
    """
    rets = periodic_returns(equity_curve)
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    excess = mean - (risk_free_rate / periods_per_year)
    return (excess / std) * math.sqrt(periods_per_year)


def sortino_ratio(
    equity_curve: Sequence[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365,
) -> float:
    """Like Sharpe, but penalizes only downside volatility.

    When there is no downside volatility and the mean excess return is
    positive, returns ``+inf`` (an ideal outcome with no losing periods).
    """
    rets = periodic_returns(equity_curve)
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    excess = mean - (risk_free_rate / periods_per_year)
    downside = [r for r in rets if r < 0.0]
    if not downside:
        return float("inf") if excess > 0.0 else 0.0
    downside_variance = sum(r * r for r in downside) / len(rets)
    downside_std = math.sqrt(downside_variance)
    if downside_std == 0:
        return 0.0
    return (excess / downside_std) * math.sqrt(periods_per_year)


def max_drawdown(equity_curve: Sequence[float]) -> float:
    """Largest peak-to-trough decline as a negative fraction.

    Example: -0.20 means the portfolio fell 20% from a prior peak.
    """
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (value / peak) - 1.0
            if drawdown < worst:
                worst = drawdown
    return worst


def win_rate(trade_pnls: Sequence[float]) -> float:
    """Fraction of trades with positive PnL. Zero if no trades."""
    if not trade_pnls:
        return 0.0
    wins = sum(1 for pnl in trade_pnls if pnl > 0.0)
    return wins / len(trade_pnls)


def profit_factor(trade_pnls: Sequence[float]) -> float:
    """Gross profit divided by gross loss. ``inf`` when no losses."""
    if not trade_pnls:
        return 0.0
    gross_profit = sum(pnl for pnl in trade_pnls if pnl > 0.0)
    gross_loss = -sum(pnl for pnl in trade_pnls if pnl < 0.0)
    if gross_loss == 0.0:
        return float("inf") if gross_profit > 0.0 else 0.0
    return gross_profit / gross_loss
