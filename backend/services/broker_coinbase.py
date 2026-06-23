"""
broker_coinbase.py
Coinbase Advanced Trade broker adapter.
Same interface as broker.py.
Set COINBASE_SANDBOX=true for paper trading.
"""
from __future__ import annotations
import os
import uuid
import logging
import pandas as pd
from datetime import datetime, timedelta
from coinbase.rest import RESTClient

log = logging.getLogger(__name__)


def to_coinbase_symbol(symbol: str) -> str:
    """BTC/USD → BTC-USDC"""
    base = symbol.split("/")[0]
    return f"{base}-USDC"


class CoinbaseBroker:

    def __init__(self, sandbox: bool = True, dry_run: bool = False):
        self.dry_run = dry_run
        self.sandbox = sandbox
        self.client = None
        if not dry_run:
            try:
                self.client = RESTClient(
                    api_key=os.environ["COINBASE_KEY"],
                    api_secret=os.environ["COINBASE_SECRET"],
                )
                log.info(
                    f"Coinbase broker ready — sandbox={sandbox}"
                )
            except Exception as e:
                log.error(f"Coinbase init failed: {e}")

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_account_value(self) -> float:
        if self.dry_run or not self.client:
            return 10_000.0
        try:
            accounts = self.client.get_accounts()
            return sum(
                float(a.available_balance.value)
                for a in accounts.accounts
                if a.currency in ("USD", "USDC")
            )
        except Exception as e:
            log.error(f"get_account_value: {e}")
            return 0.0

    def get_buying_power(self) -> float:
        return self.get_account_value()

    def can_afford(self, price: float, qty: float) -> bool:
        return self.get_buying_power() >= price * qty

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def has_position(self, symbol: str) -> bool:
        if self.dry_run or not self.client:
            return False
        try:
            base = symbol.split("/")[0]
            accounts = self.client.get_accounts()
            for a in accounts.accounts:
                if a.currency == base:
                    return float(a.available_balance.value) > 0
            return False
        except Exception:
            return False

    def is_supported_symbol(self, symbol: str) -> bool:
        """All /USD symbols are valid on Coinbase."""
        return symbol.endswith("/USD") or "/" not in symbol

    # ------------------------------------------------------------------
    # Price data
    # ------------------------------------------------------------------

    def get_latest_price(self, symbol: str) -> float:
        if self.dry_run or not self.client:
            return 0.0
        try:
            product_id = to_coinbase_symbol(symbol)
            ticker = self.client.get_best_bid_ask(
                product_ids=[product_id]
            )
            return float(
                ticker.pricebooks[0].bids[0].price
            )
        except Exception as e:
            log.error(f"get_latest_price: {e}")
            return 0.0

    def get_recent_closes(
        self, symbol: str, limit: int = 50, interval: str = "1h"
    ) -> pd.Series:
        if self.dry_run or not self.client:
            return pd.Series(dtype=float)
        try:
            granularity_map = {
                "1m":  "ONE_MINUTE",
                "5m":  "FIVE_MINUTE",
                "15m": "FIFTEEN_MINUTE",
                "30m": "THIRTY_MINUTE",
                "1h":  "ONE_HOUR",
                "4h":  "FOUR_HOUR",
                "1d":  "ONE_DAY",
            }
            hours_back = {
                "1m": limit / 60, "5m": limit / 12,
                "15m": limit / 4, "30m": limit / 2,
                "1h": limit,      "4h": limit * 4,
                "1d": limit * 24,
            }
            end = datetime.utcnow()
            start = end - timedelta(
                hours=hours_back.get(interval, limit)
            )
            candles = self.client.get_candles(
                product_id=to_coinbase_symbol(symbol),
                start=int(start.timestamp()),
                end=int(end.timestamp()),
                granularity=granularity_map.get(
                    interval, "ONE_HOUR"
                ),
            )
            closes = [float(c.close) for c in candles.candles]
            closes.reverse()
            return pd.Series(closes[-limit:])
        except Exception as e:
            log.error(f"get_recent_closes: {e}")
            return pd.Series(dtype=float)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def place_market_order(
        self, symbol: str, qty: float, side: str
    ) -> bool:
        if self.dry_run:
            log.info(f"[DRY RUN] {side} {qty} {symbol}")
            return True
        if not self.client:
            return False
        try:
            self.client.create_order(
                client_order_id=str(uuid.uuid4()),
                product_id=to_coinbase_symbol(symbol),
                side=side,
                order_configuration={
                    "market_market_ioc": {
                        "base_size": str(round(qty, 6))
                    }
                },
            )
            log.info(
                f"Coinbase order placed: {side} {qty} {symbol}"
            )
            return True
        except Exception as e:
            log.error(f"Coinbase order failed: {e}")
            return False

    def close_position(self, symbol: str) -> bool:
        if self.dry_run:
            log.info(f"[DRY RUN] close {symbol}")
            return True
        if not self.client:
            return False
        try:
            base = symbol.split("/")[0]
            accounts = self.client.get_accounts()
            qty = 0.0
            for a in accounts.accounts:
                if a.currency == base:
                    qty = float(a.available_balance.value)
                    break
            if qty <= 0:
                log.warning(f"No {base} to sell")
                return False
            return self.place_market_order(symbol, qty, "SELL")
        except Exception as e:
            log.error(f"close_position: {e}")
            return False
