"""
alerts.py
Telegram alert sender. All bot events (signals, trade closes, errors) are
dispatched here. Uses httpx.AsyncClient under the hood with a synchronous
wrapper for the bot polling thread.
"""
from __future__ import annotations
import os
import asyncio
import logging
import json
from datetime import datetime
from typing import Optional
import httpx

log = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramAlerter:
    def __init__(self, token=None, chat_id=None):
        self.token   = token   or os.getenv("TELEGRAM_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self._client = httpx.AsyncClient(timeout=10)

    async def send(self, text: str, reply_markup=None) -> dict:
        """Send message. Returns response JSON including message_id."""
        if not self.token or not self.chat_id:
            log.info(f"[ALERT] {text}")
            return {}
        url  = TELEGRAM_API.format(token=self.token, method="sendMessage")
        data = {
            "chat_id":    self.chat_id,
            "text":       text,
            "parse_mode": "Markdown",
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        try:
            r = await self._client.post(url, json=data)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error(f"Telegram send failed: {e}")
            return {}

    async def edit_message(
        self, message_id: int, text: str
    ) -> bool:
        """Edit an existing message (used after trade confirmed)."""
        if not self.token or not self.chat_id:
            log.info(f"[ALERT EDIT] {text}")
            return False
        url  = TELEGRAM_API.format(
            token=self.token, method="editMessageText"
        )
        data = {
            "chat_id":    self.chat_id,
            "message_id": message_id,
            "text":       text,
            "parse_mode": "Markdown",
        }
        try:
            r = await self._client.post(url, json=data)
            return r.status_code == 200
        except Exception:
            return False

    async def answer_callback(
        self, callback_query_id: str, text: str = ""
    ) -> bool:
        """Dismiss the loading spinner on button tap."""
        if not self.token:
            return False
        url  = TELEGRAM_API.format(
            token=self.token, method="answerCallbackQuery"
        )
        try:
            r = await self._client.post(url, json={
                "callback_query_id": callback_query_id,
                "text": text,
            })
            return r.status_code == 200
        except Exception:
            return False

    async def signal_alert(
        self, symbol, signal, price, rsi,
        qty, stop, take_profit
    ):
        """Send signal alert WITH confirm/skip buttons."""
        emoji = "🟢" if signal == "BUY" else "🔴"
        text = (
            f"{emoji} *{signal} SIGNAL — {symbol}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💵 Price      : `${price:.2f}`\n"
            f"📊 RSI        : `{rsi:.1f}`\n"
            f"🧮 Qty        : `{qty}`\n"
        )
        if signal == "BUY":
            text += (
                f"🛑 Stop loss  : `${stop:.2f}`\n"
                f"🎯 Take profit: `${take_profit:.2f}`\n"
            )
        text += (
            f"🕐 Time       : `{datetime.utcnow().strftime('%H:%M UTC')}`\n\n"
            f"_Tap a button to act on this signal:_"
        )
        # Inline keyboard with confirm and skip buttons
        # callback_data format: "action|symbol|price|qty"
        reply_markup = {
            "inline_keyboard": [[
                {
                    "text": f"✅ Confirm {signal}",
                    "callback_data": f"{signal}|{symbol}|{price}|{qty}"
                },
                {
                    "text": "❌ Skip",
                    "callback_data": f"SKIP|{symbol}|{price}|{qty}"
                }
            ]]
        }
        response = await self.send(text, reply_markup=reply_markup)
        return response.get("result", {}).get("message_id")

    async def trade_closed_alert(
        self, symbol, side, entry,
        exit_price, pnl, exit_reason, account_value
    ):
        emoji = "✅" if pnl >= 0 else "❌"
        text = (
            f"{emoji} *TRADE CLOSED — {symbol}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"↗ Entry      : `${entry:.2f}`\n"
            f"↘ Exit       : `${exit_price:.2f}`\n"
            f"💰 P&L        : `${pnl:+.2f}`\n"
            f"📋 Reason     : `{exit_reason}`\n"
            f"🏦 Account    : `${account_value:,.2f}`"
        )
        await self.send(text)

    async def error_alert(self, error_msg: str):
        await self.send(
            f"⚠️ *BOT ERROR*\n`{error_msg}`\n"
            f"`{datetime.utcnow().strftime('%H:%M UTC')}`"
        )

    async def heartbeat(
        self, symbol, rsi, price, account
    ):
        await self.send(
            f"💓 *Heartbeat — {symbol}*\n"
            f"Price: `${price:.2f}` | "
            f"RSI: `{rsi:.1f}` | "
            f"Acct: `${account:,.2f}`"
        )

    async def close(self):
        await self._client.aclose()


class SyncAlerter:
    def __init__(self, **kwargs):
        self._async = TelegramAlerter(**kwargs)

    def _run(self, coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    def send(self, text, reply_markup=None):
        return self._run(self._async.send(text, reply_markup))

    def signal_alert(self, **kwargs):
        return self._run(self._async.signal_alert(**kwargs))

    def trade_closed_alert(self, **kwargs):
        return self._run(self._async.trade_closed_alert(**kwargs))

    def error_alert(self, error_msg):
        return self._run(self._async.error_alert(error_msg))

    def heartbeat(self, **kwargs):
        return self._run(self._async.heartbeat(**kwargs))

    def edit_message(self, message_id, text):
        return self._run(self._async.edit_message(message_id, text))

    def answer_callback(self, callback_query_id, text=""):
        return self._run(
            self._async.answer_callback(callback_query_id, text)
        )
