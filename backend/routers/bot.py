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
    return BotStatusResponse(
        running=bot_state.is_running,
        symbol=bot_state.config.symbol if bot_state.config else None,
        last_price=bot_state.last_price,
        last_rsi=bot_state.last_rsi,
        last_signal=bot_state.last_signal,
        account_value=10000.0,
        open_position=bot_state.open_position,
        config=bot_state.config,
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
        timeframe=req.timeframe,
    )
    broker = Broker(paper=True, dry_run=req.dry_run)
    alerter = SyncAlerter()

    loop = asyncio.get_event_loop()
    tick_count = 0

    def on_tick(price: float, rsi: float, signal: str, account: float):
        """Broadcast every tick; persist to DB only every 10th tick."""
        nonlocal tick_count
        tick_count += 1

        # Always broadcast to WebSocket
        data = {
            "price": price,
            "rsi": rsi,
            "signal": signal,
            "account": account,
            "symbol": cfg.symbol,
            "ts": datetime.utcnow().isoformat(),
        }
        try:
            asyncio.run_coroutine_threadsafe(manager.broadcast(data), loop)
        except Exception as e:
            log.error(f"WebSocket broadcast failed: {e}")

        # Only write to DB every 10 ticks
        if tick_count % 10 != 0:
            return

        from db import engine
        try:
            with Session(engine) as s:
                s.add(BotLog(
                    symbol=req.symbol,
                    price=price,
                    rsi=rsi,
                    signal=signal,
                    account_value=account,
                    timestamp=datetime.utcnow(),
                ))
                s.commit()
        except Exception as e:
            log.error(f"on_tick DB write failed: {e}")

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


import os
from typing import Optional
from sqlmodel import SQLModel
from core.strategy import position_size, stop_price, take_profit_price
from services.broker import is_crypto
from db import engine

class ManualTradeRequest(SQLModel):
    symbol: str
    side: str          # "BUY" or "SELL"
    qty: Optional[float] = None   # if None, auto-calculate from risk settings


@router.post("/trade")
async def manual_trade(req: ManualTradeRequest):
    """
    Place a manual market order from the dashboard.
    Used when user clicks Buy Now or Sell Now button.
    """
    cfg      = bot_state.config
    is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
    dry_run  = cfg.dry_run if cfg else True
    broker   = Broker(paper=is_paper, dry_run=dry_run)
    alerter  = SyncAlerter()

    try:
        acct  = broker.get_account_value()
        price = bot_state.last_price or 0

        if price == 0:
            raise HTTPException(
                status_code=400,
                detail="No price data available. Start the bot first."
            )

        # Auto-calculate qty if not provided
        if req.qty is None and cfg:
            from core.strategy import BotConfig
            bot_cfg = BotConfig(
                symbol=req.symbol,
                stop_loss_pct=cfg.stop_loss_pct,
                take_profit_pct=cfg.take_profit_pct,
                risk_per_trade_pct=cfg.risk_per_trade_pct,
            )
            qty = position_size(
                acct, price, bot_cfg,
                crypto=is_crypto(req.symbol)
            )
        else:
            qty = req.qty or 0.001

        if req.side == "BUY":
            has_pos = broker.has_position(req.symbol)
            if has_pos:
                raise HTTPException(
                    status_code=400,
                    detail=f"Already have an open position in {req.symbol}"
                )
            ok = broker.place_market_order(req.symbol, qty, "BUY")
            if ok:
                sl = stop_price(price, bot_cfg) if cfg else price * 0.95
                tp = take_profit_price(price, bot_cfg) if cfg else price * 1.1
                with Session(engine) as session:
                    session.add(Trade(
                        symbol=req.symbol, side="BUY",
                        price=price, qty=qty,
                        rsi_at_signal=bot_state.last_rsi or 0.0,
                        timestamp=datetime.utcnow(),
                    ))
                    session.commit()
                alerter.signal_alert(
                    symbol=req.symbol, signal="BUY",
                    price=price, rsi=bot_state.last_rsi or 0.0,
                    qty=qty, stop=sl, take_profit=tp
                )
                return {
                    "ok": True,
                    "action": "BUY",
                    "symbol": req.symbol,
                    "price": price,
                    "qty": qty,
                    "dry_run": dry_run,
                }

        elif req.side == "SELL":
            ok = broker.close_position(req.symbol)
            if ok:
                with Session(engine) as session:
                    session.add(Trade(
                        symbol=req.symbol, side="SELL",
                        price=price, qty=qty,
                        rsi_at_signal=bot_state.last_rsi or 0.0,
                        timestamp=datetime.utcnow(),
                    ))
                    session.commit()
                return {
                    "ok": True,
                    "action": "SELL",
                    "symbol": req.symbol,
                    "price": price,
                    "dry_run": dry_run,
                }

        raise HTTPException(status_code=500, detail="Order failed")

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Manual trade error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
