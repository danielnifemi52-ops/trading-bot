"""
main.py
FastAPI application factory and entrypoint.
Run with: uvicorn main:app --reload
"""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from ws import manager
from routers import bot, backtest, optimizer, trades

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup (before yield) and shutdown (after yield)."""
    init_db()
    yield
    # Clean shutdown: stop any running bot
    from state import bot_state
    bot_state.stop()


app = FastAPI(
    title="RSI Bot API",
    description="Live RSI stock trading bot with backtesting and optimisation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Health check endpoint."""
    return {"status": "ok"}
