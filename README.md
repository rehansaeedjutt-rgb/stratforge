# stratforge

> An event-driven crypto strategy backtester with honest metrics.

[![CI](https://github.com/rehansaeedjutt-rgb/stratforge/actions/workflows/ci.yml/badge.svg)](https://github.com/rehansaeedjutt-rgb/stratforge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen.svg)](#testing)

## Overview

`stratforge` replays historical OHLCV data through a strategy, simulates order
fills with realistic transaction costs and slippage, and reports risk-adjusted
performance. The design goal is **honesty over hype**: the engine does not
cheat, look ahead, or hide costs.

**Status:** Phase 1 complete — event loop, cost model, metrics, CLI, example strategy.

## Why this project exists

Most backtesters quietly lie. They report returns before fees, ignore slippage,
leak future data into decisions, or overfit on a single train/test split. Each
of these turns a losing strategy into a winner on paper.

`stratforge` is built the opposite way:

- **Costs are explicit** — fees and slippage are in basis points, applied on every fill.
- **No look-ahead** — strategies see a `PortfolioView` snapshot with only past + current bar.
- **Risk-adjusted metrics** — Sharpe, Sortino, max drawdown, win rate, profit factor.
- **Honest by default** — every report ends with the disclaimer that a backtest is not a forecast.

## Live demo

Clone, install, and run a backtest on the bundled sample data:

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m stratforge backtest --csv examples/btcusdt_sample.csv --symbol BTCUSDT --fast 5 --slow 20
```

Example output:

```
Backtest: BTCUSDT
  Bars:            120
  Initial capital: 10000.00
  Final equity:    9997.33
  Total return:    -0.03%
  Sharpe:          -0.476
  Sortino:         -0.657
  Max drawdown:    -0.12%
  Win rate:        33.3%
  Profit factor:   0.081
  Trades:          6

Backtest results are NOT indicative of future returns.
```

Yes, the example loses money. A moving-average crossover on a sine wave, net of
fees, should lose money. That is what a correct backtester reports.

## Architecture

```
CSV / future: tickstream DB
        |
        v
   [ Bar stream ]
        |
        v
  +------------------------+
  |    BacktestEngine      |
  |------------------------|
  |  for each bar:         |
  |   1. update last_prices|
  |   2. build PortfolioView (snapshot)
  |   3. strategy.on_bar -> orders
  |   4. _execute -> Fill (fees + slippage)
  |   5. portfolio.apply_fill
  |   6. record equity     |
  +------------------------+
        |
        v
   [ BacktestResult ] -> metrics -> report
```

### Design choices

| Choice | Why |
|--------|-----|
| Event-driven, one bar at a time | Structural defense against look-ahead bias |
| `PortfolioView` is frozen (`ConfigDict(frozen=True)`) | Strategies cannot mutate state |
| Fees and slippage in **basis points** | Makes cost-of-trading comparisons apples-to-apples |
| `Decimal`-free prices in bar data | Backtests are estimates; float is fine and fast |
| `profit_factor = inf` when no losses | Mathematically honest, not a fake `100.0` |
| `sortino_ratio = inf` when no downside | Same reason |

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| Data | `pandas`, `numpy` |
| Schemas | `pydantic` v2 |
| Config | `pydantic-settings` |
| Logging | `structlog` |
| Testing | `pytest` |
| Quality | `ruff`, `mypy --strict` |
| CI | GitHub Actions on Python 3.12 / 3.13 / 3.14 |

## Project structure

```
stratforge/
├── src/stratforge/
│   ├── config.py               # BacktestConfig (capital, fees, slippage)
│   ├── schemas.py              # Bar, Order, Fill, Position, Side
│   ├── engine.py               # BacktestEngine, BacktestResult
│   ├── portfolio.py            # Portfolio state, fills, mark-to-market
│   ├── metrics.py              # Sharpe, Sortino, drawdown, win rate, profit factor
│   ├── strategy.py             # Strategy ABC, PortfolioView
│   └── strategies/
│       └── sma_crossover.py    # Reference strategy (long-only SMA crossover)
├── tests/unit/                 # 52 unit tests
├── examples/btcusdt_sample.csv # Deterministic OHLCV sample
├── pyproject.toml
└── README.md
```

## Development

```
ruff check .
ruff format --check .
mypy src
pytest --cov=src/stratforge --cov-report=term-missing
```

## Testing

52 unit tests, all offline (no network), covering:

- Config validation and bps conversion
- Bar/Order/Fill/Position schema invariants
- Portfolio cash and position accounting
- Engine: slippage, fees, equity curve, no-look-ahead guarantee
- Metrics: Sharpe, Sortino, drawdown, win rate, profit factor
- SMA crossover end-to-end smoke test

| Module | Coverage |
|--------|----------|
| `config.py` | 100% |
| `schemas.py` | 100% |
| `metrics.py` | 97% |
| `portfolio.py` | 95% |
| `engine.py` | 80% |
| `strategies/sma_crossover.py` | 82% |
| **Total** | **89%** |

## Roadmap

- [x] Phase 1 — Event loop, cost model, metrics, CLI, SMA example
- [ ] Phase 2 — Walk-forward validation harness
- [ ] Phase 3 — Additional strategies (mean reversion, momentum)
- [ ] Phase 4 — Integration with [tickstream](https://github.com/rehansaeedjutt-rgb/tickstream) SQLite DB
- [ ] Phase 5 — HTML/JSON report generation

## Limitations

- Only supports single-symbol strategies today.
- No short selling yet (`allow_short` flag reserved for later).
- Fill model is simple (bar close +/- slippage); no order book simulation.
- Sample data is deterministic, not real market data — the goal is engine verification, not edge discovery.

## Disclaimer

**Backtest results are not indicative of future returns.** This project makes no
guarantee of trading performance. It is a research tool, not financial advice.

## License

MIT - see [LICENSE](LICENSE) file.

## Author

**Muhammad Rehan Saeed** - [GitHub](https://github.com/rehansaeedjutt-rgb)
