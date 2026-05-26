"""
backtester.py
Walk-forward backtester. Downloads historical OHLCV data, simulates the RSI
strategy trade by trade, and returns a BacktestResponse.
Uses Alpaca for crypto and stock intraday bars; yfinance for daily/weekly stocks.
No database access.
"""
from __future__ import annotations
import logging
import os
import time
import math

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
import numpy as np
import pandas as pd
import yfinance as yf

from core.strategy import (
    BotConfig,
    calc_rsi,
    get_signal,
    position_size,
    stop_price,
    take_profit_price,
)
from models import BacktestRequest, BacktestResponse, TradeStats
from services.broker import is_crypto

log = logging.getLogger(__name__)

INTRADAY_INTERVALS = {"1h", "15m", "5m"}
YFINANCE_INTERVALS = {"1d", "1wk"}
SUPPORTED_INTERVALS = INTRADAY_INTERVALS | YFINANCE_INTERVALS


def download_alpaca(symbol: str, start: str, end: str, interval: str) -> pd.DataFrame:
    """Download intraday OHLCV bars from Alpaca."""
    api_key = os.environ.get("ALPACA_KEY")
    secret_key = os.environ.get("ALPACA_SECRET")
    if not api_key or not secret_key:
        raise ValueError(
            "ALPACA_KEY and ALPACA_SECRET must be set for intraday backtests."
        )

    client = StockHistoricalDataClient(api_key, secret_key)
    tf_map = {
        "1h": TimeFrame.Hour,
        "15m": TimeFrame(15, TimeFrameUnit.Minute),
        "5m": TimeFrame(5, TimeFrameUnit.Minute),
    }
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=tf_map[interval],
        start=start,
        end=end,
    )
    bars = client.get_stock_bars(req)
    df = getattr(bars, "df", pd.DataFrame())
    if df.empty:
        return df
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index(level=0, drop=True)
    df.columns = [c.capitalize() for c in df.columns]
    return df


def download_crypto_alpaca(
    symbol: str,
    start: str,
    end: str,
    interval: str,
) -> pd.DataFrame:
    """Download crypto OHLCV bars from Alpaca."""
    api_key = os.environ.get("ALPACA_KEY")
    secret_key = os.environ.get("ALPACA_SECRET")
    if not api_key or not secret_key:
        raise ValueError(
            "ALPACA_KEY and ALPACA_SECRET must be set for crypto backtests."
        )

    from alpaca.data.historical.crypto import CryptoHistoricalDataClient
    from alpaca.data.requests import CryptoBarsRequest

    tf_map = {
        "1d": TimeFrame.Day,
        "1h": TimeFrame.Hour,
        "15m": TimeFrame(15, TimeFrameUnit.Minute),
        "5m": TimeFrame(5, TimeFrameUnit.Minute),
    }
    if hasattr(TimeFrame, "Week"):
        tf_map["1wk"] = TimeFrame.Week

    if interval not in tf_map:
        raise ValueError(
            f"Unsupported interval '{interval}' for crypto. Use one of: "
            f"{', '.join(sorted(tf_map))}."
        )

    client = CryptoHistoricalDataClient(
        api_key=api_key,
        secret_key=secret_key,
    )
    req = CryptoBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=tf_map[interval],
        start=start,
        end=end,
    )
    bars = client.get_crypto_bars(req)
    df = getattr(bars, "df", pd.DataFrame())
    if df.empty:
        return df
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index(level=0, drop=True)
    df.columns = [c.capitalize() for c in df.columns]
    return df


def download_with_retry(
    symbol: str,
    start: str,
    end: str,
    interval: str,
    retries: int = 2,
) -> pd.DataFrame:
    """Download OHLCV. Uses Alpaca for intraday, yfinance for daily and above."""
    if is_crypto(symbol):
        return download_crypto_alpaca(symbol, start, end, interval)

    if interval in INTRADAY_INTERVALS:
        return download_alpaca(symbol, start, end, interval)
    if interval not in YFINANCE_INTERVALS:
        raise ValueError(
            f"Unsupported interval '{interval}'. Use one of: "
            f"{', '.join(sorted(SUPPORTED_INTERVALS))}."
        )

    df = pd.DataFrame()
    for attempt in range(retries):
        df = yf.download(
            symbol,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        if not df.empty:
            return df
        if attempt < retries - 1:
            log.warning("yfinance returned empty; retrying in 3s")
            time.sleep(3)
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
    Raises ValueError if no data is returned by the selected market data provider.
    """
    df = download_with_retry(req.symbol, req.start, req.end, req.interval)
    if df.empty:
        provider = "Alpaca" if is_crypto(req.symbol) or req.interval in INTRADAY_INTERVALS else "yfinance"
        raise ValueError(
            f"No data returned from {provider} for {req.symbol} between "
            f"{req.start} and {req.end}. "
            "Check the symbol and date range."
        )

    prices: pd.Series = df["Close"].squeeze().dropna()
    crypto = is_crypto(req.symbol)

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
            qty = position_size(capital, price, cfg, crypto=crypto)
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
