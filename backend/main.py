"""
main.py
FastAPI application factory and entrypoint.
Run with: uvicorn main:app --reload
"""
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from db import engine, init_db
from ws import manager
from routers import bot, backtest, optimizer, trades

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup (before yield) and shutdown (after yield)."""
    init_db()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    # Clean shutdown: stop any running bot
    from state import bot_state
    bot_state.stop()


async def cleanup_old_logs():
    """Delete BotLog rows older than 7 days. Runs once per day."""
    from sqlmodel import Session, select, delete
    from models import BotLog
    cutoff = datetime.utcnow() - timedelta(days=7)
    try:
        with Session(engine) as session:
            session.exec(delete(BotLog).where(BotLog.timestamp < cutoff))  # type: ignore[arg-type]
            session.commit()
        log.info("Cleaned up BotLog rows older than 7 days")
    except Exception as e:
        log.error(f"cleanup_old_logs failed: {e}")


scheduler.add_job(cleanup_old_logs, "interval", hours=24, id="cleanup_old_logs")


app = FastAPI(
    title="RSI Bot API",
    description="Live RSI stock trading bot with backtesting and optimisation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("CORS_ORIGIN", "https://trading-bot-nine-sepia.vercel.app"),
        "https://trading-bot-nine-sepia.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

from fastapi import Request, status
from fastapi.responses import JSONResponse

API_KEY = os.getenv("API_KEY", "")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api"):
        key = request.headers.get("X-API-Key", "")
        if API_KEY and key != API_KEY:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"}
            )
    return await call_next(request)


app.include_router(bot.router,       prefix="/api/bot",       tags=["bot"])
app.include_router(backtest.router,  prefix="/api/backtest",  tags=["backtest"])
app.include_router(optimizer.router, prefix="/api/optimizer", tags=["optimizer"])
app.include_router(trades.router,    prefix="/api/trades",    tags=["trades"])


@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    """WebSocket endpoint — streams price/RSI/signal on every bot tick."""
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()   # keep connection alive; bot pushes data
    except WebSocketDisconnect:
        await manager.disconnect(ws)


@app.get("/health")
async def health():
    """Health check: DB ping + psutil memory usage."""
    import psutil, os as _os
    from state import bot_state

    # Memory (FIX 3)
    try:
        mem_mb = psutil.Process(_os.getpid()).memory_info().rss / 1_048_576
    except Exception:
        mem_mb = 0.0

    MEM_LIMIT = 512
    status_str = "warning" if mem_mb > 450 else "ok"

    # DB ping
    db_status = "unknown"
    try:
        from sqlmodel import Session, text
        from db import engine
        with Session(engine) as session:
            session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        status_str = "error"
        db_status = f"error: {e}"

    payload = {
        "status": status_str,
        "db": db_status,
        "memory_mb": round(mem_mb, 1),
        "memory_limit_mb": MEM_LIMIT,
        "memory_pct": round(mem_mb / MEM_LIMIT * 100, 1),
        "bot_running": bot_state.is_running,
    }
    if status_str == "error":
        return JSONResponse(status_code=503, content=payload)
    return payload
