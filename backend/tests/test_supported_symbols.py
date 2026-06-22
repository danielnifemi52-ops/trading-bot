import os
# Set dummy environment variables before importing Broker or other services
os.environ["ALPACA_KEY"] = "dummy_key"
os.environ["ALPACA_SECRET"] = "dummy_secret"

import pytest
from unittest.mock import MagicMock, patch
from services.broker import Broker, SUPPORTED_CRYPTO
from routers.telegram import execute_buy


def test_is_supported_symbol_crypto():
    """Verify is_supported_symbol returns correctly for crypto pairs."""
    broker = Broker(dry_run=True)
    
    # Supported crypto
    assert broker.is_supported_symbol("BTC/USD") is True
    assert broker.is_supported_symbol("ETH/USD") is True
    
    # Unsupported crypto
    assert broker.is_supported_symbol("BNB/USD") is False
    assert broker.is_supported_symbol("SOLANA/USD") is False


def test_is_supported_symbol_stock():
    """Verify is_supported_symbol queries Alpaca client for stocks."""
    broker = Broker(dry_run=False)
    broker.client = MagicMock()
    
    # Mock asset object
    mock_asset = MagicMock()
    mock_asset.tradable = True
    broker.client.get_asset.return_value = mock_asset
    
    # Tradable stock
    assert broker.is_supported_symbol("AAPL") is True
    broker.client.get_asset.assert_called_with("AAPL")
    
    # Non-tradable stock
    mock_asset.tradable = False
    assert broker.is_supported_symbol("AAPL") is False
    
    # Exception handling
    broker.client.get_asset.side_effect = Exception("Not found")
    assert broker.is_supported_symbol("UNKNOWN") is False


def test_place_market_order_validation():
    """Verify place_market_order validates symbol before submission."""
    broker = Broker(dry_run=False)
    broker.client = MagicMock()
    
    # Unsupported crypto should be rejected directly
    assert broker.place_market_order("BNB/USD", 1.0, "BUY") is False
    broker.client.submit_order.assert_not_called()
    
    # Supported crypto should be accepted and submitted
    broker.is_supported_symbol = MagicMock(return_value=True)
    # Mock the submission
    broker.client.submit_order.return_value = MagicMock()
    assert broker.place_market_order("BTC/USD", 1.0, "BUY") is True
    broker.client.submit_order.assert_called_once()


@pytest.mark.asyncio
async def test_telegram_execute_buy_unsupported_symbol():
    """Verify Telegram execute_buy rejects unsupported symbol and notifies user."""
    broker = Broker(dry_run=False)
    # Mock is_supported_symbol to return False
    broker.is_supported_symbol = MagicMock(return_value=False)
    broker.has_position = MagicMock()
    broker.place_market_order = MagicMock()
    
    alerter = MagicMock()
    
    # Execute buy on unsupported symbol
    await execute_buy(
        broker=broker,
        alerter=alerter,
        symbol="BNB/USD",
        price=100.0,
        qty=1.0,
        message_id=12345
    )
    
    # Should edit message with unsupported error
    alerter.edit_message.assert_called_once()
    args, kwargs = alerter.edit_message.call_args
    assert args[0] == 12345
    assert "Symbol not supported" in args[1]
    assert "BNB/USD" in args[1]
    
    # Should not check position or place order
    broker.has_position.assert_not_called()
    broker.place_market_order.assert_not_called()
