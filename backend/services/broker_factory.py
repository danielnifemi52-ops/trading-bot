"""
broker_factory.py
Returns the correct broker based on ACTIVE_BROKER env var.
The rest of the app never imports a specific broker directly.
"""
from __future__ import annotations
import os
import logging

log = logging.getLogger(__name__)


def get_broker(dry_run: bool = False):
    """
    Return configured broker instance.
    ACTIVE_BROKER: alpaca | binance | coinbase
    Defaults to alpaca if not set.
    """
    active = os.getenv("ACTIVE_BROKER", "alpaca").lower()
    log.info(f"Using broker: {active} (dry_run={dry_run})")

    if active == "binance":
        from services.broker_binance import BinanceBroker
        testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        return BinanceBroker(testnet=testnet, dry_run=dry_run)

    if active == "coinbase":
        from services.broker_coinbase import CoinbaseBroker
        sandbox = os.getenv("COINBASE_SANDBOX", "true").lower() == "true"
        return CoinbaseBroker(sandbox=sandbox, dry_run=dry_run)

    # Default: Alpaca
    from services.broker import Broker
    paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
    return Broker(paper=paper, dry_run=dry_run)
