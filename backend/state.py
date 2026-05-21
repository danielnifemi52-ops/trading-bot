"""
state.py
Single source of truth for in-memory bot state.
Shared between the bot runner thread and FastAPI request handlers.
All attributes are read/written with threading.Lock for safety.
"""
from __future__ import annotations
import threading
from typing import Optional
from models import BotConfigRequest, OptimizerRun
from services.bot_runner import BotRunner


class BotState:
    """
    Singleton. Import and use `bot_state` — do not instantiate directly.
    Thread-safe: every public method acquires the lock.
    """

    def __init__(self):
        """Initialise empty state."""
        self._lock    = threading.Lock()
        self._runner: Optional[BotRunner] = None
        self._config: Optional[BotConfigRequest] = None
        self.optimizer_jobs: dict[str, OptimizerRun] = {}

    # ── Bot control ──────────────────────────────────────────────────────

    def start(self, runner: BotRunner, config: BotConfigRequest) -> None:
        """Store and start the runner. Stops any existing runner first."""
        with self._lock:
            if self._runner and self._runner.is_running():
                self._runner.stop()
            self._runner = runner
            self._config = config
        runner.start()

    def stop(self) -> None:
        """Stop the running bot if one exists."""
        with self._lock:
            if self._runner:
                self._runner.stop()

    # ── Status reads ─────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """Return True if the bot thread is alive."""
        with self._lock:
            return self._runner is not None and self._runner.is_running()

    @property
    def last_price(self) -> Optional[float]:
        """Return the most recent price seen by the bot."""
        with self._lock:
            return self._runner.last_price if self._runner else None

    @property
    def last_rsi(self) -> Optional[float]:
        """Return the most recent RSI value seen by the bot."""
        with self._lock:
            return self._runner.last_rsi if self._runner else None

    @property
    def last_signal(self) -> Optional[str]:
        """Return the most recent signal produced by the bot."""
        with self._lock:
            return self._runner.last_signal if self._runner else None

    @property
    def open_position(self) -> bool:
        """Return True if the bot currently holds an open position."""
        with self._lock:
            return self._runner.open_trade is not None if self._runner else False

    @property
    def config(self) -> Optional[BotConfigRequest]:
        """Return the current bot configuration."""
        with self._lock:
            return self._config


bot_state = BotState()
