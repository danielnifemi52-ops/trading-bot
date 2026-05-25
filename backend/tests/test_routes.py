"""
test_routes.py
FastAPI route tests using TestClient (synchronous).
These do not hit Alpaca or Telegram — broker is always dry_run.
"""
from fastapi.testclient import TestClient
from main import app
from db import init_db
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch

init_db()

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_market_data_downloads():
    """Mock market data downloads so route tests stay fast and offline."""
    dates = pd.date_range(start="2022-01-01", periods=50)
    prices = [100.0 + i for i in range(50)]
    mock_df = pd.DataFrame({"Close": prices}, index=dates)
    with patch("services.backtester.yf.download", return_value=mock_df) as mock_yf, \
         patch("services.backtester.download_alpaca", return_value=mock_df) as mock_alpaca:
        yield {"yf": mock_yf, "alpaca": mock_alpaca}



def test_health():
    """Health endpoint must return 200 with status ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_bot_status_initially_not_running():
    """Bot must not be running on a fresh app start."""
    r = client.get("/api/bot/status")
    assert r.status_code == 200
    data = r.json()
    assert data["running"] is False


def test_bot_start_dry_run():
    """Starting the bot in dry-run mode must succeed."""
    payload = {
        "symbol": "AAPL",
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        "stop_loss_pct": 5,
        "take_profit_pct": 10,
        "risk_per_trade_pct": 2,
        "poll_interval_seconds": 300,
        "dry_run": True,
    }
    r = client.post("/api/bot/start", json=payload)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_bot_start_conflict_when_already_running():
    """Starting the bot twice must return 409."""
    payload = {
        "symbol": "AAPL", "rsi_period": 14, "oversold": 30,
        "overbought": 70, "stop_loss_pct": 5, "take_profit_pct": 10,
        "risk_per_trade_pct": 2, "poll_interval_seconds": 300, "dry_run": True,
    }
    client.post("/api/bot/start", json=payload)  # start first
    r = client.post("/api/bot/start", json=payload)  # try again
    assert r.status_code == 409


def test_bot_stop():
    """Stopping the bot must return 200."""
    r = client.post("/api/bot/stop")
    assert r.status_code == 200


def test_trades_list_empty_on_fresh_db():
    """Trade list must return an empty array on a fresh database."""
    r = client.get("/api/trades/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_trades_stats_no_crash_empty():
    """Stats endpoint must not crash on an empty trade database."""
    r = client.get("/api/trades/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total_trades" in data
    assert data["total_trades"] == 0


def test_backtest_run():
    """Backtest must return stats and a non-empty equity curve."""
    payload = {
        "symbol": "AAPL",
        "start": "2022-01-01",
        "end": "2023-01-01",
        "interval": "1d",
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        "stop_loss_pct": 5,
        "take_profit_pct": 10,
        "start_capital": 10000,
    }
    r = client.post("/api/backtest/run", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "stats" in data
    assert "equity_curve" in data
    assert len(data["equity_curve"]) > 0


def test_backtest_hourly_recent_run():
    """Recent hourly backtests must work when yfinance returns data."""
    payload = {
        "symbol": "AAPL",
        "start": (datetime.now() - timedelta(days=30)).date().isoformat(),
        "end": datetime.now().date().isoformat(),
        "interval": "1h",
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        "stop_loss_pct": 5,
        "take_profit_pct": 10,
        "start_capital": 10000,
    }
    r = client.post("/api/backtest/run", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "stats" in data
    assert len(data["equity_curve"]) > 0


def test_backtest_hourly_old_range_uses_alpaca_successfully():
    """Old hourly ranges should work through Alpaca instead of yfinance."""
    payload = {
        "symbol": "AAPL",
        "start": "2022-01-01",
        "end": "2022-02-01",
        "interval": "1h",
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        "stop_loss_pct": 5,
        "take_profit_pct": 10,
        "start_capital": 10000,
    }
    r = client.post("/api/backtest/run", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "stats" in data
    assert len(data["equity_curve"]) > 0


def test_backtest_15m_run():
    """15-minute backtests should route through Alpaca."""
    payload = {
        "symbol": "AAPL",
        "start": "2022-01-01",
        "end": "2022-02-01",
        "interval": "15m",
        "rsi_period": 14,
        "oversold": 30,
        "overbought": 70,
        "stop_loss_pct": 5,
        "take_profit_pct": 10,
        "start_capital": 10000,
    }
    r = client.post("/api/backtest/run", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "stats" in data
    assert len(data["equity_curve"]) > 0


def test_optimizer_start_and_poll():
    """Optimizer must start and return a pollable job_id."""
    payload = {
        "symbol": "AAPL",
        "start": "2022-01-01",
        "end": "2023-01-01",
        "start_capital": 10000,
    }
    r = client.post("/api/optimizer/run", json=payload)
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert job_id

    r2 = client.get(f"/api/optimizer/status/{job_id}")
    assert r2.status_code == 200
    assert r2.json()["status"] in ("pending", "running", "complete")


def test_optimizer_unknown_job_returns_404():
    """Polling a non-existent job_id must return 404."""
    r = client.get("/api/optimizer/status/does-not-exist")
    assert r.status_code == 404
