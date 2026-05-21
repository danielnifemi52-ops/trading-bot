"""
db.py
Database initialisation and session management.
Uses SQLModel over SQLite for database access.
"""
from __future__ import annotations
from sqlmodel import SQLModel, create_engine, Session
from models import Trade, BotLog   # noqa: F401 — imported so SQLModel sees the tables

DATABASE_URL = "sqlite:///./rsi_bot.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    """Create all tables. Call once on app startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session per request."""
    with Session(engine) as session:
        yield session
