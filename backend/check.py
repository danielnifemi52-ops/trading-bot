"""
check.py
Verifies every module imports cleanly before starting the server.
Run with: python check.py
If it prints ALL OK — safe to start uvicorn.
If it prints any FAIL — fix that file first.
"""
# BEFORE editing this file: cd backend && python check.py
# AFTER editing this file:  cd backend && python check.py
# If check.py fails after your edit, revert the change immediately.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

checks = [
    ("core.strategy",         "from core.strategy import BotConfig, calc_rsi"),
    ("core.risk",             "from core.risk import should_stop_loss"),
    ("models",                "from models import Trade, BotLog, BotConfigRequest"),
    ("db",                    "from db import init_db, get_session"),
    ("state",                 "from state import bot_state"),
    ("ws",                    "from ws import manager"),
    ("services.alerts",       "from services.alerts import SyncAlerter"),
    ("services.broker",       "from services.broker import Broker"),
    ("services.bot_runner",   "from services.bot_runner import BotRunner"),
    ("services.backtester",   "from services.backtester import run_backtest"),
    ("services.optimizer",    "from services.optimizer import run_optimizer"),
    ("routers.bot",           "from routers.bot import router"),
    ("routers.backtest",      "from routers.backtest import router"),
    ("routers.optimizer",     "from routers.optimizer import router"),
    ("routers.trades",        "from routers.trades import router"),
    ("main",                  "from main import app"),
]

failed = 0
for name, stmt in checks:
    try:
        exec(stmt)
        print(f"  OK    {name}")
    except Exception as e:
        print(f"  FAIL  {name}  →  {e}")
        failed += 1

print()
if failed == 0:
    print("ALL OK — safe to start uvicorn")
    sys.exit(0)
else:
    print(f"{failed} module(s) broken — fix before starting")
    sys.exit(1)
