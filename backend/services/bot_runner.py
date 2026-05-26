"""
bot_runner.py
The live trading loop. Runs in a background thread started by FastAPI.
Reads/writes to the shared BotState singleton in state.py.
Never imports FastAPI; it is framework-agnostic.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from core.risk import should_stop_loss, should_take_profit
from core.strategy import (
    BotConfig,
    calc_rsi,
    get_signal,
    position_size,
    stop_price,
    take_profit_price,
)
from services.alerts import SyncAlerter
from services.broker import Broker, is_crypto
from services.stream import PriceStreamer

log = logging.getLogger(__name__)

MARKET_OPEN = dt_time(9, 30)
MARKET_CLOSE = dt_time(16, 0)
ET = ZoneInfo("America/New_York")


def market_is_open(symbol: str = "") -> bool:
    """Crypto trades 24/7. Stocks only trade during NYSE hours."""
    if is_crypto(symbol):
        return True
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def fetch_crypto_prices(symbol: str, bars: int = 200) -> pd.Series:
    """
    Fetch crypto OHLCV bars from Alpaca.
    Symbol format: BTC/USD, ETH/USD, SOL/USD.
    """
    try:
        import os

        from alpaca.data.historical.crypto import CryptoHistoricalDataClient
        from alpaca.data.requests import CryptoBarsRequest
        from alpaca.data.timeframe import TimeFrame

        client = CryptoHistoricalDataClient(
            api_key=os.environ["ALPACA_KEY"],
            secret_key=os.environ["ALPACA_SECRET"],
        )
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=bars + 24)
        req = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Hour,
            start=start,
            end=end,
            limit=bars,
        )
        bars_data = client.get_crypto_bars(req)
        df = bars_data.df
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index(level=0, drop=True)
        if df.empty:
            raise ValueError(f"No price data for {symbol}")
        return df["close"].squeeze().dropna().tail(bars)
    except Exception as e:
        log.error(f"fetch_crypto_prices failed: {e}")
        raise ValueError(f"Could not fetch crypto data for {symbol}: {e}")


def fetch_prices(symbol: str, bars: int = 200) -> pd.Series:
    """Auto-detect crypto vs stock and download recent hourly close prices."""
    if is_crypto(symbol):
        return fetch_crypto_prices(symbol, bars)

    max_retries = 2
    df = pd.DataFrame()
    for attempt in range(max_retries):
        df = yf.download(
            symbol,
            period="60d",
            interval="1h",
            auto_adjust=True,
            prepost=False,
            progress=False,
        )
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
    Call start() to begin; it spawns a daemon thread.
    Call stop() to request a clean shutdown.
    The caller must hold a reference to this object for the thread to stay alive.
    """

    def __init__(
        self,
        cfg: BotConfig,
        broker: Broker,
        alerter: SyncAlerter,
        on_tick: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
        use_stream: bool = True,
    ):
        """Initialise with config, broker, alerter, and optional callbacks."""
        self.cfg = cfg
        self.broker = broker
        self.alerter = alerter
        self.on_tick = on_tick
        self.on_trade = on_trade
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_rsi: float | None = None
        self.last_price: float | None = None
        self.last_signal: str = "HOLD"
        self.open_trade: dict | None = None
        self._last_heartbeat: float = 0.0
        self._price_buffer: deque = deque(maxlen=500)
        self._streamer: Optional[PriceStreamer] = None
        self._use_stream = use_stream
        self._stream_active = False

    def start(self) -> None:
        """Spawn the polling thread. Idempotent; safe to call twice."""
        if self._thread and self._thread.is_alive():
            log.warning("BotRunner.start() called but thread already running")
            return
        self._stop_evt.clear()

        # Start real-time price stream if enabled
        if self._use_stream:
            try:
                self._streamer = PriceStreamer(
                    symbol=self.cfg.symbol,
                    on_price=self._on_stream_price,
                )
                self._streamer.start()
                self._stream_active = True
                log.info(f"Real-time stream started for {self.cfg.symbol}")
            except Exception as e:
                log.warning(f"Stream failed, falling back to polling: {e}")
                self._use_stream = False

        self._thread = threading.Thread(target=self._loop, daemon=True, name="bot-loop")
        self._thread.start()
        log.info(f"Bot loop started for {self.cfg.symbol}")

    def stop(self) -> None:
        """Signal the loop to stop. Returns immediately; thread winds down on its own."""
        if self._streamer:
            self._streamer.stop()
            self._stream_active = False
        self._stop_evt.set()
        log.info("Bot stop requested")

    def is_running(self) -> bool:
        """Return True if the bot thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def _on_stream_price(self, symbol, price, high, low, volume, timestamp):
        """
        Called by the streamer on every price tick.
        Updates last_price immediately for dashboard display.
        Adds price to buffer for RSI calculation.
        """
        self.last_price = price
        # Add to price buffer for RSI calculation
        self._price_buffer.append(price)

        # Broadcast to dashboard immediately if we have enough data
        if self.on_tick and len(self._price_buffer) >= self.cfg.rsi_period + 1:
            prices = pd.Series(list(self._price_buffer))
            rsi_ser = calc_rsi(prices, self.cfg.rsi_period)
            rsi = float(rsi_ser.iloc[-1]) if not pd.isna(rsi_ser.iloc[-1]) else 50.0
            self.last_rsi = rsi
            signal = get_signal(rsi, self.cfg)
            self.last_signal = signal
            acct = self.broker.get_account_value()
            self.on_tick(
                price=price, rsi=rsi, signal=signal, account=acct, source="stream"
            )

    def _loop(self) -> None:
        """Main loop; runs until stop() is called."""
        while not self._stop_evt.is_set():
            try:
                self._tick()
            except Exception as e:
                log.error(f"Bot tick error: {e}", exc_info=True)
                try:
                    self.alerter.error_alert(str(e))
                except Exception:
                    pass
            for _ in range(self.cfg.poll_interval_seconds):
                if self._stop_evt.is_set():
                    break
                time.sleep(1)
        log.info("Bot loop exited cleanly")

    def _tick(self) -> None:
        """
        One bot tick: in streaming mode, check buffer and execute signals.
        In polling mode, fetch prices and execute signals.
        """
        # If streaming, use price buffer for signal execution
        if self._use_stream and len(self._price_buffer) >= self.cfg.rsi_period + 1:
            self._execute_signal_from_buffer()
            return

        # Fallback: fetch prices via HTTP polling
        try:
            prices = fetch_prices(self.cfg.symbol)
            rsi_ser = calc_rsi(prices, self.cfg.rsi_period)
            rsi = float(rsi_ser.iloc[-1])
            price = float(prices.iloc[-1])
            signal = get_signal(rsi, self.cfg)
            acct = self.broker.get_account_value()

            self.last_rsi = rsi
            self.last_price = price

            log.info(f"{self.cfg.symbol} ${price:.2f} RSI={rsi:.1f} {signal}")

            if self.on_tick:
                self.on_tick(price=price, rsi=rsi, signal=signal, account=acct)

            self._execute_signal(signal, price, rsi, acct)

        except Exception as e:
            log.error(f"Data fetch error: {e}")

        if time.time() - self._last_heartbeat > 3600:
            self.alerter.heartbeat(
                symbol=self.cfg.symbol,
                rsi=self.last_rsi or 50.0,
                price=self.last_price or 0.0,
                account=self.broker.get_account_value(),
            )
            self._last_heartbeat = time.time()

    def _execute_signal_from_buffer(self):
        """Execute signal logic using prices from the streaming buffer."""
        prices = pd.Series(list(self._price_buffer))
        rsi_ser = calc_rsi(prices, self.cfg.rsi_period)
        rsi = float(rsi_ser.iloc[-1]) if not pd.isna(rsi_ser.iloc[-1]) else 50.0
        price = self.last_price or float(prices.iloc[-1])
        signal = get_signal(rsi, self.cfg)
        acct = self.broker.get_account_value()
        has_pos = self.broker.has_position(self.cfg.symbol)

        self._execute_signal(signal, price, rsi, acct, has_pos)

    def _execute_signal(self, signal, price, rsi, acct, has_pos=None):
        """Extracted trade execution logic."""
        if has_pos is None:
            has_pos = self.broker.has_position(self.cfg.symbol)

        # BUY signal
        if signal == "BUY" and not has_pos and self.last_signal != "BUY":
            qty = position_size(acct, price, self.cfg, crypto=is_crypto(self.cfg.symbol))
            sl = stop_price(price, self.cfg)
            tp = take_profit_price(price, self.cfg)
            if qty > 0:
                if self.broker.place_market_order(self.cfg.symbol, qty, "BUY"):
                    self.open_trade = {"entry": price, "qty": qty, "sl": sl, "tp": tp}
                    self.alerter.signal_alert(
                        symbol=self.cfg.symbol,
                        signal="BUY",
                        price=price,
                        rsi=rsi,
                        qty=qty,
                        stop=sl,
                        take_profit=tp,
                    )
                    if self.on_trade:
                        self.on_trade({
                            "side": "BUY",
                            "price": price,
                            "qty": qty,
                            "rsi": rsi,
                            "symbol": self.cfg.symbol,
                        })

        # SELL via RSI
        elif signal == "SELL" and has_pos and self.last_signal != "SELL":
            if self.broker.close_position(self.cfg.symbol) and self.open_trade:
                pnl = (price - self.open_trade["entry"]) * self.open_trade["qty"]
                self.alerter.trade_closed_alert(
                    symbol=self.cfg.symbol,
                    side="SELL",
                    entry=self.open_trade["entry"],
                    exit_price=price,
                    pnl=pnl,
                    exit_reason="RSI_SIGNAL",
                    account_value=acct,
                )
                if self.on_trade:
                    self.on_trade({
                        "side": "SELL",
                        "price": price,
                        "qty": self.open_trade["qty"],
                        "pnl": pnl,
                        "exit_reason": "RSI_SIGNAL",
                        "symbol": self.cfg.symbol,
                    })
                self.open_trade = None

        # Stop loss / take profit checks
        elif has_pos and self.open_trade:
            if should_stop_loss(price, self.open_trade["entry"], self.cfg):
                if self.broker.close_position(self.cfg.symbol):
                    pnl = (price - self.open_trade["entry"]) * self.open_trade["qty"]
                    self.alerter.trade_closed_alert(
                        symbol=self.cfg.symbol,
                        side="SELL",
                        entry=self.open_trade["entry"],
                        exit_price=price,
                        pnl=pnl,
                        exit_reason="STOP_LOSS",
                        account_value=acct,
                    )
                    if self.on_trade:
                        self.on_trade({
                            "side": "SELL",
                            "price": price,
                            "qty": self.open_trade["qty"],
                            "pnl": pnl,
                            "exit_reason": "STOP_LOSS",
                            "symbol": self.cfg.symbol,
                        })
                    self.open_trade = None

            elif should_take_profit(price, self.open_trade["entry"], self.cfg):
                if self.broker.close_position(self.cfg.symbol):
                    pnl = (price - self.open_trade["entry"]) * self.open_trade["qty"]
                    self.alerter.trade_closed_alert(
                        symbol=self.cfg.symbol,
                        side="SELL",
                        entry=self.open_trade["entry"],
                        exit_price=price,
                        pnl=pnl,
                        exit_reason="TAKE_PROFIT",
                        account_value=acct,
                    )
                    if self.on_trade:
                        self.on_trade({
                            "side": "SELL",
                            "price": price,
                            "qty": self.open_trade["qty"],
                            "pnl": pnl,
                            "exit_reason": "TAKE_PROFIT",
                            "symbol": self.cfg.symbol,
                        })
                    self.open_trade = None

        self.last_signal = signal
