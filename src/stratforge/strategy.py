"""Strategy abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from stratforge.schemas import Bar, Order, Position


class PortfolioView(BaseModel):
    """Read-only snapshot of portfolio state passed to a strategy.

    Strategies must not mutate this object. Orders are returned from
    on_bar; the engine applies them.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    cash: float
    positions: dict[str, Position]
    last_prices: dict[str, float]
    equity: float

    def position_for(self, symbol: str) -> Position:
        """Return current position for the symbol, or a flat one."""
        return self.positions.get(symbol, Position(symbol=symbol))


class Strategy(ABC):
    """Abstract strategy contract.

    Lifecycle: on_start -> on_bar (many) -> on_end.
    """

    def __init__(self, symbols: list[str]) -> None:
        if not symbols:
            msg = "Strategy requires at least one symbol"
            raise ValueError(msg)
        self._symbols = list(symbols)

    @property
    def symbols(self) -> list[str]:
        return list(self._symbols)

    def on_start(self) -> None:  # noqa: B027
        """Optional hook called once before the first bar."""

    def on_end(self) -> None:  # noqa: B027
        """Optional hook called once after the last bar."""

    @abstractmethod
    def on_bar(self, bar: Bar, view: PortfolioView) -> list[Order]:
        """Return zero or more orders to execute on this bar."""
        raise NotImplementedError
