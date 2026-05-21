"""
alerts.py
Telegram alert sender. All bot events (signals, trade closes, errors) are
dispatched here. Uses httpx for synchronous HTTP calls from the bot thread.
"""
from __future__ import annotations
import os
import logging
import httpx

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class SyncAlerter:
    """Sends Telegram messages synchronously. Safe to call from any thread."""

    def __init__(self) -> None:
        """Initialise with credentials from environment."""
        self.token = os.getenv("TELEGRAM_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)
        if not self.enabled:
            log.warning("Telegram credentials not set — alerts disabled")

    def _send(self, text: str) -> None:
        """Send a raw message. Silently swallows errors to avoid crashing the bot."""
        if not self.enabled:
            log.info(f"[ALERT] {text}")
            return
        try:
            url = TELEGRAM_API.format(token=self.token)
            httpx.post(url, json={"chat_id": self.chat_id, "text": text,
                                  "parse_mode": "HTML"}, timeout=10)
        except Exception as e:
            log.error(f"Telegram alert failed: {e}")

    def signal_alert(
        self,
        symbol: str,
        signal: str,
        price: float,
        rsi: float,
        qty: int,
        stop: float,
        take_profit: float,
    ) -> None:
        """Alert on a new BUY or SELL signal."""
        emoji = "🟢" if signal == "BUY" else "🔴"
        msg = (
            f"{emoji} <b>{signal} {symbol}</b>\n"
            f"Price: ${price:.2f} | RSI: {rsi:.1f}\n"
            f"Qty: {qty} | Stop: ${stop:.2f} | TP: ${take_profit:.2f}"
        )
        log.info(msg)
        self._send(msg)

    def trade_closed_alert(
        self,
        symbol: str,
        side: str,
        entry: float,
        exit_price: float,
        pnl: float,
        exit_reason: str,
        account_value: float,
    ) -> None:
        """Alert when a trade is closed (RSI signal, stop loss, or take profit)."""
        emoji = "✅" if pnl >= 0 else "❌"
        msg = (
            f"{emoji} <b>CLOSED {symbol}</b> [{exit_reason}]\n"
            f"Entry: ${entry:.2f} → Exit: ${exit_price:.2f}\n"
            f"P&L: ${pnl:+.2f} | Account: ${account_value:,.2f}"
        )
        log.info(msg)
        self._send(msg)

    def heartbeat(self, symbol: str, rsi: float, price: float, account: float) -> None:
        """Hourly status ping."""
        msg = (
            f"💓 <b>Heartbeat</b> — {symbol}\n"
            f"Price: ${price:.2f} | RSI: {rsi:.1f} | Acct: ${account:,.2f}"
        )
        log.info(msg)
        self._send(msg)

    def error_alert(self, error: str) -> None:
        """Alert on a bot error."""
        msg = f"⚠️ <b>Bot Error</b>\n{error}"
        log.error(msg)
        self._send(msg)
