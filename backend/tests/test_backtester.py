"""
test_backtester.py
Unit tests for the backtester service.
Mocks Alpaca downloads to ensure tests run fast and without internet dependencies.
"""
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
import os

from models import BacktestRequest, BacktestResponse
from services.backtester import (
    get_timeframe,
    download_stock_alpaca,
    download_crypto_alpaca,
    download_data,
    run_backtest,
)


def test_get_timeframe():
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    tf = get_timeframe("1m")
    assert tf.amount == 1
    assert tf.unit == TimeFrameUnit.Minute

    tf = get_timeframe("1h")
    assert tf.amount == 1
    assert tf.unit == TimeFrameUnit.Hour

    tf = get_timeframe("1d")
    assert tf.amount == 1
    assert tf.unit == TimeFrameUnit.Day


def test_backtest_run_success():
    """Test that a basic backtest runs and computes correct stats with mocked data."""
    dates = pd.date_range(start="2022-01-01", periods=50)
    prices = [100.0 + i for i in range(50)]
    mock_df = pd.DataFrame({"Close": prices}, index=dates)

    req = BacktestRequest(
        symbol="AAPL",
        start="2022-01-01",
        end="2022-02-20",
        interval="1d",
        rsi_period=14,
        oversold=30.0,
        overbought=70.0,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        start_capital=10000.0,
    )

    with patch("services.backtester.download_data", return_value=mock_df) as mock_dl:
        res = run_backtest(req)
        
        mock_dl.assert_called_once_with("AAPL", "2022-01-01", "2022-02-20", "1d")

        assert isinstance(res, BacktestResponse)
        assert res.symbol == "AAPL"
        assert res.start == "2022-01-01"
        assert res.end == "2022-02-20"
        
        assert res.stats.total_trades >= 0
        assert 0.0 <= res.stats.win_rate <= 1.0
        assert isinstance(res.trades, list)
        assert isinstance(res.equity_curve, list)
        assert len(res.equity_curve) == 50


def test_backtest_run_empty_data_raises_value_error():
    """Test that empty data raises ValueError."""
    req = BacktestRequest(
        symbol="AAPL",
        start="2022-01-01",
        end="2022-02-20",
        interval="1d",
    )

    with patch("services.backtester.download_data", side_effect=ValueError("No data returned")):
        with pytest.raises(ValueError, match="No data returned"):
            run_backtest(req)


def test_download_data_routes_correctly():
    """Test that download_data routes crypto vs stock appropriately."""
    mock_df = pd.DataFrame({"Close": [100.0]})
    with patch("services.backtester.download_crypto_alpaca", return_value=mock_df) as mock_crypto, \
         patch("services.backtester.download_stock_alpaca", return_value=mock_df) as mock_stock:
        
        # Crypto
        res = download_data("BTC/USD", "2022-01-01", "2022-01-02", "1d")
        mock_crypto.assert_called_once_with("BTC/USD", "2022-01-01", "2022-01-02", "1d")
        mock_stock.assert_not_called()

        # Stock
        mock_crypto.reset_mock()
        mock_stock.reset_mock()
        res_stock = download_data("AAPL", "2022-01-01", "2022-01-02", "1d")
        mock_stock.assert_called_once_with("AAPL", "2022-01-01", "2022-01-02", "1d")
        mock_crypto.assert_not_called()


@patch.dict(os.environ, {"ALPACA_KEY": "fake_key", "ALPACA_SECRET": "fake_secret"})
def test_download_stock_alpaca_api_call():
    """Test download_stock_alpaca builds request and calls client."""
    mock_df = pd.DataFrame({"close": [100.0], "open": [99.0]}, index=pd.MultiIndex.from_product([["AAPL"], pd.date_range("2022-01-01", periods=1)]))
    mock_bars = MagicMock()
    mock_bars.df = mock_df

    with patch("services.backtester.StockHistoricalDataClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = mock_bars

        df = download_stock_alpaca("AAPL", "2022-01-01", "2022-01-02", "1d")
        
        mock_client_cls.assert_called_once_with(api_key="fake_key", secret_key="fake_secret")
        req = mock_client.get_stock_bars.call_args[0][0]
        assert req.symbol_or_symbols == "AAPL"
        assert df.columns.tolist() == ["Close", "Open"]


@patch.dict(os.environ, {"ALPACA_KEY": "fake_key", "ALPACA_SECRET": "fake_secret"})
def test_download_crypto_alpaca_api_call():
    """Test download_crypto_alpaca builds request and calls client."""
    mock_df = pd.DataFrame({"close": [100.0], "open": [99.0]}, index=pd.MultiIndex.from_product([["BTC/USD"], pd.date_range("2022-01-01", periods=1)]))
    mock_bars = MagicMock()
    mock_bars.df = mock_df

    with patch("services.backtester.CryptoHistoricalDataClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_crypto_bars.return_value = mock_bars

        df = download_crypto_alpaca("BTC/USD", "2022-01-01", "2022-01-02", "1d")
        
        mock_client_cls.assert_called_once_with(api_key="fake_key", secret_key="fake_secret")
        req = mock_client.get_crypto_bars.call_args[0][0]
        assert req.symbol_or_symbols == "BTC/USD"
        assert df.columns.tolist() == ["Close", "Open"]
