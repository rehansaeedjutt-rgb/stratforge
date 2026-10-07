"""Tests for stratforge.portfolio."""

from datetime import UTC, datetime

import pytest

from stratforge.portfolio import Portfolio
from stratforge.schemas import Fill, Side

_TS = datetime(2026, 1, 1, tzinfo=UTC)


def _fill(side: Side, qty: float, price: float, fee: float = 0.0) -> Fill:
    return Fill(symbol="BTCUSDT", side=side, quantity=qty, price=price, fee=fee, timestamp=_TS)


def test_initial_cash_preserved() -> None:
    p = Portfolio(cash=10_000.0)
    assert p.cash == 10_000.0
    assert p.positions == {}


def test_buy_reduces_cash_and_creates_position() -> None:
    p = Portfolio(cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, qty=1.0, price=100.0, fee=0.1))
    assert p.cash == pytest.approx(10_000.0 - 100.0 - 0.1)
    pos = p.positions["BTCUSDT"]
    assert pos.quantity == pytest.approx(1.0)
    assert pos.avg_price == pytest.approx(100.0)


def test_sell_increases_cash() -> None:
    p = Portfolio(cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, qty=1.0, price=100.0, fee=0.1))
    p.apply_fill(_fill(Side.SELL, qty=1.0, price=110.0, fee=0.11))
    expected_cash = 10_000.0 - 100.0 - 0.1 + 110.0 - 0.11
    assert p.cash == pytest.approx(expected_cash)
    assert p.positions["BTCUSDT"].is_flat


def test_adding_to_position_updates_avg_price() -> None:
    p = Portfolio(cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, qty=1.0, price=100.0))
    p.apply_fill(_fill(Side.BUY, qty=1.0, price=120.0))
    pos = p.positions["BTCUSDT"]
    assert pos.quantity == pytest.approx(2.0)
    assert pos.avg_price == pytest.approx(110.0)


def test_partial_sell_keeps_avg_price() -> None:
    p = Portfolio(cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, qty=2.0, price=100.0))
    p.apply_fill(_fill(Side.SELL, qty=1.0, price=120.0))
    pos = p.positions["BTCUSDT"]
    assert pos.quantity == pytest.approx(1.0)
    assert pos.avg_price == pytest.approx(100.0)


def test_equity_with_no_positions() -> None:
    p = Portfolio(cash=10_000.0)
    assert p.equity({}) == 10_000.0


def test_equity_marks_to_market() -> None:
    p = Portfolio(cash=10_000.0)
    p.apply_fill(_fill(Side.BUY, qty=1.0, price=100.0))
    # Price moves to 150 -> equity = cash + 1 * 150
    assert p.equity({"BTCUSDT": 150.0}) == pytest.approx(10_000.0 - 100.0 + 150.0)
