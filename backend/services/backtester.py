"""
backtester.py
Walk-forward backtester. Downloads historical OHLCV data via yfinance,
simulates the RSI strategy trade by trade, and returns a BacktestResponse.
No network calls other than yfinance. No database access.
"""
from __future__ import annotations
import logging
import time
import math
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

from core.strategy import BotConfig, calc_rsi, get_signal, stop_price, take_profit_price
from models import BacktestRequest, BacktestResponse, TradeStats

log = logging.getLogger(__name__)


def _download_with_retry(symbol: str, start: str, end: str, interval: str) -> pd.DataFrame:
    """Download OHLCV with one retry on empty response (yfinance rate limiting)."""
    for attempt in range(2):
        df = yf.download(symbol, start=start, end=end, interval=interval,
                         auto_adjust=True, progress=False)
        if not df.empty:
            return df
        if attempt == 0:
            log.warning("yfinance returned empty — waiting 60s and retrying")
            time.sleep(60)
    return df


def _compute_stats(trades: list[dict], equity_curve: list[float], start_capital: float) -> TradeStats:
    """Compute aggregate statistics from a completed backtest."""
    if not trades:
        return TradeStats(
            total_trades=0, win_rate=0.0, total_pnl=0.0,
            avg_win=0.0, avg_loss=0.0, profit_factor=0.0,
            max_drawdown_pct=0.0, sharpe_ratio=0.0,
        )

    pnls = [t["pnl"] for t in trades if t.get("pnl") is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / len(pnls) if pnls else 0.0
    total_pnl = sum(pnls)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else 0.0

    # Max drawdown
    peak = start_capital
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio (annualised, daily returns, risk-free = 0)
    if len(equity_curve) > 1:
        returns = pd.Series(equity_curve).pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * math.sqrt(252)) if returns.std() > 0 else 0.0
    else:
        sharpe = 0.0

    return TradeStats(
        total_trades=len(pnls),
        win_rate=round(win_rate, 4),
        total_pnl=round(total_pnl, 2),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        profit_factor=round(profit_factor, 4),
        max_drawdown_pct=round(max_dd, 2),
        sharpe_ratio=round(sharpe, 4),
    )


def run_backtest(req: BacktestRequest) -> BacktestResponse:
    """
    Run a full walk-forward backtest for the given parameters.
    Returns a BacktestResponse with stats, trade list, and equity curve.
    Raises ValueError if no data is returned by yfinance.
    """
    df = _download_with_retry(req.symbol, req.start, req.end, req.interval)
    if df.empty:
        raise ValueError(f"No price data for {req.symbol} between {req.start} and {req.end}")

    prices: pd.Series = df["Close"].squeeze().dropna()

    cfg = BotConfig(
        symbol=req.symbol,
        rsi_period=req.rsi_period,
        oversold=req.oversold,
        overbought=req.overbought,
        stop_loss_pct=req.stop_loss_pct,
        take_profit_pct=req.take_profit_pct,
    )

    rsi_series = calc_rsi(prices, cfg.rsi_period)
    capital = req.start_capital
    position: dict | None = None
    trades: list[dict] = []
    equity_curve: list[dict] = []
    prev_signal = "HOLD"

    for i, (date, price) in enumerate(prices.items()):
        price = float(price)
        rsi = float(rsi_series.iloc[i])
        signal = get_signal(rsi, cfg)
        date_str = str(date)[:10]

        # Check stop loss / take profit on open position
        if position:
            sl = stop_price(position["entry"], cfg)
            tp = take_profit_price(position["entry"], cfg)

            exit_reason = None
            if price <= sl:
                exit_reason = "STOP_LOSS"
            elif price >= tp:
                exit_reason = "TAKE_PROFIT"
            elif signal == "SELL" and prev_signal != "SELL":
                exit_reason = "RSI_SIGNAL"

            if exit_reason:
                pnl = (price - position["entry"]) * position["qty"]
                capital += pnl
                trades.append({
                    "date": date_str,
                    "symbol": req.symbol,
                    "side": "SELL",
                    "entry": position["entry"],
                    "exit": price,
                    "qty": position["qty"],
                    "pnl": round(pnl, 2),
                    "rsi": round(rsi, 2),
                    "exit_reason": exit_reason,
                })
                position = None

        # Open new position on BUY signal
        if signal == "BUY" and position is None and prev_signal != "BUY":
            risk_dollars = capital * (cfg.risk_per_trade_pct / 100)
            per_share_risk = price * (cfg.stop_loss_pct / 100)
            qty = int(risk_dollars / per_share_risk) if per_share_risk > 0 else 0
            if qty > 0:
                position = {"entry": price, "qty": qty, "date": date_str, "rsi": round(rsi, 2)}

        equity_val = capital
        if position:
            equity_val = capital + (price - position["entry"]) * position["qty"]
        equity_curve.append({"date": date_str, "value": round(equity_val, 2)})

        prev_signal = signal

    # Close any remaining open position at last price
    if position and len(prices) > 0:
        last_price = float(prices.iloc[-1])
        pnl = (last_price - position["entry"]) * position["qty"]
        capital += pnl
        trades.append({
            "date": str(prices.index[-1])[:10],
            "symbol": req.symbol,
            "side": "SELL",
            "entry": position["entry"],
            "exit": last_price,
            "qty": position["qty"],
            "pnl": round(pnl, 2),
            "rsi": float(rsi_series.iloc[-1]),
            "exit_reason": "END_OF_DATA",
        })

    equity_values = [e["value"] for e in equity_curve]
    stats = _compute_stats(trades, equity_values, req.start_capital)

    return BacktestResponse(
        symbol=req.symbol,
        start=req.start,
        end=req.end,
        stats=stats,
        trades=trades,
        equity_curve=equity_curve,
    )
