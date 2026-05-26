"""
stream.py
Connects to Alpaca's real-time crypto data stream via WebSocket.
Receives live price ticks and pushes them to the dashboard.
Runs in a background thread alongside the bot loop.
"""
import asyncio
import logging
import os
import threading
from typing import Callable, Optional

log = logging.getLogger(__name__)


class PriceStreamer:
    """
    Streams real-time price data from Alpaca.
    Calls on_price(symbol, price, high, low, volume, timestamp) on every bar update.
    Works for both crypto and stocks.
    """

    def __init__(
        self,
        symbol: str,
        on_price: Callable,
        on_bar: Optional[Callable] = None,
    ):
        self.symbol = symbol
        self.on_price = on_price
        self.on_bar = on_bar
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        """Start the stream in a background thread."""
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"stream-{self.symbol}"
        )
        self._thread.start()
        log.info(f"Price stream started for {self.symbol}")

    def stop(self):
        self._stop.set()
        log.info(f"Price stream stopping for {self.symbol}")

    def _run(self):
        """Run the async stream in a new event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._stream())
        except Exception as e:
            log.error(f"Stream error: {e}")
        finally:
            loop.close()

    async def _stream(self):
        from services.broker import is_crypto

        if is_crypto(self.symbol):
            await self._stream_crypto()
        else:
            await self._stream_stock()

    async def _stream_crypto(self):
        """Stream real-time crypto bars from Alpaca."""
        try:
            from alpaca.data.live.crypto import CryptoDataStream

            stream = CryptoDataStream(
                api_key=os.environ["ALPACA_KEY"],
                secret_key=os.environ["ALPACA_SECRET"],
            )

            async def on_bar(bar):
                if self._stop.is_set():
                    return
                log.debug(f"Bar received: {self.symbol} ${bar.close:.2f}")

            async def on_quote(quote):
                """Called on every bid/ask update — true real-time."""
                if self._stop.is_set():
                    return
                mid = (float(quote.bid_price) + float(quote.ask_price)) / 2
                self.on_price(
                    symbol=self.symbol,
                    price=mid,
                    high=float(quote.ask_price),
                    low=float(quote.bid_price),
                    volume=None,
                    timestamp=quote.timestamp,
                )

            stream.subscribe_quotes(on_quote, self.symbol)
            stream.subscribe_bars(on_bar, self.symbol)
            log.info(f"Subscribed to {self.symbol} quotes + bars")
            await stream._run_forever()

        except Exception as e:
            log.error(f"Crypto stream error: {e}", exc_info=True)

    async def _stream_stock(self):
        """Stream real-time stock bars from Alpaca."""
        try:
            from alpaca.data.live.stock import StockDataStream

            stream = StockDataStream(
                api_key=os.environ["ALPACA_KEY"],
                secret_key=os.environ["ALPACA_SECRET"],
            )

            async def on_bar(bar):
                if self._stop.is_set():
                    return
                self.on_price(
                    symbol=self.symbol,
                    price=float(bar.close),
                    high=float(bar.high),
                    low=float(bar.low),
                    volume=float(bar.volume),
                    timestamp=bar.timestamp,
                )

            stream.subscribe_bars(on_bar, self.symbol)
            log.info(f"Subscribed to {self.symbol} bars")
            await stream._run_forever()

        except Exception as e:
            log.error(f"Stock stream error: {e}", exc_info=True)
