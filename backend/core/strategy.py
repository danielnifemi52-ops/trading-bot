"""
strategy.py
Pure RSI calculation and signal generation.
No I/O, no side effects. Fully testable in isolation.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Literal, Optional
from datetime import datetime

Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass
class BotConfig:
    """All tunable parameters for one bot instance."""
    symbol: str
    rsi_period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    risk_per_trade_pct: float = 2.0
    poll_interval_seconds: int = 300


@dataclass
class TradeRecord:
    """One completed or open trade."""
    symbol: str
    side: Literal["BUY", "SELL"]
    price: float
    qty: int
    rsi_at_signal: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    pnl: Optional[float] = None
    exit_reason: Optional[str] = None


def calc_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Wilder's smoothed RSI. Matches TradingView default.
    Returns NaN for first `period` bars.
    """
    if len(prices) < period + 1:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.iloc[:period].mean()
    avg_loss = loss.iloc[:period].mean()
    rsi_vals: list[float] = [np.nan] * period
    for i in range(period, len(prices)):
        avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period
        if avg_loss == 0:
            rsi_val = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100.0 - (100.0 / (1.0 + rs))
        rsi_vals.append(round(rsi_val, 4))
    return pd.Series(rsi_vals, index=prices.index)


def get_signal(rsi_value: float, cfg: BotConfig) -> Signal:
    """Map a single RSI float to BUY / SELL / HOLD."""
    if np.isnan(rsi_value):
        return "HOLD"
    if rsi_value <= cfg.oversold:
        return "BUY"
    if rsi_value >= cfg.overbought:
        return "SELL"
    return "HOLD"


def stop_price(entry: float, cfg: BotConfig) -> float:
    """Price at which stop loss triggers."""
    return round(entry * (1 - cfg.stop_loss_pct / 100), 4)


def take_profit_price(entry: float, cfg: BotConfig) -> float:
    """Price at which take profit triggers."""
    return round(entry * (1 + cfg.take_profit_pct / 100), 4)


def position_size(account_value: float, entry: float, cfg: BotConfig) -> int:
    """
    Risk-based position sizing.
    Never risks more than cfg.risk_per_trade_pct% of account on a single trade.
    Returns 0 if calculation produces invalid result.
    """
    risk_dollars = account_value * (cfg.risk_per_trade_pct / 100)
    per_share_risk = entry * (cfg.stop_loss_pct / 100)
    if per_share_risk <= 0:
        return 0
    return max(int(risk_dollars / per_share_risk), 0)
