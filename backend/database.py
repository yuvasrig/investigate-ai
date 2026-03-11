"""
SQLAlchemy database setup — SQLite for dev, PostgreSQL for prod.

Set DATABASE_URL env var to switch:
  sqlite:///./investigateai.db   (default)
  postgresql://user:pass@host/db
"""

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, JSON, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./investigateai.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    portfolio_value = Column(Float, nullable=False)
    risk_tolerance = Column(String, nullable=False)
    time_horizon = Column(String, nullable=False)
    result = Column(JSON, nullable=False)       # full AnalysisResponse as dict
    execution_time = Column(Float)
    llm_provider = Column(String)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
