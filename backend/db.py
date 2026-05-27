"""
db.py
Database initialisation and session management.
Supports PostgreSQL (Supabase) via DATABASE_URL env var,
falls back to SQLite for local development.
"""
from __future__ import annotations
import os
from sqlmodel import SQLModel, create_engine, Session
from models import Trade, BotLog   # noqa: F401 — imported so SQLModel sees the tables

# Use PostgreSQL if DATABASE_URL is set, otherwise SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./rsi_bot.db"
)

# Supabase uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# PostgreSQL doesn't need check_same_thread
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,    # test connection before using
        pool_recycle=300,      # recycle connections every 5 min
        pool_size=5,           # max 5 persistent connections
        max_overflow=10,       # allow 10 extra burst connections
    )


def init_db() -> None:
    """Create all tables. Call once on app startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session per request."""
    with Session(engine) as session:
        yield session
