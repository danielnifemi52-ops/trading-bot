"""
broker.py
Thin wrapper around Alpaca TradingClient.
All broker interactions go through this class.
Never call alpaca-py directly from routers or the bot runner.
"""
from __future__ import annotations
import os
import logging

log = logging.getLogger(__name__)

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    log.warning("alpaca-py not installed — broker running in dry-run mode only")


class Broker:
    """
    Wraps Alpaca. All methods are synchronous and safe to call from threads.
    Set dry_run=True to simulate all orders without touching the broker.
    """

    def __init__(self, paper: bool = True, dry_run: bool = False):
        """Initialise the broker client, or enter dry-run mode."""
        self.dry_run = dry_run
        self.client = None
        if not dry_run and ALPACA_AVAILABLE:
            self.client = TradingClient(
                api_key=os.environ["ALPACA_KEY"],
                secret_key=os.environ["ALPACA_SECRET"],
                paper=paper,
            )
            log.info(f"Broker initialised — paper={paper}")

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
            pos = self.client.get_open_position(symbol)
            return pos is not None
        except Exception:
            return False

    def place_market_order(self, symbol: str, qty: int, side: str) -> bool:
        """Place a market order. Returns True on success."""
        if self.dry_run:
            log.info(f"[DRY RUN] {side} {qty}x {symbol}")
            return True
        if not self.client:
            log.warning("Alpaca not configured — order skipped")
            return False
        try:
            self.client.submit_order(MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            ))
            log.info(f"Order placed: {side} {qty}x {symbol}")
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
            self.client.close_position(symbol)
            log.info(f"Position closed: {symbol}")
            return True
        except Exception as e:
            log.error(f"close_position failed: {e}")
            return False
