"""
bot_runner.py
The live trading loop. Runs in a background thread started by FastAPI.
Reads/writes to the shared BotState singleton in state.py.
Never imports FastAPI; it is framework-agnostic.
"""
from __future__ import annotations

import gc
import logging
import os
import threading
import time
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import psutil
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

log = logging.getLogger(__name__)

# ── Supported symbol sets ────────────────────────────────────────────────────
# Keep in sync with frontend/src/components/TickerSelect.jsx
ALPACA_CRYPTO = {
    "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "DOGE/USD",
    "SHIB/USD", "LTC/USD", "BCH/USD", "LINK/USD", "UNI/USD",
    "AAVE/USD", "CRV/USD",
}
ALPACA_STOCKS = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "AMD",  "NFLX", "V",
    "SPY",  "QQQ",  "IWM",  "DIA",  "VTI",
}


class UnsupportedSymbolError(ValueError):
    """Raised when a symbol is not supported by the configured data source."""
    pass

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


from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

def get_alpaca_timeframe(tf: str):
    mapping = {
        "1m":  TimeFrame(1,  TimeFrameUnit.Minute),
        "5m":  TimeFrame(5,  TimeFrameUnit.Minute),
        "15m": TimeFrame(15, TimeFrameUnit.Minute),
        "30m": TimeFrame(30, TimeFrameUnit.Minute),
        "1h":  TimeFrame(1,  TimeFrameUnit.Hour),
        "4h":  TimeFrame(4,  TimeFrameUnit.Hour),
        "1d":  TimeFrame(1,  TimeFrameUnit.Day),
    }
    return mapping.get(tf, TimeFrame(1, TimeFrameUnit.Hour))

def fetch_crypto_prices(
    symbol: str,
    bars: int = 200,
    timeframe: str = "1h",
) -> pd.Series:
    """
    Fetch crypto OHLCV bars from Alpaca.
    Symbol format: BTC/USD, ETH/USD, SOL/USD.
    Raises UnsupportedSymbolError immediately for unknown symbols.
    """
    # ── Guard: reject symbols Alpaca doesn't support ─────────────────────────
    if symbol not in ALPACA_CRYPTO:
        supported = ", ".join(sorted(ALPACA_CRYPTO))
        raise UnsupportedSymbolError(
            f"{symbol!r} is not supported by Alpaca crypto data. "
            f"Supported pairs: {supported}"
        )

    try:
        import os
        from alpaca.data.historical.crypto import CryptoHistoricalDataClient
        from alpaca.data.requests import CryptoBarsRequest

        client = CryptoHistoricalDataClient(
            api_key=os.environ["ALPACA_KEY"],
            secret_key=os.environ["ALPACA_SECRET"],
        )
        req = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=get_alpaca_timeframe(timeframe),
            limit=bars,
        )
        bars_data = client.get_crypto_bars(req)
        df = bars_data.df
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index(level=0, drop=True)
        if df.empty:
            raise ValueError(f"No price data returned for {symbol}")
        return df["close"].squeeze().dropna().tail(bars)
    except UnsupportedSymbolError:
        raise  # already descriptive — don't wrap
    except Exception as e:
        log.error(f"fetch_crypto_prices failed for {symbol}: {e}")
        raise ValueError(f"Could not fetch crypto data for {symbol}: {e}")


