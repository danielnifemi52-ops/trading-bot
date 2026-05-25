"""
test_backtester.py
Unit tests for the backtester service.
Mocks yfinance downloads to ensure tests run fast and without internet dependencies.
"""
from unittest.mock import patch
import pandas as pd
import pytest

from models import BacktestRequest, BacktestResponse
from services.backtester import run_backtest


def test_backtest_run_success():
    """Test that a basic backtest runs and computes correct stats with mocked data."""
    # Generate 50 days of increasing prices from 100 to 149
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

    with patch("services.backtester.yf.download", return_value=mock_df) as mock_yf:
        res = run_backtest(req)
        
        # Verify yfinance was called with correct parameters
        mock_yf.assert_called_once_with(
            "AAPL", start="2022-01-01", end="2022-02-20",
            interval="1d", auto_adjust=True, progress=False
        )

        # Check response fields
        assert isinstance(res, BacktestResponse)
        assert res.symbol == "AAPL"
        assert res.start == "2022-01-01"
        assert res.end == "2022-02-20"
        
        # Stats checks
        assert res.stats.total_trades >= 0
        assert 0.0 <= res.stats.win_rate <= 1.0
        assert isinstance(res.trades, list)
        assert isinstance(res.equity_curve, list)
        assert len(res.equity_curve) == 50


def test_backtest_run_empty_data_raises_value_error():
    """Test that empty yfinance data raises ValueError."""
    req = BacktestRequest(
        symbol="AAPL",
        start="2022-01-01",
        end="2022-02-20",
        interval="1d",
    )

    with patch("services.backtester.yf.download", return_value=pd.DataFrame()), \
         patch("services.backtester.time.sleep") as mock_sleep:
        with pytest.raises(ValueError, match="No price data for AAPL"):
            run_backtest(req)
        mock_sleep.assert_called_once_with(60)
