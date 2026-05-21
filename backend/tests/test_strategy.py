"""
test_strategy.py
Unit tests for core RSI logic and signal generation.
No network calls, no database — pure math tests.
"""
import math
import numpy as np
import pandas as pd
import pytest

from core.strategy import (
    BotConfig, calc_rsi, get_signal,
    stop_price, take_profit_price, position_size,
)

SYMBOL = "AAPL"


def make_cfg(**kwargs) -> BotConfig:
    """Create a BotConfig with sensible defaults, overridable via kwargs."""
    defaults = dict(
        symbol=SYMBOL, rsi_period=14, oversold=30.0, overbought=70.0,
        stop_loss_pct=5.0, take_profit_pct=10.0, risk_per_trade_pct=2.0,
    )
    defaults.update(kwargs)
    return BotConfig(**defaults)


def make_prices(n: int = 30, start: float = 100.0, step: float = 1.0) -> pd.Series:
    """Generate a monotonically increasing price series."""
    return pd.Series([start + i * step for i in range(n)])


# ── calc_rsi ────────────────────────────────────────────────────────────────

def test_rsi_returns_correct_length():
    """RSI output must have the same length as the input."""
    prices = make_prices(30)
    rsi = calc_rsi(prices, 14)
    assert len(rsi) == len(prices)


def test_rsi_first_n_values_are_nan():
    """First `period` values of RSI must be NaN."""
    prices = make_prices(30)
    rsi = calc_rsi(prices, 14)
    assert all(math.isnan(v) for v in rsi.iloc[:14])


def test_rsi_values_in_valid_range():
    """All non-NaN RSI values must be between 0 and 100."""
    prices = make_prices(30)
    rsi = calc_rsi(prices, 14)
    valid = rsi.dropna()
    assert all(0 <= v <= 100 for v in valid)


def test_rsi_too_short_series_all_nan():
    """RSI on a series shorter than period+1 must return all NaN."""
    prices = make_prices(5)
    rsi = calc_rsi(prices, 14)
    assert all(math.isnan(v) for v in rsi)


def test_rsi_constant_prices_returns_nan_or_50():
    """Flat prices produce 0 loss → RSI should be 100 or NaN (no movement)."""
    prices = pd.Series([100.0] * 30)
    rsi = calc_rsi(prices, 14)
    valid = rsi.dropna()
    # When avg_loss == 0 we return 100; all valid values must be 100 or nan
    assert all(v == 100.0 or math.isnan(v) for v in rsi)


# ── get_signal ───────────────────────────────────────────────────────────────

def test_rsi_oversold_gives_buy():
    """RSI at 28 (below oversold=30) must produce BUY."""
    cfg = make_cfg(oversold=30.0)
    assert get_signal(28.0, cfg) == "BUY"


def test_rsi_overbought_gives_sell():
    """RSI at 72 (above overbought=70) must produce SELL."""
    cfg = make_cfg(overbought=70.0)
    assert get_signal(72.0, cfg) == "SELL"


def test_rsi_neutral_gives_hold():
    """RSI at 50 (between thresholds) must produce HOLD."""
    cfg = make_cfg(oversold=30.0, overbought=70.0)
    assert get_signal(50.0, cfg) == "HOLD"


def test_get_signal_nan_gives_hold():
    """NaN RSI must produce HOLD (not crash)."""
    cfg = make_cfg()
    assert get_signal(float("nan"), cfg) == "HOLD"


def test_get_signal_at_exact_oversold_threshold():
    """RSI exactly at oversold threshold must produce BUY."""
    cfg = make_cfg(oversold=30.0)
    assert get_signal(30.0, cfg) == "BUY"


def test_get_signal_at_exact_overbought_threshold():
    """RSI exactly at overbought threshold must produce SELL."""
    cfg = make_cfg(overbought=70.0)
    assert get_signal(70.0, cfg) == "SELL"


# ── stop_price / take_profit_price ──────────────────────────────────────────

def test_stop_price_is_below_entry():
    """Stop loss price must always be below the entry price."""
    cfg = make_cfg(stop_loss_pct=5.0)
    assert stop_price(200.0, cfg) < 200.0


def test_take_profit_price_is_above_entry():
    """Take profit price must always be above the entry price."""
    cfg = make_cfg(take_profit_pct=10.0)
    assert take_profit_price(200.0, cfg) > 200.0


def test_stop_price_value():
    """Stop loss at 5% of $200 entry must be $190."""
    cfg = make_cfg(stop_loss_pct=5.0)
    assert stop_price(200.0, cfg) == pytest.approx(190.0, rel=1e-4)


def test_take_profit_price_value():
    """Take profit at 10% of $200 entry must be $220."""
    cfg = make_cfg(take_profit_pct=10.0)
    assert take_profit_price(200.0, cfg) == pytest.approx(220.0, rel=1e-4)


# ── position_size ────────────────────────────────────────────────────────────

def test_position_size_zero_when_no_capital():
    """Zero account value must return 0 shares."""
    cfg = make_cfg(risk_per_trade_pct=2.0, stop_loss_pct=5.0)
    assert position_size(0.0, 100.0, cfg) == 0


def test_position_size_respects_risk_pct():
    """
    2% risk on $10,000 = $200 risk budget.
    5% stop on $100 entry = $5 per-share risk.
    => 200/5 = 40 shares.
    """
    cfg = make_cfg(risk_per_trade_pct=2.0, stop_loss_pct=5.0)
    assert position_size(10_000.0, 100.0, cfg) == 40


def test_position_size_never_negative():
    """Position size must never return a negative value."""
    cfg = make_cfg(risk_per_trade_pct=2.0, stop_loss_pct=5.0)
    assert position_size(50.0, 100.0, cfg) >= 0


def test_position_size_returns_int():
    """Position size must always be an integer (whole shares)."""
    cfg = make_cfg()
    result = position_size(10_000.0, 150.0, cfg)
    assert isinstance(result, int)
