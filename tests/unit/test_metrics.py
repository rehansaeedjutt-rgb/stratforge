"""Tests for stratforge.metrics."""

import math

import pytest

from stratforge.metrics import (
    max_drawdown,
    periodic_returns,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    total_return,
    win_rate,
)


def test_total_return_basic() -> None:
    assert total_return([100.0, 150.0]) == pytest.approx(0.5)


def test_total_return_loss() -> None:
    assert total_return([100.0, 50.0]) == pytest.approx(-0.5)


def test_total_return_degenerate() -> None:
    assert total_return([]) == 0.0
    assert total_return([100.0]) == 0.0
    assert total_return([0.0, 100.0]) == 0.0


def test_periodic_returns() -> None:
    rets = periodic_returns([100.0, 110.0, 99.0])
    assert rets[0] == pytest.approx(0.10)
    assert rets[1] == pytest.approx(-0.10)


def test_sharpe_zero_volatility_returns_zero() -> None:
    assert sharpe_ratio([100.0, 100.0, 100.0, 100.0]) == 0.0


def test_sharpe_positive_for_uptrend() -> None:
    equity = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    assert sharpe_ratio(equity) > 0


def test_sharpe_degenerate_inputs() -> None:
    assert sharpe_ratio([]) == 0.0
    assert sharpe_ratio([100.0]) == 0.0


def test_sortino_positive_for_uptrend() -> None:
    equity = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    assert sortino_ratio(equity) > 0


def test_sortino_handles_no_downside_returns_inf() -> None:
    # All positive returns -> no downside volatility -> ideal -> +inf
    assert math.isinf(sortino_ratio([100.0, 110.0, 120.0, 130.0]))


def test_sortino_degenerate_inputs() -> None:
    assert sortino_ratio([]) == 0.0
    assert sortino_ratio([100.0]) == 0.0


def test_max_drawdown_basic() -> None:
    # Peak 120, trough 90 -> (90/120 - 1) = -0.25
    curve = [100.0, 120.0, 90.0, 110.0]
    assert max_drawdown(curve) == pytest.approx(-0.25)


def test_max_drawdown_monotonic_increase() -> None:
    assert max_drawdown([100.0, 110.0, 120.0, 130.0]) == 0.0


def test_max_drawdown_degenerate() -> None:
    assert max_drawdown([]) == 0.0
    assert max_drawdown([100.0]) == 0.0


def test_win_rate() -> None:
    assert win_rate([10.0, -5.0, 20.0, -3.0]) == pytest.approx(0.5)
    assert win_rate([]) == 0.0
    assert win_rate([10.0, 20.0]) == pytest.approx(1.0)


def test_profit_factor_basic() -> None:
    assert profit_factor([10.0, -5.0, 20.0, -3.0]) == pytest.approx(3.75)


def test_profit_factor_no_losses_returns_inf() -> None:
    assert math.isinf(profit_factor([10.0, 20.0]))


def test_profit_factor_all_losses_returns_zero() -> None:
    assert profit_factor([-10.0, -20.0]) == 0.0


def test_profit_factor_empty() -> None:
    assert profit_factor([]) == 0.0
