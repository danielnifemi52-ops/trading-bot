"""
db.py
Database initialisation and session management.
Supports PostgreSQL (Supabase) via DATABASE_URL env var,
falls back to SQLite for local development.
Uses psycopg2 driver explicitly — asyncpg is NOT required.
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

# Force psycopg2 driver explicitly — avoids asyncpg being picked up
if DATABASE_URL.startswith("postgresql://") and "psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# SQLite needs check_same_thread=False; PostgreSQL does not
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,   # test connection before using
    pool_recycle=300,     # recycle connections every 5 min
)


def init_db() -> None:
    """Create all tables. Call once on app startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session per request."""
    with Session(engine) as session:
        yield session
