"""
db.py
Database initialisation and session management.
Supports PostgreSQL (Supabase) via DATABASE_URL env var,
falls back to SQLite for local development.
Uses psycopg2 driver explicitly — asyncpg is NOT required.
"""
from __future__ import annotations
import os
import logging
from sqlmodel import SQLModel, create_engine, Session
from models import Trade, BotLog   # noqa: F401 — imported so SQLModel sees the tables

log = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./rsi_bot.db"
)

# Fix URL format issues
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

# Force psycopg2 driver for PostgreSQL
if ("postgresql://" in DATABASE_URL and 
    "psycopg2" not in DATABASE_URL):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )

# Supabase pooler needs this extra parameter
connect_args = {}
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
    engine_kwargs = {
        "echo": False,
        "connect_args": connect_args
    }
else:
    # PostgreSQL pooler settings
    engine_kwargs.update({
        "pool_size": 3,
        "max_overflow": 5,
        "pool_recycle": 300,
        "pool_timeout": 30,
        "connect_args": {
            "connect_timeout": 10,
            "sslmode": "require",
        }
    })

try:
    engine = create_engine(DATABASE_URL, **engine_kwargs)
    log.info(f"Database engine created: {DATABASE_URL[:30]}...")
except Exception as e:
    log.error(f"Database setup failed: {e}")
    log.warning("Falling back to SQLite")
    DATABASE_URL = "sqlite:///./rsi_bot.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )


def init_db() -> None:
    """Create tables. Fails gracefully if DB unreachable."""
    try:
        SQLModel.metadata.create_all(engine)
        log.info("Database tables created/verified")
    except Exception as e:
        log.error(f"init_db failed: {e}")
        raise


def get_session():
    with Session(engine) as session:
        yield session
