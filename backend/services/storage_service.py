"""Persist and retrieve analyses from the database."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from database import Analysis


def save_analysis(
    db: Session,
    analysis_id: str,
    result_dict: dict,
    *,
    amount: float = 0.0,
    portfolio_value: float = 0.0,
    risk_tolerance: str = "",
    time_horizon: str = "",
) -> None:
    """Write a completed analysis to the database."""
    record = Analysis(
        id=analysis_id,
        ticker=result_dict["ticker"],
        amount=amount,
        portfolio_value=portfolio_value,
        risk_tolerance=risk_tolerance,
        time_horizon=time_horizon,
        result=result_dict,
        execution_time=result_dict.get("execution_time"),
        llm_provider=result_dict.get("llm_provider"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()


def get_analysis(db: Session, analysis_id: str) -> Optional[dict]:
    """Fetch a single analysis by UUID. Returns None if not found."""
    record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if record is None:
        return None
    return record.result


def list_analyses(db: Session, limit: int = 20, offset: int = 0) -> list[dict]:
    """Return the most recent analyses in descending order."""
    rows = (
        db.query(Analysis)
        .order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "analysis_id": r.id,
            "ticker": r.ticker,
            "llm_provider": r.llm_provider,
            "execution_time": r.execution_time,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
