"""
bot.py
/api/bot/* — start, stop, status, logs
"""
from __future__ import annotations
import asyncio
import logging
import math
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db import get_session
from models import BotConfigRequest, BotStatusResponse, BotLog, Trade
from state import bot_state
from ws import manager
from core.strategy import BotConfig
from services.broker import Broker
from services.broker_factory import get_broker
from services.alerts import SyncAlerter
from services.bot_runner import BotRunner

log = logging.getLogger(__name__)
router = APIRouter()


def safe_float(value, default=None):
    """
    Convert float to JSON-safe value.
    Returns default if value is NaN, Infinity, or None.
    """
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 4)
    except (TypeError, ValueError):
        return default


@router.get("/status")
async def get_status():
    """Return the current bot status. Never returns 500."""
    try:
        # Safe attribute access — never crash on a bad state
        is_running    = False
        last_price    = None
        last_rsi      = None
        last_signal   = "HOLD"
        open_position = False
        config        = None
        stream_active = False

        try:
            is_running = bot_state.is_running
        except Exception:
            pass
        try:
            last_price = safe_float(bot_state.last_price)
        except Exception:
            pass
        try:
            last_rsi = safe_float(bot_state.last_rsi)
        except Exception:
            pass
        try:
            last_signal = bot_state.last_signal or "HOLD"
        except Exception:
            pass
        try:
            open_position = bot_state.open_position
        except Exception:
            pass
        try:
            config = bot_state.config
        except Exception:
            pass

        # Get real account value safely
        account_value = 10000.0
        try:
            symbol = config.symbol if config else ""
            broker = get_broker(symbol=symbol, dry_run=False)
            account_value = safe_float(broker.get_account_value(), 10000.0)
        except Exception:
            pass

        return {
            "running":       is_running,
            "symbol":        config.symbol if config else None,
            "last_price":    last_price,
            "last_rsi":      last_rsi,
            "last_signal":   last_signal,
            "account_value": account_value,
            "open_position": open_position,
            "config":        config,
            "stream_active": stream_active,
        }
    except Exception as e:
        log.error(f"Status endpoint error: {e}", exc_info=True)
        # Never return 500 — always return something useful
        return {
            "running":       False,
            "symbol":        None,
            "last_price":    None,
            "last_rsi":      None,
            "last_signal":   "HOLD",
            "account_value": 10000.0,
            "open_position": False,
            "config":        None,
            "stream_active": False,
            "error":         str(e),
        }


class StartBotRequest(BotConfigRequest):
    force_restart: bool = False


