"""
bot_runner.py
The live trading loop. Runs in a background thread started by FastAPI.
Reads/writes to the shared BotState singleton in state.py.
Never imports FastAPI — it is framework-agnostic.
"""
from __future__ import annotations
import time
import logging
import threading
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from core.strategy import (
    BotConfig, calc_rsi, get_signal,
    stop_price, take_profit_price, position_size,
)
from core.risk import should_stop_loss, should_take_profit
from services.broker import Broker
from services.alerts import SyncAlerter

log = logging.getLogger(__name__)

MARKET_OPEN  = dt_time(9, 30)
MARKET_CLOSE = dt_time(16, 0)
ET = ZoneInfo("America/New_York")


def market_is_open() -> bool:
    """Return True if NYSE market hours are currently active."""
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def fetch_prices(symbol: str, bars: int = 60) -> pd.Series:
    """Download recent hourly close prices. Raises ValueError if empty."""
    max_retries = 2
    for attempt in range(max_retries):
        df = yf.download(symbol, period="60d", interval="1h",
                         auto_adjust=True, progress=False)
        if not df.empty:
            break
        if attempt < max_retries - 1:
            log.warning(f"yfinance returned empty data for {symbol}, retrying in 60s...")
            time.sleep(60)
    if df.empty:
        raise ValueError(f"No price data for {symbol}")
    return df["Close"].squeeze().dropna().tail(bars)


