"""
SQLAlchemy database setup — SQLite for dev, PostgreSQL for prod.

Set DATABASE_URL env var to switch:
  sqlite:///./investigateai.db   (default)
  postgresql://user:pass@host/db

Tables:
  analyses   — full analysis results
  users      — registered accounts (optional auth)
  watchlists — per-user stock watchlists
  alerts     — per-user price/risk alert rules
"""

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    JSON, String, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./investigateai.db")
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine       = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id                 = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email              = Column(String, unique=True, nullable=False, index=True)
    name               = Column(String, nullable=False, default="")
    hashed_password    = Column(String, nullable=False)
    is_active          = Column(Boolean, default=True)
    plaid_access_token = Column(Text, nullable=True)    # store encrypted in prod
    preferences        = Column(JSON, default=dict)     # {"risk_tolerance": "moderate", ...}
    created_at         = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    analyses   = relationship("Analysis",  back_populates="user",  foreign_keys="Analysis.user_id")
    watchlists = relationship("Watchlist", back_populates="user",  cascade="all, delete-orphan")
    alerts     = relationship("Alert",     back_populates="user",  cascade="all, delete-orphan")


# ── Analyses ──────────────────────────────────────────────────────────────────

class Analysis(Base):
    __tablename__ = "analyses"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker          = Column(String, nullable=False, index=True)
    amount          = Column(Float,  nullable=False)
    portfolio_value = Column(Float,  nullable=False)
    risk_tolerance  = Column(String, nullable=False)
    time_horizon    = Column(String, nullable=False)
    result          = Column(JSON,   nullable=False)   # full AnalysisResponse dict
    execution_time  = Column(Float)
    llm_provider    = Column(String)
    user_id         = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    created_at      = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="analyses", foreign_keys=[user_id])


# ── Watchlists ────────────────────────────────────────────────────────────────

class Watchlist(Base):
    __tablename__ = "watchlists"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name       = Column(String, nullable=False, default="My Watchlist")
    tickers    = Column(JSON, default=list)   # ["NVDA", "AAPL", ...]
    notes      = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="watchlists")


# ── Alerts ────────────────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    ticker       = Column(String, nullable=False, index=True)
    alert_type   = Column(String, nullable=False)    # "price_above" | "price_below" | "risk_change"
    threshold    = Column(Float,  nullable=True)     # price level or risk score
    message      = Column(Text,   nullable=True)
    is_active    = Column(Boolean, default=True)
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="alerts")


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
