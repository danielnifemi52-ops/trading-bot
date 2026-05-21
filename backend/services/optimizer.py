"""
optimizer.py
Async grid-search optimizer. Iterates over RSI parameter combinations,
runs a mini-backtest for each, ranks results by Sharpe ratio.
Writes progress to bot_state.optimizer_jobs — safe to run in a thread.
"""
from __future__ import annotations
import logging
import itertools
from typing import TYPE_CHECKING

from models import OptimizerRequest, OptimizerRun, BacktestRequest
from services.backtester import run_backtest

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

# Parameter grid — 3×3×3×2×2 = 108 combinations
RSI_PERIODS     = [10, 14, 20]
OVERSOLD_VALS   = [25.0, 30.0, 35.0]
OVERBOUGHT_VALS = [65.0, 70.0, 75.0]
STOP_LOSSES     = [3.0, 5.0]
TAKE_PROFITS    = [8.0, 12.0]


def run_optimizer(req: OptimizerRequest, job_id: str, jobs: dict) -> None:
    """
    Grid-search over RSI parameters. Runs in a background thread.
    Updates jobs[job_id] with progress and results as it runs.
    """
    combos = list(itertools.product(
        RSI_PERIODS, OVERSOLD_VALS, OVERBOUGHT_VALS, STOP_LOSSES, TAKE_PROFITS
    ))
    total = len(combos)
    results: list[dict] = []

    jobs[job_id] = OptimizerRun(job_id=job_id, status="running", progress=0)

    for idx, (period, oversold, overbought, sl, tp) in enumerate(combos):
        # Skip nonsensical parameter combos
        if oversold >= overbought:
            jobs[job_id] = OptimizerRun(
                job_id=job_id, status="running",
                progress=int((idx + 1) / total * 100),
            )
            continue
        try:
            bt_req = BacktestRequest(
                symbol=req.symbol,
                start=req.start,
                end=req.end,
                interval="1d",
                rsi_period=period,
                oversold=oversold,
                overbought=overbought,
                stop_loss_pct=sl,
                take_profit_pct=tp,
                start_capital=req.start_capital,
            )
            result = run_backtest(bt_req)
            s = result.stats
            score = s.sharpe_ratio  # primary ranking metric
            results.append({
                "rsi_period": period,
                "oversold": oversold,
                "overbought": overbought,
                "stop_loss_pct": sl,
                "take_profit_pct": tp,
                "total_trades": s.total_trades,
                "win_rate": s.win_rate,
                "total_pnl": s.total_pnl,
                "max_drawdown_pct": s.max_drawdown_pct,
                "sharpe_ratio": s.sharpe_ratio,
                "profit_factor": s.profit_factor,
                "score": round(score, 4),
            })
        except Exception as e:
            log.warning(f"Optimizer combo failed ({period},{oversold},{overbought},{sl},{tp}): {e}")

        progress = int((idx + 1) / total * 100)
        jobs[job_id] = OptimizerRun(
            job_id=job_id, status="running", progress=progress,
        )

    # Sort by score descending, return top 20
    results.sort(key=lambda x: x["score"], reverse=True)
    top20 = results[:20]

    jobs[job_id] = OptimizerRun(
        job_id=job_id, status="complete", progress=100, results=top20,
    )
    log.info(f"Optimizer job {job_id} complete — {len(results)} combos evaluated")
