"""
test_broker_split.py
Unit tests for the automatic broker split routing (Alpaca vs Binance).
"""
import os
import pytest
from services.broker_factory import get_broker
from services.broker import Broker
from services.broker_binance import BinanceBroker


def test_get_broker_routing_for_stocks():
    """Verify that stock symbols like AAPL or TSLA route to the Alpaca Broker."""
    os.environ["ALPACA_KEY"] = "dummy_alpaca_key"
    os.environ["ALPACA_SECRET"] = "dummy_alpaca_secret"
    os.environ["ALPACA_PAPER"] = "true"

    broker = get_broker("AAPL", dry_run=True)
    assert isinstance(broker, Broker)
    assert broker.dry_run is True


def test_get_broker_routing_for_crypto():
    """Verify that crypto symbols containing '/' route to the Binance Broker."""
    os.environ["BINANCE_KEY"] = "dummy_binance_key"
    os.environ["BINANCE_SECRET"] = "dummy_binance_secret"
    os.environ["BINANCE_TESTNET"] = "true"

    broker = get_broker("BTC/USD", dry_run=True)
    assert isinstance(broker, BinanceBroker)
    assert broker.dry_run is True


def test_supported_symbol_check_binance():
    """Verify is_supported_symbol logic on BinanceBroker."""
    os.environ["BINANCE_KEY"] = "dummy_binance_key"
    os.environ["BINANCE_SECRET"] = "dummy_binance_secret"
    
    broker = BinanceBroker(testnet=True, dry_run=True)
    
    # Symbols ending with /USD are supported
    assert broker.is_supported_symbol("BTC/USD") is True
    assert broker.is_supported_symbol("ETH/USD") is True
    
    # Symbols not containing '/' (stocks) are supported by this check (routed to Alpaca at factory level)
    assert broker.is_supported_symbol("AAPL") is True
