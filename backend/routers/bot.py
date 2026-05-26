"""
bot.py
/api/bot/* — start, stop, status, logs
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session
from models import BotConfigRequest, BotStatusResponse, BotLog, Trade
from state import bot_state
from ws import manager
from core.strategy import BotConfig
from services.broker import Broker
from services.alerts import SyncAlerter
from services.bot_runner import BotRunner

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status", response_model=BotStatusResponse)
def get_status():
    """Return the current bot status."""
    runner = bot_state._runner
    stream_active = False
    if runner:
        stream_active = getattr(runner, '_stream_active', False)
    return BotStatusResponse(
        running=bot_state.is_running,
        symbol=bot_state.config.symbol if bot_state.config else None,
        last_price=bot_state.last_price,
        last_rsi=bot_state.last_rsi,
        last_signal=bot_state.last_signal,
        account_value=10000.0,
        open_position=bot_state.open_position,
        config=bot_state.config,
        stream_active=stream_active,
    )


@router.post("/start")
async def start_bot(req: BotConfigRequest, session: Session = Depends(get_session)):
    """Start the trading bot with the given configuration."""
    if bot_state.is_running:
        raise HTTPException(status_code=409, detail="Bot is already running")

    cfg = BotConfig(
        symbol=req.symbol,
        rsi_period=req.rsi_period,
        oversold=req.oversold,
        overbought=req.overbought,
        stop_loss_pct=req.stop_loss_pct,
        take_profit_pct=req.take_profit_pct,
        risk_per_trade_pct=req.risk_per_trade_pct,
        poll_interval_seconds=req.poll_interval_seconds,
    )
    broker = Broker(paper=True, dry_run=req.dry_run)
    alerter = SyncAlerter()

    loop = asyncio.get_event_loop()

    def on_tick(price: float, rsi: float, signal: str, account: float, source: str = "poll"):
        """Persist a BotLog row and broadcast to WebSocket clients."""
        from db import engine
        try:
            with Session(engine) as s:
                row = BotLog(
                    symbol=req.symbol, price=price, rsi=rsi,
                    signal=signal, account_value=account,
                    timestamp=datetime.utcnow(),
                )
                s.add(row)
                s.commit()
        except Exception as e:
            log.error(f"on_tick DB write failed: {e}")

        data = {
            "price": price,
            "rsi": rsi,
            "signal": signal,
            "account": account,
            "symbol": cfg.symbol,
            "ts": datetime.utcnow().isoformat(),
            "source": source,
        }
        try:
            asyncio.run_coroutine_threadsafe(manager.broadcast(data), loop)
        except Exception as e:
            log.error(f"WebSocket broadcast failed: {e}")

    def on_trade(trade_dict: dict):
        """Persist a Trade row on every executed trade."""
        try:
            with Session(session.get_bind()) as s:
                row = Trade(
                    symbol=trade_dict["symbol"],
                    side=trade_dict["side"],
                    price=trade_dict["price"],
                    qty=trade_dict["qty"],
                    rsi_at_signal=trade_dict.get("rsi", 0.0),
                    pnl=trade_dict.get("pnl"),
                    exit_reason=trade_dict.get("exit_reason"),
                    timestamp=datetime.utcnow(),
                )
                s.add(row)
                s.commit()
        except Exception as e:
            log.error(f"on_trade DB write failed: {e}")

    runner = BotRunner(cfg=cfg, broker=broker, alerter=alerter,
        on_tick=on_tick, on_trade=on_trade)
    bot_state.start(runner, req)
    log.info(f"Bot started for {req.symbol}")
    return {"ok": True, "message": f"Bot started for {req.symbol}"}


@router.post("/stop")
def stop_bot():
    """Stop the running bot."""
    bot_state.stop()
    return {"ok": True}


@router.get("/logs")
def get_logs(limit: int = 100, session: Session = Depends(get_session)):
    """Return the most recent bot log entries."""
    rows = session.exec(
        select(BotLog).order_by(BotLog.id.desc()).limit(limit) # type: ignore[arg-type]
    ).all()
    return list(reversed(rows))