class BotRunner:
    """
    Encapsulates one live bot instance.
    Call start() to begin — it spawns a daemon thread.
    Call stop() to request a clean shutdown.
    The caller must hold a reference to this object for the thread to stay alive.
    """

    def __init__(
        self,
        cfg: BotConfig,
        broker: Broker,
        alerter: SyncAlerter,
        on_tick=None,       # optional callback(price, rsi, signal, account)
        on_trade=None,      # optional callback(trade_dict)
    ):
        """Initialise with config, broker, alerter, and optional callbacks."""
        self.cfg        = cfg
        self.broker     = broker
        self.alerter    = alerter
        self.on_tick    = on_tick
        self.on_trade   = on_trade
        self._stop_evt  = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_rsi: float | None    = None
        self.last_price: float | None  = None
        self.last_signal: str          = "HOLD"
        self.open_trade: dict | None   = None
        self._last_heartbeat: float    = 0.0

    def start(self) -> None:
        """Spawn the polling thread. Idempotent — safe to call twice."""
        if self._thread and self._thread.is_alive():
            log.warning("BotRunner.start() called but thread already running")
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="bot-loop")
        self._thread.start()
        log.info(f"Bot loop started for {self.cfg.symbol}")

    def stop(self) -> None:
        """Signal the loop to stop. Returns immediately; thread winds down on its own."""
        self._stop_evt.set()
        log.info("Bot stop requested")

    def is_running(self) -> bool:
        """Return True if the bot thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        """Main loop — runs until stop() is called."""
        while not self._stop_evt.is_set():
            try:
                self._tick()
            except Exception as e:
                log.error(f"Bot tick error: {e}", exc_info=True)
                try:
                    self.alerter.error_alert(str(e))
                except Exception:
                    pass
            # Sleep in 1-second increments for fast shutdown response
            for _ in range(self.cfg.poll_interval_seconds):
                if self._stop_evt.is_set():
                    break
                time.sleep(1)
        log.info("Bot loop exited cleanly")

    def _tick(self) -> None:
        """One bot tick — fetch price, compute RSI, act on signal."""
        if not market_is_open():
            return

        prices  = fetch_prices(self.cfg.symbol)
        rsi_ser = calc_rsi(prices, self.cfg.rsi_period)
        rsi     = float(rsi_ser.iloc[-1])
        price   = float(prices.iloc[-1])
        signal  = get_signal(rsi, self.cfg)
        acct    = self.broker.get_account_value()
        has_pos = self.broker.has_position(self.cfg.symbol)

        self.last_rsi    = rsi
        self.last_price  = price

        log.info(f"{self.cfg.symbol} ${price:.2f}  RSI={rsi:.1f}  {signal}  acct=${acct:,.2f}")

        if self.on_tick:
            self.on_tick(price=price, rsi=rsi, signal=signal, account=acct)

        # ── BUY ─────────────────────────────────────────────────────────
        if signal == "BUY" and not has_pos and self.last_signal != "BUY":
            qty = position_size(acct, price, self.cfg)
            sl  = stop_price(price, self.cfg)
            tp  = take_profit_price(price, self.cfg)
            if qty > 0:
                if self.broker.place_market_order(self.cfg.symbol, qty, "BUY"):
                    self.open_trade = {"entry": price, "qty": qty, "sl": sl, "tp": tp}
                    self.alerter.signal_alert(
                        symbol=self.cfg.symbol, signal="BUY",
                        price=price, rsi=rsi, qty=qty, stop=sl, take_profit=tp
                    )
                    if self.on_trade:
                        self.on_trade({"side": "BUY", "price": price, "qty": qty,
                                       "rsi": rsi, "symbol": self.cfg.symbol})

        # ── SELL via RSI signal ──────────────────────────────────────────
        elif signal == "SELL" and has_pos and self.last_signal != "SELL":
            if self.broker.close_position(self.cfg.symbol) and self.open_trade:
                pnl = (price - self.open_trade["entry"]) * self.open_trade["qty"]
                self.alerter.trade_closed_alert(
                    symbol=self.cfg.symbol, side="SELL",
                    entry=self.open_trade["entry"], exit_price=price,
                    pnl=pnl, exit_reason="RSI_SIGNAL", account_value=acct
                )
                if self.on_trade:
                    self.on_trade({"side": "SELL", "price": price,
                                   "qty": self.open_trade["qty"], "pnl": pnl,
                                   "exit_reason": "RSI_SIGNAL", "symbol": self.cfg.symbol})
                self.open_trade = None

        # ── SELL via stop loss ───────────────────────────────────────────
        elif has_pos and self.open_trade:
            if should_stop_loss(price, self.open_trade["entry"], self.cfg):
                if self.broker.close_position(self.cfg.symbol):
                    pnl = (price - self.open_trade["entry"]) * self.open_trade["qty"]
                    self.alerter.trade_closed_alert(
                        symbol=self.cfg.symbol, side="SELL",
                        entry=self.open_trade["entry"], exit_price=price,
                        pnl=pnl, exit_reason="STOP_LOSS", account_value=acct
                    )
                    if self.on_trade:
                        self.on_trade({"side": "SELL", "price": price,
                                       "qty": self.open_trade["qty"], "pnl": pnl,
                                       "exit_reason": "STOP_LOSS", "symbol": self.cfg.symbol})
                    self.open_trade = None

            elif should_take_profit(price, self.open_trade["entry"], self.cfg):
                if self.broker.close_position(self.cfg.symbol):
                    pnl = (price - self.open_trade["entry"]) * self.open_trade["qty"]
                    self.alerter.trade_closed_alert(
                        symbol=self.cfg.symbol, side="SELL",
                        entry=self.open_trade["entry"], exit_price=price,
                        pnl=pnl, exit_reason="TAKE_PROFIT", account_value=acct
                    )
                    if self.on_trade:
                        self.on_trade({"side": "SELL", "price": price,
                                       "qty": self.open_trade["qty"], "pnl": pnl,
                                       "exit_reason": "TAKE_PROFIT", "symbol": self.cfg.symbol})
                    self.open_trade = None

        self.last_signal = signal

        # ── Hourly heartbeat ─────────────────────────────────────────────
        if time.time() - self._last_heartbeat > 3600:
            self.alerter.heartbeat(symbol=self.cfg.symbol, rsi=rsi,
                                   price=price, account=acct)
            self._last_heartbeat = time.time()
