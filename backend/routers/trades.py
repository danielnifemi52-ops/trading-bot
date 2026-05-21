"""
trades.py
/api/trades/* — trade history, stats, delete
"""
from __future__ import annotations
import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session
from models import Trade, TradeStats

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def list_trades(
    limit: int = 50,
    symbol: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Return trade history, optionally filtered by symbol."""
    query = select(Trade).order_by(Trade.id.desc()).limit(limit)  # type: ignore[arg-type]
    rows = session.exec(query).all()
    if symbol:
        rows = [r for r in rows if r.symbol == symbol]
    return list(reversed(rows))


@router.get("/stats", response_model=TradeStats)
def get_stats(session: Session = Depends(get_session)):
    """Return aggregated trade statistics computed from the database."""
    trades = session.exec(select(Trade)).all()

    if not trades:
        return TradeStats(
            total_trades=0, win_rate=0.0, total_pnl=0.0,
            avg_win=0.0, avg_loss=0.0, profit_factor=0.0,
            max_drawdown_pct=0.0, sharpe_ratio=0.0,
        )

    pnls = [t.pnl for t in trades if t.pnl is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_pnl = sum(pnls)
    win_rate = len(wins) / len(pnls) if pnls else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0.0

    # Approximate max drawdown from cumulative PnL
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    start_capital = 10000.0  # baseline for % calc
    for p in pnls:
        cumulative += p
        if cumulative > peak:
            peak = cumulative
        dd = (peak - cumulative) / (start_capital + peak) * 100
        if dd > max_dd:
            max_dd = dd

    # Simple Sharpe on PnL list
    if len(pnls) > 1:
        import statistics
        mean_pnl = statistics.mean(pnls)
        std_pnl = statistics.stdev(pnls)
        sharpe = (mean_pnl / std_pnl * math.sqrt(252)) if std_pnl > 0 else 0.0
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


@router.delete("/{trade_id}")
def delete_trade(trade_id: int, session: Session = Depends(get_session)):
    """Delete a single trade record by ID."""
    trade = session.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    session.delete(trade)
    session.commit()
    return {"ok": True}
