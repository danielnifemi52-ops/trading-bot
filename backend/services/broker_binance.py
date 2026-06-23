"""
broker_binance.py
Binance broker adapter. Same interface as broker.py.
Supports BNB, ADA, XRP, MATIC and all Binance spot pairs.
Set BINANCE_TESTNET=true for paper trading.
"""
from __future__ import annotations
import os
import logging
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException

log = logging.getLogger(__name__)


def to_binance_symbol(symbol: str) -> str:
    """BNB/USD → BNBUSDT"""
    return symbol.replace("/USD", "USDT").replace("/", "")


class BinanceBroker:

    def __init__(self, testnet: bool = True, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = None
        if not dry_run:
            try:
                self.client = Client(
                    api_key=os.environ["BINANCE_KEY"],
                    api_secret=os.environ["BINANCE_SECRET"],
                    testnet=testnet,
                )
                log.info(f"Binance broker ready — testnet={testnet}")
            except Exception as e:
                log.error(f"Binance init failed: {e}")

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_account_value(self) -> float:
        if self.dry_run or not self.client:
            return 10_000.0
        try:
            balances = self.client.get_account()["balances"]
            return sum(
                float(b["free"]) + float(b["locked"])
                for b in balances if b["asset"] == "USDT"
            )
        except Exception as e:
            log.error(f"get_account_value: {e}")
            return 0.0

    def get_buying_power(self) -> float:
        if self.dry_run or not self.client:
            return 10_000.0
        try:
            balances = self.client.get_account()["balances"]
            return next(
                (float(b["free"]) for b in balances
                 if b["asset"] == "USDT"), 0.0
            )
        except Exception as e:
            log.error(f"get_buying_power: {e}")
            return 0.0

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
            balances = self.client.get_account()["balances"]
            qty = next(
                (float(b["free"]) for b in balances
                 if b["asset"] == base), 0.0
            )
            return qty > 0.0001
        except Exception:
            return False

    def is_supported_symbol(self, symbol: str) -> bool:
        """All Binance spot pairs ending in /USD are supported."""
        return symbol.endswith("/USD") or "/" not in symbol

    # ------------------------------------------------------------------
    # Price data
    # ------------------------------------------------------------------

    def get_latest_price(self, symbol: str) -> float:
        if self.dry_run or not self.client:
            return 0.0
        try:
            ticker = self.client.get_symbol_ticker(
                symbol=to_binance_symbol(symbol)
            )
            return float(ticker["price"])
        except Exception as e:
            log.error(f"get_latest_price: {e}")
            return 0.0

    def get_recent_closes(
        self, symbol: str, limit: int = 50, interval: str = "1h"
    ) -> pd.Series:
        if self.dry_run or not self.client:
            return pd.Series(dtype=float)
        try:
            interval_map = {
                "1m":  Client.KLINE_INTERVAL_1MINUTE,
                "5m":  Client.KLINE_INTERVAL_5MINUTE,
                "15m": Client.KLINE_INTERVAL_15MINUTE,
                "30m": Client.KLINE_INTERVAL_30MINUTE,
                "1h":  Client.KLINE_INTERVAL_1HOUR,
                "4h":  Client.KLINE_INTERVAL_4HOUR,
                "1d":  Client.KLINE_INTERVAL_1DAY,
            }
            klines = self.client.get_klines(
                symbol=to_binance_symbol(symbol),
                interval=interval_map.get(
                    interval, Client.KLINE_INTERVAL_1HOUR
                ),
                limit=limit,
            )
            return pd.Series([float(k[4]) for k in klines])
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
            bs = to_binance_symbol(symbol)
            if side == "BUY":
                self.client.order_market_buy(
                    symbol=bs, quantity=round(qty, 6)
                )
            else:
                self.client.order_market_sell(
                    symbol=bs, quantity=round(qty, 6)
                )
            log.info(f"Binance order placed: {side} {qty} {symbol}")
            return True
        except BinanceAPIException as e:
            log.error(f"Binance order failed: {e}")
            return False

    def close_position(self, symbol: str) -> bool:
        if self.dry_run:
            log.info(f"[DRY RUN] close {symbol}")
            return True
        if not self.client:
            return False
        try:
            base = symbol.split("/")[0]
            balances = self.client.get_account()["balances"]
            qty = next(
                (float(b["free"]) for b in balances
                 if b["asset"] == base), 0.0
            )
            if qty <= 0:
                log.warning(f"No {base} balance to sell")
                return False
            self.client.order_market_sell(
                symbol=to_binance_symbol(symbol),
                quantity=round(qty, 6),
            )
            log.info(f"Binance position closed: {symbol}")
            return True
        except BinanceAPIException as e:
            log.error(f"close_position: {e}")
            return False
