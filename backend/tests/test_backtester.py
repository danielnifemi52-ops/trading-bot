"""
test_backtester.py
Unit tests for the backtester service.
Mocks yfinance downloads to ensure tests run fast and without internet dependencies.
"""
from unittest.mock import patch
import pandas as pd
import pytest

from models import BacktestRequest, BacktestResponse
from services.backtester import download_alpaca, download_crypto_alpaca, run_backtest


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
        with pytest.raises(ValueError, match="No data returned from yfinance for AAPL"):
            run_backtest(req)
        mock_sleep.assert_called_once_with(3)


def test_weekly_backtest_uses_yfinance():
    """Weekly backtests should stay on yfinance."""
    dates = pd.date_range(start="2022-01-01", periods=50, freq="W")
    prices = [100.0 + i for i in range(50)]
    mock_df = pd.DataFrame({"Close": prices}, index=dates)
    req = BacktestRequest(
        symbol="AAPL",
        start="2022-01-01",
        end="2023-01-01",
        interval="1wk",
    )

    with patch("services.backtester.yf.download", return_value=mock_df) as mock_yf, \
         patch("services.backtester.download_alpaca") as mock_alpaca:
        res = run_backtest(req)

        mock_yf.assert_called_once_with(
            "AAPL", start="2022-01-01", end="2023-01-01",
            interval="1wk", auto_adjust=True, progress=False
        )
        mock_alpaca.assert_not_called()
        assert len(res.equity_curve) == 50


def test_crypto_daily_backtest_uses_alpaca_not_yfinance():
    """Crypto backtests should use Alpaca even for daily intervals."""
    dates = pd.date_range(start="2022-01-01", periods=50)
    prices = [50_000.0] * 50
    mock_df = pd.DataFrame({"Close": prices}, index=dates)
    req = BacktestRequest(
        symbol="BTC/USD",
        start="2022-01-01",
        end="2022-02-20",
        interval="1d",
        oversold=100.0,
        overbought=101.0,
    )

    with patch("services.backtester.download_crypto_alpaca", return_value=mock_df) as mock_crypto, \
         patch("services.backtester.download_alpaca") as mock_alpaca, \
         patch("services.backtester.yf.download") as mock_yf:
        res = run_backtest(req)

        mock_crypto.assert_called_once_with("BTC/USD", "2022-01-01", "2022-02-20", "1d")
        mock_alpaca.assert_not_called()
        mock_yf.assert_not_called()
        assert res.trades[0]["qty"] == pytest.approx(0.08)


def test_unsupported_interval_raises_value_error():
    """Unsupported intervals must not fall back to yfinance."""
    req = BacktestRequest(
        symbol="AAPL",
        start="2022-01-01",
        end="2022-01-02",
        interval="30m",
    )

    with patch("services.backtester.yf.download") as mock_yf, \
         patch("services.backtester.download_alpaca") as mock_alpaca:
        with pytest.raises(ValueError, match="Unsupported interval '30m'"):
            run_backtest(req)
        mock_yf.assert_not_called()
        mock_alpaca.assert_not_called()


@pytest.mark.parametrize("interval", ["1h", "15m", "5m"])
def test_intraday_backtest_uses_alpaca_not_yfinance(interval):
    """Intraday backtests must use Alpaca instead of yfinance."""
    dates = pd.date_range(start="2022-01-01 09:30", periods=50, freq="h")
    prices = [100.0 + i for i in range(50)]
    mock_df = pd.DataFrame({"Close": prices}, index=dates)

    req = BacktestRequest(
        symbol="AAPL",
        start="2022-01-01",
        end="2022-02-20",
        interval=interval,
        rsi_period=14,
        oversold=30.0,
        overbought=70.0,
        stop_loss_pct=5.0,
        take_profit_pct=10.0,
        start_capital=10000.0,
    )

    with patch("services.backtester.download_alpaca", return_value=mock_df) as mock_alpaca, \
         patch("services.backtester.yf.download") as mock_yf:
        res = run_backtest(req)

        mock_alpaca.assert_called_once_with("AAPL", "2022-01-01", "2022-02-20", interval)
        mock_yf.assert_not_called()
        assert isinstance(res, BacktestResponse)
        assert len(res.equity_curve) == 50


def test_intraday_empty_data_raises_alpaca_error():
    """Empty Alpaca intraday responses must return a provider-specific error."""
    req = BacktestRequest(
        symbol="AAPL",
        start="2022-01-01",
        end="2022-01-02",
        interval="1h",
    )

    with patch("services.backtester.download_alpaca", return_value=pd.DataFrame()), \
         patch("services.backtester.yf.download") as mock_yf:
        with pytest.raises(ValueError, match="No data returned from Alpaca for AAPL"):
            run_backtest(req)
        mock_yf.assert_not_called()


def test_download_alpaca_requires_credentials():
    """Intraday Alpaca downloads need API credentials in the environment."""
    with patch.dict("services.backtester.os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="ALPACA_KEY and ALPACA_SECRET"):
            download_alpaca("AAPL", "2022-01-01", "2022-01-02", "1h")


def test_download_crypto_alpaca_requires_credentials():
    """Crypto Alpaca downloads need API credentials in the environment."""
    with patch.dict("services.backtester.os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="ALPACA_KEY and ALPACA_SECRET"):
            download_crypto_alpaca("BTC/USD", "2022-01-01", "2022-01-02", "1d")


@pytest.mark.parametrize(
    ("interval", "expected_timeframe"),
    [("1h", "1Hour"), ("15m", "15Min"), ("5m", "5Min")],
)
def test_download_alpaca_builds_intraday_timeframe(interval, expected_timeframe):
    """Alpaca requests must use the correct timeframe for each intraday interval."""
    mock_df = pd.DataFrame(
        {"close": [100.0], "open": [99.0]},
        index=pd.MultiIndex.from_product([["AAPL"], pd.date_range("2022-01-01", periods=1)]),
    )
    mock_bars = type("MockBars", (), {"df": mock_df})()

    with patch.dict(
        "services.backtester.os.environ",
        {"ALPACA_KEY": "key", "ALPACA_SECRET": "secret"},
        clear=True,
    ), patch("services.backtester.StockHistoricalDataClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = mock_bars

        df = download_alpaca("AAPL", "2022-01-01", "2022-01-02", interval)

        mock_client_cls.assert_called_once_with("key", "secret")
        req = mock_client.get_stock_bars.call_args.args[0]
        assert req.symbol_or_symbols == "AAPL"
        assert req.timeframe.value == expected_timeframe
        assert list(df.columns) == ["Close", "Open"]
