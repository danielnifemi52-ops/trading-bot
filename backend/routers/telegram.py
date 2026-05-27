"""
telegram.py
Receives Telegram webhook callbacks (button taps).
When user taps Confirm BUY/SELL, executes the trade.
When user taps Skip, does nothing.
"""
import os
import logging
from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from sqlmodel import Session

from db import engine
from models import Trade
from services.broker import Broker, is_crypto
from services.alerts import SyncAlerter
from state import bot_state

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receives all Telegram updates including button callbacks.
    Telegram sends a POST here every time user taps a button.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    log.info(f"Telegram update: {data}")

    # Handle inline keyboard button tap
    if "callback_query" in data:
        await handle_callback(data["callback_query"])

    # Handle text commands (/start, /status, /stop)
    elif "message" in data:
        await handle_command(data["message"])

    return {"ok": True}


async def handle_callback(callback: dict):
    """Process button tap from inline keyboard."""
    callback_id = callback["id"]
    message_id  = callback["message"]["message_id"]
    raw_data    = callback.get("data", "")
    alerter     = SyncAlerter()

    # Parse: "BUY|BTC/USD|75000.0|0.001"
    parts = raw_data.split("|")
    if len(parts) < 4:
        alerter.answer_callback(callback_id, "Invalid data")
        return

    action, symbol, price_str, qty_str = parts[:4]
    try:
        price = float(price_str)
        qty   = float(qty_str)
    except ValueError:
        alerter.answer_callback(callback_id, "Error parsing quantity or price")
        return

    # User tapped Skip
    if action == "SKIP":
        alerter.answer_callback(callback_id, "⏭ Signal skipped")
        alerter.edit_message(
            message_id,
            f"⏭ *Signal skipped*\n"
            f"You chose to skip the {symbol} signal at `${price:.2f}`"
        )
        return

    # User tapped Confirm BUY or SELL
    cfg      = bot_state.config
    is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
    dry_run  = cfg.dry_run if cfg else True
    broker   = Broker(paper=is_paper, dry_run=dry_run)

    alerter.answer_callback(
        callback_id,
        f"⏳ Placing {action} order..."
    )

    if action == "BUY":
        ok = broker.place_market_order(symbol, qty, "BUY")
        if ok:
            try:
                with Session(engine) as session:
                    session.add(Trade(
                        symbol=symbol, side="BUY",
                        price=price, qty=qty,
                        rsi_at_signal=0.0,
                        timestamp=datetime.utcnow(),
                    ))
                    session.commit()
            except Exception as db_err:
                log.error(f"Failed to persist buy trade: {db_err}")

            alerter.edit_message(
                message_id,
                f"✅ *BUY ORDER PLACED*\n"
                f"Symbol: `{symbol}`\n"
                f"Price:  `${price:.2f}`\n"
                f"Qty:    `{qty}`\n"
                f"{'[DRY RUN — no real order placed]' if dry_run else ''}"
            )
        else:
            alerter.edit_message(
                message_id,
                f"❌ *BUY ORDER FAILED*\n"
                f"Could not place order for {symbol}. "
                f"Check Alpaca connection."
            )

    elif action == "SELL":
        ok = broker.close_position(symbol)
        if ok:
            try:
                with Session(engine) as session:
                    session.add(Trade(
                        symbol=symbol, side="SELL",
                        price=price, qty=qty,
                        rsi_at_signal=0.0,
                        timestamp=datetime.utcnow(),
                    ))
                    session.commit()
            except Exception as db_err:
                log.error(f"Failed to persist sell trade: {db_err}")

            alerter.edit_message(
                message_id,
                f"✅ *SELL ORDER PLACED*\n"
                f"Position closed: `{symbol}`\n"
                f"Price: `${price:.2f}`\n"
                f"{'[DRY RUN]' if dry_run else ''}"
            )
        else:
            alerter.edit_message(
                message_id,
                f"❌ *SELL ORDER FAILED*\n"
                f"Could not close position for {symbol}."
            )


async def handle_command(message: dict):
    """Handle text commands typed in Telegram chat."""
    text    = message.get("text", "").strip()
    alerter = SyncAlerter()

    if text == "/status":
        if bot_state.is_running:
            price_str  = f"{bot_state.last_price:.2f}" if bot_state.last_price is not None else "—"
            rsi_str    = f"{bot_state.last_rsi:.1f}" if bot_state.last_rsi is not None else "—"
            signal = bot_state.last_signal or "HOLD"
            symbol = bot_state.config.symbol if bot_state.config else "—"
            alerter._run(alerter._async.send(
                f"📊 *Bot Status*\n"
                f"Symbol : `{symbol}`\n"
                f"Price  : `${price_str}`\n"
                f"RSI    : `{rsi_str}`\n"
                f"Signal : `{signal}`\n"
                f"Status : `RUNNING ✅`"
            ))
        else:
            alerter._run(alerter._async.send(
                "⚪ Bot is currently *IDLE*\n"
                "Start it from the dashboard."
            ))

    elif text == "/stop":
        bot_state.stop()
        alerter._run(alerter._async.send(
            "🛑 *Bot stopped* from Telegram"
        ))

    elif text == "/help" or text == "/start":
        alerter._run(alerter._async.send(
            "📱 *Available commands*\n\n"
            "/status — Check current price and RSI\n"
            "/stop   — Stop the bot\n"
            "/help   — Show this message\n\n"
            "_Tap Confirm/Skip buttons on signal alerts "
            "to execute trades directly from Telegram._"
        ))
