"""Command-line entry point for stratforge."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from stratforge import __version__
from stratforge.config import BacktestConfig
from stratforge.engine import BacktestEngine, BacktestResult
from stratforge.schemas import Bar
from stratforge.strategies.sma_crossover import SmaCrossoverStrategy


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stratforge",
        description="Event-driven crypto strategy backtester.",
    )
    parser.add_argument("--version", action="version", version=f"stratforge {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Run a backtest on a CSV of OHLCV bars.")
    bt.add_argument("--csv", required=True, help="Path to OHLCV CSV file.")
    bt.add_argument("--symbol", required=True, help="Symbol to filter (e.g. BTCUSDT).")
    bt.add_argument("--fast", type=int, default=5, help="Fast SMA window (default: 5).")
    bt.add_argument("--slow", type=int, default=20, help="Slow SMA window (default: 20).")
    bt.add_argument("--capital", type=float, default=10_000.0, help="Initial capital.")
    bt.add_argument("--fee-bps", type=float, default=10.0, help="Fee in bps.")
    bt.add_argument("--slippage-bps", type=float, default=5.0, help="Slippage in bps.")
    bt.add_argument("--json", action="store_true", help="Emit JSON report.")

    return parser


def _load_bars(csv_path: Path, symbol: str) -> list[Bar]:
    """Load OHLCV rows for a single symbol from a CSV.

    Expected columns: symbol, timestamp, open, high, low, close, volume.
    """
    bars: list[Bar] = []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row["symbol"] != symbol:
                continue
            ts_raw = row["timestamp"]
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            bars.append(
                Bar(
                    symbol=row["symbol"],
                    timestamp=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
    return bars


def _print_report(symbol: str, num_bars: int, result: BacktestResult) -> None:
    report = result.to_dict()
    total_return_pct = float(report["total_return"]) * 100.0
    max_dd_pct = float(report["max_drawdown"]) * 100.0
    win_rate_pct = float(report["win_rate"]) * 100.0

    print(f"Backtest: {symbol}")
    print(f"  Bars:            {num_bars}")
    print(f"  Initial capital: {result.initial_capital:.2f}")
    print(f"  Final equity:    {result.final_equity:.2f}")
    print(f"  Total return:    {total_return_pct:.2f}%")
    print(f"  Sharpe:          {result.sharpe_ratio:.3f}")
    print(f"  Sortino:         {result.sortino_ratio:.3f}")
    print(f"  Max drawdown:    {max_dd_pct:.2f}%")
    print(f"  Win rate:        {win_rate_pct:.1f}%")
    print(f"  Profit factor:   {result.profit_factor:.3f}")
    print(f"  Trades:          {result.num_trades}")
    print()
    print("Backtest results are NOT indicative of future returns.")


def _run_backtest(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2

    bars = _load_bars(csv_path, args.symbol)
    if not bars:
        print(f"No bars found for symbol {args.symbol}", file=sys.stderr)
        return 2

    config = BacktestConfig(
        initial_capital=args.capital,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
    )
    strategy = SmaCrossoverStrategy(
        args.symbol,
        fast_window=args.fast,
        slow_window=args.slow,
        position_size=1.0,
    )

    result = BacktestEngine(config).run(bars, strategy)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_report(args.symbol, len(bars), result)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "backtest":
        return _run_backtest(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
