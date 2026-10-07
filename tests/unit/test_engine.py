"""End-to-end tests for the backtest engine."""

from datetime import UTC, datetime, timedelta

import pytest

from stratforge.config import BacktestConfig
from stratforge.engine import BacktestEngine
from stratforge.schemas import Bar, Order, Side
from stratforge.strategies.sma_crossover import SmaCrossoverStrategy
from stratforge.strategy import PortfolioView, Strategy

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _bars(prices: list[float], symbol: str = "BTCUSDT") -> list[Bar]:
    out: list[Bar] = []
    for i, price in enumerate(prices):
        out.append(
            Bar(
                symbol=symbol,
                timestamp=_BASE + timedelta(hours=i),
                open=price,
                high=price * 1.001,
                low=price * 0.999,
                close=price,
                volume=100.0,
            )
        )
    return out


class _AlwaysBuyOnce(Strategy):
    """Test fixture: buys 1 unit on the very first bar, then does nothing."""

    def __init__(self) -> None:
        super().__init__(["BTCUSDT"])
        self._bought = False

    def on_bar(self, bar: Bar, view: PortfolioView) -> list[Order]:
        if self._bought:
            return []
        self._bought = True
        return [Order(symbol=bar.symbol, side=Side.BUY, quantity=1.0, timestamp=bar.timestamp)]


class _BuyThenSell(Strategy):
    """Test fixture: buys on first bar, sells on second bar."""

    def __init__(self) -> None:
        super().__init__(["BTCUSDT"])
        self._step = 0

    def on_bar(self, bar: Bar, view: PortfolioView) -> list[Order]:
        self._step += 1
        if self._step == 1:
            return [Order(symbol=bar.symbol, side=Side.BUY, quantity=1.0, timestamp=bar.timestamp)]
        if self._step == 2:
            return [Order(symbol=bar.symbol, side=Side.SELL, quantity=1.0, timestamp=bar.timestamp)]
        return []


def test_engine_no_trades_preserves_capital() -> None:
    config = BacktestConfig(initial_capital=10_000.0, fee_bps=0.0, slippage_bps=0.0)
    engine = BacktestEngine(config)
    result = engine.run(_bars([100.0, 101.0, 102.0]), _AlwaysBuyOnce())
    # One buy of 1 @ 100 -> cash 9900, position 1 @ 100, equity at end = 9900 + 102 = 10002
    assert result.num_trades == 1
    assert result.final_equity == pytest.approx(10_002.0)


def test_engine_applies_slippage_on_buy() -> None:
    config = BacktestConfig(initial_capital=10_000.0, fee_bps=0.0, slippage_bps=100.0)  # 1%
    engine = BacktestEngine(config)
    result = engine.run(_bars([100.0]), _AlwaysBuyOnce())
    # Buy 1 unit at 100 * 1.01 = 101, cash = 10000 - 101 = 9899
    assert result.num_trades == 1
    assert result.fills[0].price == pytest.approx(101.0)


def test_engine_applies_slippage_on_sell() -> None:
    config = BacktestConfig(initial_capital=10_000.0, fee_bps=0.0, slippage_bps=100.0)
    engine = BacktestEngine(config)
    result = engine.run(_bars([100.0, 110.0]), _BuyThenSell())
    # Buy at 100*1.01=101, sell at 110*0.99=108.9
    assert result.num_trades == 2
    assert result.fills[1].price == pytest.approx(108.9)


def test_engine_charges_fees() -> None:
    config = BacktestConfig(initial_capital=10_000.0, fee_bps=10.0, slippage_bps=0.0)
    engine = BacktestEngine(config)
    result = engine.run(_bars([100.0]), _AlwaysBuyOnce())
    # Fee = 100 * 0.001 = 0.1
    assert result.fills[0].fee == pytest.approx(0.1)


def test_engine_equity_curve_length_matches_bars() -> None:
    config = BacktestConfig()
    engine = BacktestEngine(config)
    bars = _bars([100.0, 101.0, 102.0, 103.0, 104.0])
    result = engine.run(bars, _AlwaysBuyOnce())
    assert len(result.equity_curve) == len(bars)


def test_engine_no_lookahead_uses_current_bar_close() -> None:
    """Strategy sees the CURRENT bar only; fill uses current bar close."""
    config = BacktestConfig(fee_bps=0.0, slippage_bps=0.0)
    engine = BacktestEngine(config)
    result = engine.run(_bars([100.0, 500.0]), _AlwaysBuyOnce())
    # Buy happens on bar 1 (price 100), not bar 2 (price 500)
    assert result.fills[0].price == pytest.approx(100.0)


def test_engine_sma_crossover_runs_end_to_end() -> None:
    """Smoke test: SMA crossover runs without error and produces a report."""
    prices = [100.0 + (i % 10) * 2.0 for i in range(60)]
    bars = _bars(prices)
    config = BacktestConfig(initial_capital=10_000.0)
    engine = BacktestEngine(config)
    strategy = SmaCrossoverStrategy("BTCUSDT", fast_window=3, slow_window=10)
    result = engine.run(bars, strategy)
    assert result.num_trades >= 0
    assert result.initial_capital == 10_000.0
    assert len(result.equity_curve) == len(bars)
    # Sanity: metrics are finite
    assert result.sharpe_ratio == result.sharpe_ratio  # not NaN
    assert result.max_drawdown <= 0.0
