"""Event-driven backtest engine."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

import structlog

from stratforge.config import BacktestConfig
from stratforge.metrics import (
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    total_return,
    win_rate,
)
from stratforge.portfolio import Portfolio
from stratforge.schemas import Bar, Fill, Order, OrderType, Side
from stratforge.strategy import PortfolioView, Strategy

logger = structlog.get_logger(__name__)


@dataclass
class BacktestResult:
    """Final report from a backtest run."""

    initial_capital: float
    final_equity: float
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int
    fills: list[Fill] = field(default_factory=list)
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)

    def to_dict(self) -> dict[str, float | int]:
        """Flatten for JSON serialization."""
        return {
            "initial_capital": self.initial_capital,
            "final_equity": self.final_equity,
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "num_trades": self.num_trades,
        }


class BacktestEngine:
    """Event-driven backtest engine.

    Replays bars one at a time. At each bar:

    1. Build a PortfolioView snapshot (never leaks future data).
    2. Ask the strategy for orders.
    3. Execute orders at the bar close with fees and slippage.
    4. Mark-to-market the portfolio.

    All trades use the CURRENT bar close — no look-ahead.
    """

    def __init__(self, config: BacktestConfig) -> None:
        self._config = config

    def run(self, bars: Iterable[Bar], strategy: Strategy) -> BacktestResult:
        portfolio = Portfolio(cash=self._config.initial_capital)
        last_prices: dict[str, float] = {}
        equity_curve: list[tuple[datetime, float]] = []
        all_fills: list[Fill] = []

        strategy.on_start()
        try:
            for bar in bars:
                last_prices[bar.symbol] = bar.close
                equity = portfolio.equity(last_prices)

                view = PortfolioView(
                    timestamp=bar.timestamp,
                    cash=portfolio.cash,
                    positions=dict(portfolio.positions),
                    last_prices=dict(last_prices),
                    equity=equity,
                )

                orders = strategy.on_bar(bar, view)
                for order in orders:
                    fill = self._execute(order, bar)
                    if fill is None:
                        continue
                    portfolio.apply_fill(fill)
                    all_fills.append(fill)

                equity_curve.append((bar.timestamp, portfolio.equity(last_prices)))
        finally:
            strategy.on_end()

        return self._build_result(portfolio, last_prices, equity_curve, all_fills)

    def _execute(self, order: Order, bar: Bar) -> Fill | None:
        """Convert an order to a fill, applying fees and slippage.

        MARKET orders always fill at close +/- slippage. LIMIT orders fill
        only if the bar range crosses the limit price.
        """
        if order.symbol != bar.symbol:
            logger.warning(
                "engine.order_symbol_mismatch",
                order_symbol=order.symbol,
                bar_symbol=bar.symbol,
            )
            return None

        if order.order_type is OrderType.LIMIT:
            if order.limit_price is None:
                return None
            if order.side is Side.BUY and order.limit_price < bar.low:
                return None
            if order.side is Side.SELL and order.limit_price > bar.high:
                return None
            base_price = order.limit_price
        else:
            base_price = bar.close

        fill_price = self._apply_slippage(base_price, order.side)
        notional = fill_price * order.quantity
        fee = notional * self._config.fee_rate

        return Fill(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            fee=fee,
            timestamp=bar.timestamp,
        )

    def _apply_slippage(self, price: float, side: Side) -> float:
        """Adverse slippage: buys pay more, sells receive less."""
        slip = self._config.slippage_rate
        return price * (1.0 + slip) if side is Side.BUY else price * (1.0 - slip)

    def _build_result(
        self,
        portfolio: Portfolio,
        last_prices: dict[str, float],
        equity_curve: list[tuple[datetime, float]],
        fills: list[Fill],
    ) -> BacktestResult:
        values = [v for _, v in equity_curve]
        if not values:
            values = [self._config.initial_capital]

        # Per-trade PnL approximated as the notional change from each fill.
        # For a single-symbol long-only strategy this matches realized+unrealized.
        trade_pnls = self._compute_trade_pnls(fills)

        return BacktestResult(
            initial_capital=self._config.initial_capital,
            final_equity=values[-1],
            total_return=total_return(values),
            sharpe_ratio=sharpe_ratio(values),
            sortino_ratio=sortino_ratio(values),
            max_drawdown=max_drawdown(values),
            win_rate=win_rate(trade_pnls),
            profit_factor=profit_factor(trade_pnls),
            num_trades=len(fills),
            fills=fills,
            equity_curve=equity_curve,
        )

    @staticmethod
    def _compute_trade_pnls(fills: list[Fill]) -> list[float]:
        """Approximate realized PnL by pairing buys and sells FIFO per symbol."""
        open_lots: dict[str, list[tuple[float, float]]] = {}
        pnls: list[float] = []

        for fill in fills:
            lots = open_lots.setdefault(fill.symbol, [])
            remaining = fill.quantity

            if fill.side is Side.BUY:
                lots.append((fill.price, fill.quantity))
                continue

            # SELL: consume from oldest lots FIFO.
            while remaining > 1e-12 and lots:
                entry_price, entry_qty = lots[0]
                matched = min(remaining, entry_qty)
                pnl = (fill.price - entry_price) * matched - fill.fee * (matched / fill.quantity)
                pnls.append(pnl)
                remaining -= matched
                if entry_qty - matched < 1e-12:
                    lots.pop(0)
                else:
                    lots[0] = (entry_price, entry_qty - matched)

        return pnls