@router.post("/start")
async def start_bot(req: StartBotRequest, session: Session = Depends(get_session)):
    """Start the trading bot with the given configuration."""
    # If force_restart is not set and bot is genuinely running, reject
    if bot_state.is_running and not req.force_restart:
        raise HTTPException(
            status_code=409,
            detail="Bot is already running. Use force_restart=true to restart."
        )

    # Force stop any existing instance (handles stale state after redeploy)
    try:
        bot_state.stop()
        import time
        time.sleep(1)   # give thread time to stop
    except Exception:
        pass

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
    broker = get_broker(symbol=req.symbol, dry_run=req.dry_run)
    alerter = SyncAlerter()

    loop = asyncio.get_event_loop()
    tick_count = 0

    def on_tick(price: float, rsi: float, signal: str, account: float):
        """Broadcast every tick; persist to DB only every 10th tick."""
        nonlocal tick_count
        tick_count += 1

        # Sanitize floats — NaN/Inf crash JSON serialization
        safe_price   = safe_float(price)
        safe_rsi     = safe_float(rsi)
        safe_account = safe_float(account, 10000.0)

        # Only broadcast if we have valid price data
        if safe_price is None:
            return

        data = {
            "price":   safe_price,
            "rsi":     safe_rsi,
            "signal":  signal or "HOLD",
            "account": safe_account,
            "symbol":  cfg.symbol,
            "ts":      datetime.utcnow().isoformat(),
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
    dry_run  = False
    broker   = get_broker(symbol=req.symbol, dry_run=dry_run)
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
    """Get real account data from the active broker (auto-detected by symbol)."""
    try:
        from services.broker_binance import BinanceBroker
        symbol = (
            bot_state.config.symbol
            if bot_state.config else ""
        )
        broker = get_broker(symbol=symbol, dry_run=False)

        # ── Binance path ────────────────────────────────────────────────────
        if isinstance(broker, BinanceBroker):
            return {
                "connected":       broker.client is not None,
                "account_id":      "binance",
                "status":          "ACTIVE",
                "currency":        "USDT",
                "portfolio_value": broker.get_account_value(),
                "cash":            broker.get_buying_power(),
                "buying_power":    broker.get_buying_power(),
                "equity":          broker.get_account_value(),
                "last_equity":     broker.get_account_value(),
                "pnl":             0.0,
                "pnl_pct":         0.0,
                "paper":           os.getenv("BINANCE_TESTNET", "true").lower() == "true",
            }

        # ── Alpaca path ─────────────────────────────────────────────────────
        if not broker.client:
            return {
                "connected": False,
                "message": "Alpaca not configured",
            }

        acct = broker.client.get_account()
        is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"

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
    """Get all open positions from the active broker (auto-detected by symbol)."""
    try:
        from services.broker_binance import BinanceBroker
        symbol = (
            bot_state.config.symbol
            if bot_state.config else ""
        )
        broker = get_broker(symbol=symbol, dry_run=False)

        # ── Binance: return current crypto balances as positions ─────────────
        if isinstance(broker, BinanceBroker):
            if not broker.client:
                return {"positions": []}
            try:
                balances = broker.client.get_account()["balances"]
                positions = []
                for b in balances:
                    free = float(b["free"])
                    locked = float(b["locked"])
                    total = free + locked
                    if total > 0.0001 and b["asset"] not in ("USDT", "BNB"):
                        sym = f"{b['asset']}/USD"
                        price = broker.get_latest_price(sym) if total > 0 else 0.0
                        positions.append({
                            "symbol":        sym,
                            "qty":           total,
                            "side":          "long",
                            "entry_price":   0.0,
                            "current_price": price,
                            "market_value":  total * price,
                            "cost_basis":    0.0,
                            "unrealized_pnl": 0.0,
                            "unrealized_pct": 0.0,
                            "change_today":  0.0,
                        })
                return {"positions": positions}
            except Exception as e:
                log.error(f"Binance positions fetch error: {e}")
                return {"positions": []}

        # ── Alpaca path ──────────────────────────────────────────────────────
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
    """Get recent orders from the active broker (auto-detected by symbol)."""
    try:
        from services.broker_binance import BinanceBroker
        symbol = (
            bot_state.config.symbol
            if bot_state.config else ""
        )
        broker = get_broker(symbol=symbol, dry_run=False)

        # ── Binance: fetch recent trades ─────────────────────────────────────
        if isinstance(broker, BinanceBroker):
            if not broker.client:
                return {"orders": []}
            try:
                from services.broker_binance import to_binance_symbol
                bsym = to_binance_symbol(symbol) if symbol else None
                if not bsym:
                    return {"orders": []}
                trades = broker.client.get_my_trades(symbol=bsym, limit=limit)
                return {
                    "orders": [
                        {
                            "id":           str(t["orderId"]),
                            "symbol":       symbol,
                            "side":         "BUY" if t["isBuyer"] else "SELL",
                            "qty":           float(t["qty"]),
                            "filled_qty":    float(t["qty"]),
                            "filled_price":  float(t["price"]),
                            "status":        "filled",
                            "type":          "market",
                            "created_at":    str(t["time"]),
                            "filled_at":     str(t["time"]),
                        }
                        for t in trades
                    ]
                }
            except Exception as e:
                log.error(f"Binance orders fetch error: {e}")
                return {"orders": []}

        # ── Alpaca path ──────────────────────────────────────────────────────
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

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
        broker = get_broker(symbol=symbol, dry_run=False)
        ok = broker.close_position(symbol)
        if ok:
            return {"ok": True, "message": f"Position closed: {symbol}"}
        raise HTTPException(status_code=500, detail="Failed to close position")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
