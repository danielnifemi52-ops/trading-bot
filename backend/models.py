"""
models.py
All SQLModel database models and Pydantic request/response schemas.
SQLModel lets the same class serve as both ORM model and Pydantic schema.
"""
from __future__ import annotations
from typing import Optional, Literal
from datetime import datetime
from sqlmodel import SQLModel, Field


# ── Database models (these create tables) ──────────────────────────────────

class Trade(SQLModel, table=True):
    """Persisted record of every trade the bot executes."""
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str
    side: str                         # "BUY" or "SELL"
    price: float
    qty: float
    rsi_at_signal: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    pnl: Optional[float] = None
    exit_reason: Optional[str] = None  # "RSI_SIGNAL" | "STOP_LOSS" | "TAKE_PROFIT"


class BotLog(SQLModel, table=True):
    """One log line per bot tick — price, RSI, signal, account value."""
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str
    price: float
    rsi: float
    signal: str
    account_value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Request schemas ─────────────────────────────────────────────────────────

class BotConfigRequest(SQLModel):
    """Request body for POST /api/bot/start"""
    symbol: str = "AAPL"
    rsi_period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    risk_per_trade_pct: float = 2.0
    poll_interval_seconds: int = 30
    dry_run: bool = True


class BacktestRequest(SQLModel):
    """Request body for POST /api/backtest/run"""
    symbol: str = "AAPL"
    start: str = "2020-01-01"
    end: str = "2024-01-01"
    interval: str = "1d"
    rsi_period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0
    start_capital: float = 10000.0


class OptimizerRequest(SQLModel):
    """Request body for POST /api/optimizer/run"""
    symbol: str = "AAPL"
    start: str = "2019-01-01"
    end: str = "2023-01-01"
    start_capital: float = 10000.0


# ── Response schemas ────────────────────────────────────────────────────────

class BotStatusResponse(SQLModel):
    """Response for GET /api/bot/status"""
    running: bool
    symbol: Optional[str] = None
    last_price: Optional[float] = None
    last_rsi: Optional[float] = None
    last_signal: Optional[str] = None
    account_value: Optional[float] = None
    open_position: bool = False
    config: Optional[BotConfigRequest] = None


class TradeStats(SQLModel):
    """Aggregated trade statistics."""
    total_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float


class BacktestResponse(SQLModel):
    """Response for POST /api/backtest/run"""
    symbol: str
    start: str
    end: str
    stats: TradeStats
    trades: list[dict]
    equity_curve: list[dict]   # [{"date": "...", "value": 10234.5}, ...]


class OptimizerRun(SQLModel):
    """State of an async optimizer job."""
    job_id: str
    status: Literal["pending", "running", "complete", "error"]
    progress: int              # 0–100
    results: Optional[list[dict]] = None
    error: Optional[str] = None
