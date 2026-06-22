"""
telegram.py
Handles all Telegram updates.
Button taps → place real Alpaca orders.
"""
import os
import math
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from sqlmodel import Session

from db import engine
from models import Trade
from services.broker import Broker, is_crypto
from services.alerts import SyncAlerter
from state import bot_state

log = logging.getLogger(__name__)
router = APIRouter()


def safe_float(value, default=None):
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def get_broker() -> Broker:
    """Get broker instance using current env settings."""
    is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
    return Broker(paper=is_paper, dry_run=False)


def get_alerter() -> SyncAlerter:
    return SyncAlerter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receives ALL Telegram updates.
    Called by Telegram every time user sends message 
    or taps a button.
    """
    try:
        data = await request.json()
        log.info(f"Telegram update received: {list(data.keys())}")

        if "callback_query" in data:
            await handle_button_tap(data["callback_query"])
        elif "message" in data:
            await handle_text_command(data["message"])

    except Exception as e:
        log.error(f"Telegram webhook error: {e}", exc_info=True)

    # Always return 200 to Telegram
    return {"ok": True}


async def handle_button_tap(callback: dict):
    """
    User tapped a button on a signal alert.
    callback_data format: "ACTION|SYMBOL|PRICE|QTY"
    """
    callback_id = callback.get("id", "")
    message     = callback.get("message", {})
    message_id  = message.get("message_id")
    raw_data    = callback.get("data", "")
    alerter     = get_alerter()

    log.info(f"Button tapped: {raw_data}")

    # Parse callback data
    parts = raw_data.split("|")
    if len(parts) < 4:
        alerter.answer_callback(callback_id, "❌ Invalid data")
        return

    action     = parts[0]
    symbol     = parts[1]
    price      = safe_float(parts[2], 0)
    qty        = safe_float(parts[3], 0)

    # User tapped Skip
    if action == "SKIP":
        alerter.answer_callback(callback_id, "⏭ Skipped")
        alerter.edit_message(
            message_id,
            f"⏭ *Signal skipped*\n"
            f"You skipped the {symbol} signal at "
            f"`${price:.2f}`\n\n"
            f"_Bot continues watching for next signal._"
        )
        return

    # Dismiss the loading spinner on button
    alerter.answer_callback(
        callback_id,
        f"⏳ Placing {action} order on Alpaca..."
    )

    broker = get_broker()

    if action == "BUY":
        await execute_buy(
            broker, alerter, symbol, 
            price, qty, message_id
        )

    elif action == "SELL":
        await execute_sell(
            broker, alerter, symbol,
            price, message_id
        )


async def execute_buy(
    broker, alerter, symbol, 
    price, qty, message_id
):
    """Place a BUY order and update the Telegram message."""
    try:
        # Check symbol is supported before trying to order
        if not broker.is_supported_symbol(symbol):
            alerter.edit_message(
                message_id,
                f"❌ *Symbol not supported*\n"
                f"`{symbol}` is not available on Alpaca.\n\n"
                f"Supported crypto:\n"
                f"BTC/USD, ETH/USD, SOL/USD, AVAX/USD,\n"
                f"DOGE/USD, LTC/USD, LINK/USD and more.\n\n"
                f"Change symbol in dashboard and restart bot."
            )
            return

        # Check if already have position
        if broker.has_position(symbol):
            alerter.edit_message(
                message_id,
                f"⚠️ *Already have position*\n"
                f"You already own {symbol}.\n"
                f"Sell your current position first."
            )
            return

        # Check buying power
        if not broker.can_afford(price, qty):
            bp = broker.get_buying_power()
            alerter.edit_message(
                message_id,
                f"❌ *Insufficient funds*\n"
                f"Need: `${price * qty:.2f}`\n"
                f"Available: `${bp:.2f}`\n"
                f"Reduce position size or add funds."
            )
            return

        # Place the order
        ok = broker.place_market_order(symbol, qty, "BUY")

        if ok:
            # Save to database
            with Session(engine) as session:
                trade = Trade(
                    symbol=symbol,
                    side="BUY",
                    price=price,
                    qty=qty,
                    rsi_at_signal=safe_float(
                        bot_state.last_rsi, 0
                    ),
                    timestamp=datetime.utcnow(),
                )
                session.add(trade)
                session.commit()

            # Calculate stop and take profit
            from core.strategy import BotConfig
            cfg = bot_state.config
            if cfg:
                sl = price * (1 - cfg.stop_loss_pct / 100)
                tp = price * (1 + cfg.take_profit_pct / 100)
            else:
                sl = price * 0.95
                tp = price * 1.10

            # Update the Telegram message
            is_paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
            alerter.edit_message(
                message_id,
                f"✅ *BUY ORDER PLACED*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📈 Symbol     : `{symbol}`\n"
                f"💵 Price      : `${price:.2f}`\n"
                f"🧮 Quantity   : `{qty}`\n"
                f"💰 Cost       : `${price * qty:.2f}`\n"
                f"🛑 Stop loss  : `${sl:.2f}`\n"
                f"🎯 Take profit: `${tp:.2f}`\n"
                f"📋 Account    : `{'Paper' if is_paper else 'LIVE'}`\n"
                f"🕐 Time       : "
                f"`{datetime.utcnow().strftime('%H:%M UTC')}`"
            )
            log.info(f"BUY order placed via Telegram: {qty} {symbol}")
        else:
            alerter.edit_message(
                message_id,
                f"❌ *BUY ORDER FAILED*\n"
                f"Could not place order for `{symbol}`.\n"
                f"Check your Alpaca account status."
            )

    except Exception as e:
        log.error(f"execute_buy error: {e}", exc_info=True)
        alerter.edit_message(
            message_id,
            f"❌ *Error placing BUY order*\n`{str(e)[:200]}`"
        )


async def execute_sell(
    broker, alerter, symbol, price, message_id
):
    """Close position and update the Telegram message."""
    try:
        # Check if have position
        if not broker.has_position(symbol):
            alerter.edit_message(
                message_id,
                f"⚠️ *No position to sell*\n"
                f"You don't have an open position in `{symbol}`."
            )
            return

        acct_before = broker.get_account_value()
        ok = broker.close_position(symbol)

        if ok:
            acct_after = broker.get_account_value()
            pnl = acct_after - acct_before
            is_paper = os.getenv(
                "ALPACA_PAPER", "true"
            ).lower() == "true"

            alerter.edit_message(
                message_id,
                f"{'✅' if pnl >= 0 else '❌'} "
                f"*SELL ORDER PLACED*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📉 Symbol   : `{symbol}`\n"
                f"💵 Price    : `${price:.2f}`\n"
                f"💰 P&L      : `${pnl:+.2f}`\n"
                f"🏦 Account  : `${acct_after:,.2f}`\n"
                f"📋 Type     : "
                f"`{'Paper' if is_paper else 'LIVE'}`\n"
                f"🕐 Time     : "
                f"`{datetime.utcnow().strftime('%H:%M UTC')}`"
            )
            log.info(
                f"SELL order placed via Telegram: {symbol}"
            )
        else:
            alerter.edit_message(
                message_id,
                f"❌ *SELL ORDER FAILED*\n"
                f"Could not close position for `{symbol}`."
            )

    except Exception as e:
        log.error(f"execute_sell error: {e}", exc_info=True)
        alerter.edit_message(
            message_id,
            f"❌ *Error placing SELL order*\n"
            f"`{str(e)[:200]}`"
        )


async def handle_text_command(message: dict):
    """Handle typed commands in Telegram chat."""
    text    = message.get("text", "").strip().lower()
    alerter = get_alerter()
    broker  = get_broker()

    if text == "/status":
        running = bot_state.is_running
        symbol  = bot_state.config.symbol if bot_state.config else "—"
        price   = safe_float(bot_state.last_price)
        rsi     = safe_float(bot_state.last_rsi)
        signal  = bot_state.last_signal or "HOLD"
        acct    = broker.get_account_value()

        # Get open positions
        try:
            positions = broker.client.get_all_positions()
            pos_text = ""
            for p in positions:
                pnl = float(p.unrealized_pl)
                pos_text += (
                    f"\n  {p.symbol}: "
                    f"{p.qty} @ ${float(p.avg_entry_price):.2f} "
                    f"({pnl:+.2f})"
                )
            if not pos_text:
                pos_text = "\n  No open positions"
        except Exception:
            pos_text = "\n  Could not fetch positions"

        alerter._run(alerter._async.send(
            f"📊 *Bot Status*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Status  : `{'🟢 RUNNING' if running else '⚪ IDLE'}`\n"
            f"Symbol  : `{symbol}`\n"
            f"Price   : `${price:.2f if price else '—'}`\n"
            f"RSI     : `{rsi:.1f if rsi else '—'}`\n"
            f"Signal  : `{signal}`\n"
            f"Account : `${acct:,.2f}`\n"
            f"\n*Open Positions:*{pos_text}"
        ))

    elif text == "/buy":
        symbol = bot_state.config.symbol if bot_state.config else None
        price  = safe_float(bot_state.last_price)
        if not symbol or not price:
            alerter._run(alerter._async.send(
                "⚠️ Start the bot first before placing manual orders."
            ))
            return
        cfg = bot_state.config
        from core.strategy import BotConfig, position_size
        acct = broker.get_account_value()
        bot_cfg = BotConfig(
            symbol=symbol,
            stop_loss_pct=cfg.stop_loss_pct if cfg else 5,
            take_profit_pct=cfg.take_profit_pct if cfg else 10,
            risk_per_trade_pct=cfg.risk_per_trade_pct if cfg else 2,
        )
        qty = position_size(
            acct, price, bot_cfg,
            crypto=is_crypto(symbol)
        )
        # Send confirmation buttons
        alerter._run(alerter._async.signal_alert(
            symbol=symbol, signal="BUY",
            price=price,
            rsi=safe_float(bot_state.last_rsi, 50),
            qty=qty,
            stop=price * (1 - (cfg.stop_loss_pct if cfg else 5) / 100),
            take_profit=price * (1 + (cfg.take_profit_pct if cfg else 10) / 100),
        ))

    elif text == "/sell":
        symbol = bot_state.config.symbol if bot_state.config else None
        price  = safe_float(bot_state.last_price)
        if not symbol or not price:
            alerter._run(alerter._async.send(
                "⚠️ Start the bot first before placing orders."
            ))
            return
        alerter._run(alerter._async.signal_alert(
            symbol=symbol, signal="SELL",
            price=price,
            rsi=safe_float(bot_state.last_rsi, 50),
            qty=0,
            stop=0,
            take_profit=0,
        ))

    elif text == "/positions":
        acct = broker.get_account_value()
        try:
            positions = broker.client.get_all_positions()
            if not positions:
                alerter._run(alerter._async.send(
                    "📭 *No open positions*"
                ))
                return
            msg = f"📈 *Open Positions*\n━━━━━━━━━━━━━━━\n"
            for p in positions:
                pnl     = float(p.unrealized_pl)
                pnl_pct = float(p.unrealized_plpc) * 100
                msg += (
                    f"\n*{p.symbol}*\n"
                    f"  Qty    : `{p.qty}`\n"
                    f"  Entry  : `${float(p.avg_entry_price):.2f}`\n"
                    f"  Current: `${float(p.current_price):.2f}`\n"
                    f"  P&L    : `${pnl:+.2f} ({pnl_pct:+.2f}%)`\n"
                )
            msg += f"\n🏦 Account: `${acct:,.2f}`"
            alerter._run(alerter._async.send(msg))
        except Exception as e:
            alerter._run(alerter._async.send(
                f"❌ Could not fetch positions: {e}"
            ))

    elif text == "/stop":
        bot_state.stop()
        alerter._run(alerter._async.send(
            "🛑 *Bot stopped* from Telegram\n"
            "Go to dashboard to restart."
        ))

    elif text == "/help":
        alerter._run(alerter._async.send(
            "📱 *RSI Bot Commands*\n"
            "━━━━━━━━━━━━━━━\n"
            "/status     — Price, RSI, account value\n"
            "/buy        — Manual BUY with confirm button\n"
            "/sell       — Manual SELL with confirm button\n"
            "/positions  — Show all open positions\n"
            "/stop       — Stop the bot\n"
            "/help       — Show this menu\n\n"
            "_Signal alerts include Confirm/Skip buttons "
            "to trade directly from Telegram._"
        ))

    else:
        # Unknown command
        alerter._run(alerter._async.send(
            "❓ Unknown command. Send /help for the command list."
        ))


@router.post("/register")
async def register_webhook():
    """Manually register Telegram webhook."""
    import httpx
    
    token       = os.environ["TELEGRAM_TOKEN"]
    render_url  = os.environ.get("RENDER_URL", "")
    
    if not render_url:
        raise HTTPException(
            status_code=400,
            detail="RENDER_URL not set in environment variables"
        )
    
    webhook_url = f"{render_url}/api/telegram/webhook"
    
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"]
            }
        )
        data = r.json()
        
        if data.get("ok"):
            log.info(f"✅ Telegram webhook manually registered: {webhook_url}")
            return {
                "ok": True,
                "webhook_url": webhook_url,
                "message": "Webhook registered successfully"
            }
        else:
            log.error(f"❌ Telegram rejected webhook: {data}")
            raise HTTPException(
                status_code=400,
                detail=f"Telegram rejected webhook: {data}"
            )


@router.get("/info")
async def webhook_info():
    """Check current webhook status."""
    import httpx
    
    token = os.environ["TELEGRAM_TOKEN"]
    
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.telegram.org/bot{token}/getWebhookInfo"
        )
        data = r.json()
        log.info(f"Webhook info: {data}")
        return data

