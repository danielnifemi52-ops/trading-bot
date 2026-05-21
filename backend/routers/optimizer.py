"""
optimizer.py
/api/optimizer/* — start async grid search, poll status
"""
from __future__ import annotations
import logging
import threading
import uuid

from fastapi import APIRouter, HTTPException
from models import OptimizerRequest, OptimizerRun
from state import bot_state
from services.optimizer import run_optimizer

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run")
def start_optimizer(req: OptimizerRequest):
    """
    Start an async optimizer job. Returns a job_id immediately.
    Poll /status/{job_id} to track progress.
    """
    job_id = str(uuid.uuid4())
    bot_state.optimizer_jobs[job_id] = OptimizerRun(
        job_id=job_id, status="pending", progress=0
    )

    thread = threading.Thread(
        target=run_optimizer,
        args=(req, job_id, bot_state.optimizer_jobs),
        daemon=True,
        name=f"optimizer-{job_id[:8]}",
    )
    thread.start()
    log.info(f"Optimizer job {job_id} started")
    return {"job_id": job_id}


@router.get("/status/{job_id}", response_model=OptimizerRun)
def get_status(job_id: str):
    """Return the current status/progress/results of an optimizer job."""
    job = bot_state.optimizer_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job