def fetch_prices(symbol: str, bars: int = 200, timeframe: str = "1h") -> pd.Series:
    """Auto-detect crypto vs stock and download recent close prices."""
    if is_crypto(symbol):
        return fetch_crypto_prices(symbol, bars, timeframe)

    max_retries = 2
    df = pd.DataFrame()
    yf_intervals = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "4h": "1h", "1d": "1d"
    }
    yf_interval = yf_intervals.get(timeframe, "1h")
    period = "60d"
    if yf_interval in ["1m", "5m", "15m", "30m"]:
        period = "7d" if yf_interval != "1m" else "1d"

    for attempt in range(max_retries):
        df = yf.download(
            symbol,
            period=period,
            interval=yf_interval,
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
    ):
        """Initialise with config, broker, alerter, and optional callbacks."""
        self.cfg = cfg
        # Auto-update poll interval based on timeframe
        TIMEFRAME_POLL_MAP = {
            "1m":  30,
            "5m":  60,
            "15m": 60,
            "30m": 120,
            "1h":  300,
            "4h":  600,
            "1d":  3600,
        }
        if hasattr(self.cfg, "timeframe") and self.cfg.timeframe in TIMEFRAME_POLL_MAP:
            self.cfg.poll_interval_seconds = TIMEFRAME_POLL_MAP[self.cfg.timeframe]

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

    def start(self) -> None:
        """Spawn the polling thread. Idempotent; safe to call twice."""
        if self._thread and self._thread.is_alive():
            log.warning("BotRunner.start() called but thread already running")
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="bot-loop")
        self._thread.start()
        log.info(f"Bot loop started for {self.cfg.symbol}")

    def stop(self) -> None:
        """Signal the loop to stop and wait for the thread to exit cleanly."""
        self._stop_evt.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                log.warning("Bot thread did not stop cleanly")
        self._thread = None
        self.last_price = None
        self.last_rsi = None
        self.open_trade = None
        gc.collect()
        log.info("Bot stopped and memory cleared")

    def is_running(self) -> bool:
        """Return True if the bot thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def _check_memory(self) -> bool:
        """Returns True if memory was dangerously high and GC was triggered."""
        try:
            mem_mb = psutil.Process(os.getpid()).memory_info().rss / 1_048_576
            if mem_mb > 450:
                log.warning(f"High memory: {mem_mb:.0f} MB — running GC")
                gc.collect()
                return True
        except Exception:
            pass
        return False

    def _loop(self) -> None:
        """Main loop; runs until stop() is called."""
        while not self._stop_evt.is_set():
            self._check_memory()
            try:
                self._tick()
            except Exception as e:
                log.error(f"Bot tick error: {e}", exc_info=True)
                try:
                    self.alerter.error_alert(str(e))
                except Exception:
                    pass
            # Force garbage collection after every tick
            gc.collect()
            for _ in range(self.cfg.poll_interval_seconds):
                if self._stop_evt.is_set():
                    break
                time.sleep(1)
        log.info("Bot loop exited cleanly")

    def _tick(self) -> None:
        """One bot tick: fetch prices via HTTP polling and execute signals."""
        symbol = self.cfg.symbol
        currently_open = market_is_open(symbol)

        # Detect market open/close transitions
        if hasattr(self, "_last_market_state"):
            if not self._last_market_state and currently_open:
                # Market just opened
                self.alerter.send(
                    f"🔔 *NYSE OPEN* — {symbol} is now trading\n"
                    f"Bot is actively watching for RSI signals"
                )
            elif self._last_market_state and not currently_open:
                # Market just closed
                self.alerter.send(
                    f"🔕 *NYSE CLOSED* — {symbol} stopped trading\n"
                    f"Next session: tomorrow 2:30 PM Lagos time"
                )
        self._last_market_state = currently_open

        try:
            prices = fetch_prices(
                self.cfg.symbol,
                bars=100,
                timeframe=getattr(self.cfg, "timeframe", "1h")
            )
        except UnsupportedSymbolError as e:
            msg = str(e)
            log.error(f"Unsupported symbol — stopping bot: {msg}")
            try:
                self.alerter.error_alert(
                    f"⛔ Bot stopped: {msg}. "
                    f"Please restart with a supported symbol."
                )
            except Exception:
                pass
            self.stop()  # clean shutdown — no more retries
            return
        except Exception as e:
            log.error(f"Tick error: {e}", exc_info=True)
            return

        try:
            rsi_ser = calc_rsi(prices, self.cfg.rsi_period)
            rsi     = float(rsi_ser.iloc[-1])
            price   = float(prices.iloc[-1])
            signal  = get_signal(rsi, self.cfg)
            acct    = self.broker.get_account_value()

            self.last_rsi    = rsi
            self.last_price  = price

            log.info(
                f"{self.cfg.symbol} ${price:.2f} "
                f"RSI={rsi:.1f} {signal}"
            )

            if self.on_tick:
                self.on_tick(
                    price=price,
                    rsi=rsi,
                    signal=signal,
                    account=acct,
                )

            if not market_is_open(self.cfg.symbol):
                self.last_signal = signal
                return

            self._execute_signal(
                signal, price, rsi, acct,
                self.broker.has_position(self.cfg.symbol)
            )

        except Exception as e:
            log.error(f"Tick error: {e}", exc_info=True)

        if time.time() - self._last_heartbeat > 3600:
            self.alerter.heartbeat(
                symbol=self.cfg.symbol,
                rsi=self.last_rsi or 50.0,
                price=self.last_price or 0.0,
                account=self.broker.get_account_value(),
            )
            self._last_heartbeat = time.time()

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
                self.alerter.signal_alert(
                    symbol=self.cfg.symbol,
                    signal="BUY",
                    price=price,
                    rsi=rsi,
                    qty=qty,
                    stop=sl,
                    take_profit=tp,
                )
                if self.broker.place_market_order(self.cfg.symbol, qty, "BUY"):
                    self.open_trade = {"entry": price, "qty": qty, "sl": sl, "tp": tp}
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
            if self.open_trade:
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
                if self.broker.close_position(self.cfg.symbol):
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
                if self.broker.close_position(self.cfg.symbol):
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
                if self.broker.close_position(self.cfg.symbol):
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
