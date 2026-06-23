"""
broker_factory.py
Automatically routes to the correct broker based on symbol.
Crypto (contains "/") → Binance
Stocks/ETFs           → Alpaca
No manual config needed. Detects from symbol automatically.
"""
from __future__ import annotations
import logging
import os

log = logging.getLogger(__name__)


def get_broker(symbol: str = "", dry_run: bool = False):
    """
    Return the correct broker for the given symbol.
    Crypto symbols contain "/" e.g. BTC/USD → Binance
    Stock symbols e.g. AAPL → Alpaca
    """
    if "/" in symbol:
        log.info(f"Symbol {symbol!r} is crypto → using Binance")
        from services.broker_binance import BinanceBroker
        testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        return BinanceBroker(testnet=testnet, dry_run=dry_run)
    else:
        log.info(f"Symbol {symbol!r} is stock/ETF → using Alpaca")
        from services.broker import Broker
        paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        return Broker(paper=paper, dry_run=dry_run)
