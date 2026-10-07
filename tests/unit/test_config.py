"""Tests for stratforge.config."""

import pytest
from pydantic import ValidationError

from stratforge.config import BacktestConfig


def test_defaults_are_sensible() -> None:
    cfg = BacktestConfig()
    assert cfg.initial_capital == 10_000.0
    assert cfg.fee_bps == 10.0
    assert cfg.slippage_bps == 5.0
    assert cfg.allow_short is False
    assert cfg.max_position_pct == 1.0


def test_fee_rate_converts_bps_to_fraction() -> None:
    cfg = BacktestConfig(fee_bps=10.0)
    assert cfg.fee_rate == pytest.approx(0.001)


def test_slippage_rate_converts_bps_to_fraction() -> None:
    cfg = BacktestConfig(slippage_bps=5.0)
    assert cfg.slippage_rate == pytest.approx(0.0005)


def test_zero_fees_allowed() -> None:
    cfg = BacktestConfig(fee_bps=0.0, slippage_bps=0.0)
    assert cfg.fee_rate == 0.0
    assert cfg.slippage_rate == 0.0


def test_negative_fee_rejected() -> None:
    with pytest.raises(ValidationError):
        BacktestConfig(fee_bps=-1.0)


def test_negative_slippage_rejected() -> None:
    with pytest.raises(ValidationError):
        BacktestConfig(slippage_bps=-1.0)


def test_zero_capital_rejected() -> None:
    with pytest.raises(ValidationError):
        BacktestConfig(initial_capital=0.0)


def test_max_position_pct_upper_bound() -> None:
    with pytest.raises(ValidationError):
        BacktestConfig(max_position_pct=1.5)


def test_max_position_pct_lower_bound() -> None:
    with pytest.raises(ValidationError):
        BacktestConfig(max_position_pct=0.0)
