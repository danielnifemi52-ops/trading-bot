"""
broker.py
Thin wrapper around Alpaca TradingClient.
Supports stock symbols such as AAPL and crypto symbols such as BTC/USD.
All broker interactions go through this class.
Never call alpaca-py directly from routers or the bot runner.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest

    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    log.warning("alpaca-py not installed - broker running in dry-run mode only")

try:
    from alpaca.data.historical.crypto import CryptoHistoricalDataClient

    CRYPTO_DATA_AVAILABLE = True
except ImportError:
    CRYPTO_DATA_AVAILABLE = False


SUPPORTED_CRYPTO = {
    "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD",
    "DOGE/USD", "SHIB/USD", "LTC/USD", "BCH/USD",
    "LINK/USD", "UNI/USD", "AAVE/USD", "CRV/USD",
    "XTZ/USD", "BAT/USD", "MKR/USD", "SUSHI/USD",
    "YFI/USD", "GRT/USD", "SNX/USD", "ALGO/USD",
}


def is_crypto(symbol: str) -> bool:
    """Return True for Alpaca crypto pair symbols such as BTC/USD."""
    return "/" in (symbol or "")


class Broker:
    """
    Wraps Alpaca. All methods are synchronous and safe to call from threads.
    Set dry_run=True to simulate all orders without touching the broker.
    """

    def __init__(self, paper: bool = True, dry_run: bool = False):
        """Initialise the broker client, or enter dry-run mode."""
        self.dry_run = dry_run
        self.client = None
        self.crypto_data_client = None

        if not dry_run and ALPACA_AVAILABLE:
            self.client = TradingClient(
                api_key=os.environ["ALPACA_KEY"],
                secret_key=os.environ["ALPACA_SECRET"],
                paper=paper,
            )
            log.info(f"Broker initialised - paper={paper}")

        if not dry_run and CRYPTO_DATA_AVAILABLE:
            self.crypto_data_client = CryptoHistoricalDataClient(
                api_key=os.environ["ALPACA_KEY"],
                secret_key=os.environ["ALPACA_SECRET"],
            )

    def is_supported_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported by Alpaca."""
        if is_crypto(symbol):
            return symbol in SUPPORTED_CRYPTO
        if not self.client:
            return False
        # For stocks, try to get asset info
        try:
            asset = self.client.get_asset(symbol)
            return asset.tradable
        except Exception:
            return False

    def get_account_value(self) -> float:
        """Return current portfolio value. Returns 10_000 in dry-run."""
        if self.dry_run or not self.client:
            return 10_000.0
        try:
            return float(self.client.get_account().portfolio_value)
        except Exception as e:
            log.error(f"get_account_value failed: {e}")
            return 0.0

    def has_position(self, symbol: str) -> bool:
        """Return True if there is an open position for this symbol."""
        if self.dry_run or not self.client:
            return False
        try:
            clean = symbol.replace("/", "")
            pos = self.client.get_open_position(clean)
            return pos is not None
        except Exception:
            return False

    def place_market_order(self, symbol: str, qty: float, side: str) -> bool:
        """
        Place a market order.
        Crypto quantities are fractional base-currency units.
        Stock quantities are whole shares.
        """
        if self.dry_run:
            log.info(f"[DRY RUN] {side} {qty} {symbol}")
            return True
        if not self.client:
            log.warning("Alpaca not configured - order skipped")
            return False

        # Validate symbol before placing order
        if not self.is_supported_symbol(symbol):
            log.error(
                f"{symbol} is not supported by Alpaca. "
                f"Order rejected."
            )
            return False
        try:
            side_enum = OrderSide.BUY if side == "BUY" else OrderSide.SELL
            if is_crypto(symbol):
                order = MarketOrderRequest(
                    symbol=symbol,
                    qty=round(float(qty), 6),
                    side=side_enum,
                    time_in_force=TimeInForce.GTC,
                )
            else:
                order = MarketOrderRequest(
                    symbol=symbol,
                    qty=int(qty),
                    side=side_enum,
                    time_in_force=TimeInForce.DAY,
                )
            self.client.submit_order(order)
            log.info(f"Order placed: {side} {qty} {symbol}")
            return True
        except Exception as e:
            log.error(f"Order failed: {e}")
            return False

    def close_position(self, symbol: str) -> bool:
        """Close the entire open position for this symbol."""
        if self.dry_run:
            log.info(f"[DRY RUN] Close position {symbol}")
            return True
        if not self.client:
            return False
        try:
            clean = symbol.replace("/", "")
            self.client.close_position(clean)
            log.info(f"Position closed: {symbol}")
            return True
        except Exception as e:
            log.error(f"close_position failed: {e}")
            return False

    def get_crypto_price(self, symbol: str) -> float:
        """Return the latest Alpaca crypto close price for a pair symbol."""
        if not self.crypto_data_client:
            return 0.0
        try:
            from alpaca.data.requests import CryptoLatestBarRequest

            req = CryptoLatestBarRequest(symbol_or_symbols=symbol)
            latest = self.crypto_data_client.get_crypto_latest_bar(req)
            if isinstance(latest, dict):
                return float(latest[symbol].close)
            return float(latest.close)
        except Exception as e:
            log.error(f"get_crypto_price failed: {e}")
            return 0.0
