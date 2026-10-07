"""Simple SMA-crossover example strategy.

Long-only: buy when fast SMA crosses above slow SMA, sell when it
crosses below. Serves as a runnable example and a test fixture.
"""

from __future__ import annotations

from collections import deque

from stratforge.schemas import Bar, Order, Side
from stratforge.strategy import PortfolioView, Strategy


class SmaCrossoverStrategy(Strategy):
    """Long-only SMA crossover on a single symbol."""

    def __init__(
        self,
        symbol: str,
        fast_window: int = 5,
        slow_window: int = 20,
        position_size: float = 1.0,
    ) -> None:
        super().__init__([symbol])
        if fast_window < 1 or slow_window < 2:
            msg = "fast_window must be >= 1 and slow_window >= 2"
            raise ValueError(msg)
        if fast_window >= slow_window:
            msg = "fast_window must be smaller than slow_window"
            raise ValueError(msg)
        if position_size <= 0:
            msg = "position_size must be positive"
            raise ValueError(msg)

        self._symbol = symbol
        self._fast_window = fast_window
        self._slow_window = slow_window
        self._position_size = position_size
        self._prices: deque[float] = deque(maxlen=slow_window)
        self._prev_fast: float | None = None
        self._prev_slow: float | None = None

    def on_bar(self, bar: Bar, view: PortfolioView) -> list[Order]:
        if bar.symbol != self._symbol:
            return []

        self._prices.append(bar.close)
        if len(self._prices) < self._slow_window:
            return []

        prices = list(self._prices)
        fast = sum(prices[-self._fast_window :]) / self._fast_window
        slow = sum(prices) / self._slow_window

        orders: list[Order] = []
        position = view.position_for(self._symbol)

        if self._prev_fast is not None and self._prev_slow is not None:
            crossed_up = self._prev_fast <= self._prev_slow and fast > slow
            crossed_down = self._prev_fast >= self._prev_slow and fast < slow

            if crossed_up and position.is_flat:
                orders.append(
                    Order(
                        symbol=self._symbol,
                        side=Side.BUY,
                        quantity=self._position_size,
                        timestamp=bar.timestamp,
                    )
                )
            elif crossed_down and not position.is_flat and position.quantity > 0:
                orders.append(
                    Order(
                        symbol=self._symbol,
                        side=Side.SELL,
                        quantity=abs(position.quantity),
                        timestamp=bar.timestamp,
                    )
                )

        self._prev_fast = fast
        self._prev_slow = slow
        return orders
