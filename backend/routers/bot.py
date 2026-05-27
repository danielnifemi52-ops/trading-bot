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
    dry_run  = False
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


# ---------------------------------------------------------------------------
# Data-source diagnostics
# ---------------------------------------------------------------------------
import pandas as pd  # noqa: E402  (already a project dep)


@router.get("/diagnose/{symbol}")
async def diagnose_symbol(symbol: str):
    """
    Tests all data sources for a symbol and returns results.
    Use to debug why a symbol is not showing price data.
    Visit: /api/bot/diagnose/AAPL  or  /api/bot/diagnose/BTC%2FUSD
    """
    results: dict = {}

    # ------------------------------------------------------------------
    # Test 1 — Alpaca stock data
    # ------------------------------------------------------------------
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        client = StockHistoricalDataClient(
            api_key=os.environ["ALPACA_KEY"],
            secret_key=os.environ["ALPACA_SECRET"],
        )
        req_s = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Hour,
            limit=5,
        )
        bars = client.get_stock_bars(req_s)
        df = bars.df
        if not df.empty:
            results["alpaca_stock"] = {
                "status": "ok",
                "bars": len(df),
                "latest_price": float(df["close"].iloc[-1]),
                "latest_time": str(df.index[-1]),
            }
        else:
            results["alpaca_stock"] = {
                "status": "empty",
                "message": "Alpaca returned no data for this symbol",
            }
    except Exception as exc:
        results["alpaca_stock"] = {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Test 2 — Alpaca crypto data
    # ------------------------------------------------------------------
    try:
        from alpaca.data.historical.crypto import CryptoHistoricalDataClient
        from alpaca.data.requests import CryptoBarsRequest
        from alpaca.data.timeframe import TimeFrame as TF2  # noqa: F811

        client2 = CryptoHistoricalDataClient(
            api_key=os.environ["ALPACA_KEY"],
            secret_key=os.environ["ALPACA_SECRET"],
        )
        req_c = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TF2.Hour,
            limit=5,
        )
        bars2 = client2.get_crypto_bars(req_c)
        df2 = bars2.df
        if isinstance(df2.index, pd.MultiIndex):
            df2 = df2.reset_index(level=0, drop=True)
        if not df2.empty:
            results["alpaca_crypto"] = {
                "status": "ok",
                "bars": len(df2),
                "latest_price": float(df2["close"].iloc[-1]),
                "latest_time": str(df2.index[-1]),
            }
        else:
            results["alpaca_crypto"] = {
                "status": "empty",
                "message": "No crypto data returned",
            }
    except Exception as exc:
        results["alpaca_crypto"] = {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Test 3 — yfinance
    # ------------------------------------------------------------------
    try:
        import yfinance as yf

        df3 = yf.download(
            symbol, period="5d", interval="1h",
            auto_adjust=True, progress=False,
        )
        if not df3.empty:
            results["yfinance"] = {
                "status": "ok",
                "bars": len(df3),
                "latest_price": float(df3["Close"].iloc[-1]),
                "latest_time": str(df3.index[-1]),
            }
        else:
            results["yfinance"] = {
                "status": "empty",
                "message": "yfinance returned no data",
            }
    except Exception as exc:
        results["yfinance"] = {"status": "error", "message": str(exc)}

    return {
        "symbol": symbol,
        "results": results,
        "recommendation": _get_recommendation(results),
    }


def _get_recommendation(results: dict) -> str:
    alpaca_stock  = results.get("alpaca_stock",  {})
    alpaca_crypto = results.get("alpaca_crypto", {})
    yfinance      = results.get("yfinance",      {})

    if alpaca_crypto.get("status") == "ok":
        return "Use Alpaca crypto data — working correctly"
    if alpaca_stock.get("status") == "ok":
        return "Use Alpaca stock data — working correctly"
    if yfinance.get("status") == "ok":
        return "Use yfinance fallback — Alpaca not available for this symbol"
    return "No data source working — check API keys and symbol name"


# ---------------------------------------------------------------------------
# Alpaca Account Sync Endpoints
# ---------------------------------------------------------------------------

@router.get("/account")
async def get_account():
    """Get real account data from Alpaca paper trading."""
    try:
        is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        broker = Broker(paper=is_paper, dry_run=False)
        
        if not broker.client:
            return {
                "connected": False,
                "message": "Alpaca not configured",
            }

        acct = broker.client.get_account()
        
        return {
            "connected":        True,
            "account_id":       str(acct.id),
            "status":           str(acct.status),
            "currency":         str(acct.currency),
            "portfolio_value":  float(acct.portfolio_value),
            "cash":             float(acct.cash),
            "buying_power":     float(acct.buying_power),
            "equity":           float(acct.equity),
            "last_equity":      float(acct.last_equity),
            "pnl":              float(acct.equity) - float(acct.last_equity),
            "pnl_pct":          ((float(acct.equity) - float(acct.last_equity)) 
                                 / float(acct.last_equity) * 100) 
                                 if float(acct.last_equity) > 0 else 0,
            "paper":            is_paper,
        }
    except Exception as e:
        log.error(f"Account fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions():
    """Get all open positions from Alpaca."""
    try:
        is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        broker = Broker(paper=is_paper, dry_run=False)
        
        if not broker.client:
            return {"positions": []}

        positions = broker.client.get_all_positions()
        
        return {
            "positions": [
                {
                    "symbol":        str(p.symbol),
                    "qty":           float(p.qty),
                    "side":          str(p.side),
                    "entry_price":   float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "market_value":  float(p.market_value),
                    "cost_basis":    float(p.cost_basis),
                    "unrealized_pnl":float(p.unrealized_pl),
                    "unrealized_pct":float(p.unrealized_plpc) * 100,
                    "change_today":  float(p.change_today),
                }
                for p in positions
            ]
        }
    except Exception as e:
        log.error(f"Positions fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_orders(limit: int = 20):
    """Get recent orders from Alpaca."""
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

        is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        broker = Broker(paper=is_paper, dry_run=False)

        if not broker.client:
            return {"orders": []}

        req = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            limit=limit,
        )
        orders = broker.client.get_orders(req)

        return {
            "orders": [
                {
                    "id":          str(o.id),
                    "symbol":      str(o.symbol),
                    "side":        str(o.side),
                    "qty":         float(o.qty or 0),
                    "filled_qty":  float(o.filled_qty or 0),
                    "filled_price":float(o.filled_avg_price or 0),
                    "status":      str(o.status),
                    "type":        str(o.order_type),
                    "created_at":  str(o.created_at),
                    "filled_at":   str(o.filled_at) if o.filled_at else None,
                }
                for o in orders
            ]
        }
    except Exception as e:
        log.error(f"Orders fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/positions/{symbol:path}")
async def close_position_endpoint(symbol: str):
    """Close a specific position from the dashboard."""
    try:
        is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        broker = Broker(paper=is_paper, dry_run=False)
        ok = broker.close_position(symbol)
        if ok:
            return {"ok": True, "message": f"Position closed: {symbol}"}
        raise HTTPException(status_code=500, detail="Failed to close position")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
