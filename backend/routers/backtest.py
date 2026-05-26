"""
backtest.py
/api/backtest/* — run a backtest, return results
"""
from __future__ import annotations
import asyncio
import logging

from fastapi import APIRouter, HTTPException
from models import BacktestRequest, BacktestResponse
from services.backtester import run_backtest

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run", response_model=BacktestResponse)
async def run(req: BacktestRequest):
    """
    Run a walk-forward backtest. Runs in a thread to avoid blocking the event loop.
    Returns HTTP 400 if the data provider returns no data for the symbol/range.
    """
    try:
        result = await asyncio.to_thread(run_backtest, req)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error(f"Backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest failed: {e}")
