"""Portfolio state and fill application."""

from __future__ import annotations

from dataclasses import dataclass, field

from stratforge.schemas import Fill, Position, Side


@dataclass
class Portfolio:
    """Tracks cash and positions as fills are applied."""

    cash: float
    positions: dict[str, Position] = field(default_factory=dict)

    def apply_fill(self, fill: Fill) -> None:
        """Update cash and position for a single fill."""
        self.cash -= fill.notional
        self.cash -= fill.fee

        current = self.positions.get(fill.symbol, Position(symbol=fill.symbol))
        signed_qty = fill.quantity if fill.side is Side.BUY else -fill.quantity
        new_qty = current.quantity + signed_qty

        if abs(new_qty) < 1e-12:
            new_avg = 0.0
            new_qty = 0.0
        elif (current.quantity >= 0 and signed_qty > 0) or (
            current.quantity <= 0 and signed_qty < 0
        ):
            total_cost = current.avg_price * abs(current.quantity) + fill.price * fill.quantity
            new_avg = total_cost / abs(new_qty)
        elif (current.quantity > 0 and signed_qty < 0) or (current.quantity < 0 and signed_qty > 0):
            new_avg = current.avg_price if abs(new_qty) > 1e-12 else 0.0
        else:
            new_avg = fill.price

        self.positions[fill.symbol] = Position(
            symbol=fill.symbol,
            quantity=new_qty,
            avg_price=new_avg,
        )

    def equity(self, last_prices: dict[str, float]) -> float:
        """Cash plus mark-to-market value of all open positions."""
        total = self.cash
        for symbol, pos in self.positions.items():
            if pos.is_flat:
                continue
            price = last_prices.get(symbol, pos.avg_price)
            total += pos.quantity * price
        return total
