"""Tests for stratforge.schemas."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from stratforge.schemas import Bar, Fill, Order, OrderType, Position, Side

_TS = datetime(2026, 1, 1, tzinfo=UTC)


def test_side_opposite() -> None:
    assert Side.BUY.opposite() is Side.SELL
    assert Side.SELL.opposite() is Side.BUY


def test_bar_requires_positive_prices() -> None:
    with pytest.raises(ValidationError):
        Bar(symbol="BTCUSDT", timestamp=_TS, open=0, high=1, low=1, close=1, volume=1)


def test_bar_allows_zero_volume() -> None:
    bar = Bar(symbol="BTCUSDT", timestamp=_TS, open=1, high=2, low=0.5, close=1.5, volume=0)
    assert bar.volume == 0


def test_bar_is_immutable() -> None:
    bar = Bar(symbol="BTCUSDT", timestamp=_TS, open=1, high=2, low=0.5, close=1.5, volume=1)
    with pytest.raises(ValidationError):
        bar.close = 99.0  # type: ignore[misc]


def test_order_defaults_to_market() -> None:
    order = Order(symbol="BTCUSDT", side=Side.BUY, quantity=0.1, timestamp=_TS)
    assert order.order_type is OrderType.MARKET
    assert order.limit_price is None


def test_order_requires_positive_quantity() -> None:
    with pytest.raises(ValidationError):
        Order(symbol="BTCUSDT", side=Side.BUY, quantity=0, timestamp=_TS)


def test_fill_notional_buy_positive() -> None:
    fill = Fill(
        symbol="BTCUSDT",
        side=Side.BUY,
        quantity=0.5,
        price=100.0,
        fee=0.1,
        timestamp=_TS,
    )
    assert fill.notional == pytest.approx(50.0)


def test_fill_notional_sell_negative() -> None:
    fill = Fill(
        symbol="BTCUSDT",
        side=Side.SELL,
        quantity=0.5,
        price=100.0,
        fee=0.1,
        timestamp=_TS,
    )
    assert fill.notional == pytest.approx(-50.0)


def test_fill_rejects_negative_fee() -> None:
    with pytest.raises(ValidationError):
        Fill(symbol="BTCUSDT", side=Side.BUY, quantity=1, price=1, fee=-0.1, timestamp=_TS)


def test_position_defaults_to_flat() -> None:
    pos = Position(symbol="BTCUSDT")
    assert pos.is_flat is True
    assert pos.quantity == 0.0


def test_position_not_flat_with_quantity() -> None:
    pos = Position(symbol="BTCUSDT", quantity=0.1, avg_price=100.0)
    assert pos.is_flat is False
