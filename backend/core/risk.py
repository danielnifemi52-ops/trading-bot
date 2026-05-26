"""
risk.py
Risk management helpers used by the bot runner and backtester.
"""
from __future__ import annotations
from core.strategy import BotConfig, stop_price, take_profit_price


def should_stop_loss(current_price: float, entry_price: float, cfg: BotConfig) -> bool:
    """Return True if current price has hit or crossed the stop loss level."""
    return current_price <= stop_price(entry_price, cfg)


def should_take_profit(current_price: float, entry_price: float, cfg: BotConfig) -> bool:
    """Return True if current price has hit or crossed the take profit level."""
    return current_price >= take_profit_price(entry_price, cfg)


def unrealised_pnl(current_price: float, entry_price: float, qty: float) -> float:
    """Calculate unrealised P&L for an open long position."""
    return round((current_price - entry_price) * qty, 4)
