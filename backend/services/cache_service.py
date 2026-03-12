"""
Simple in-memory result cache with a 5-minute TTL.

Cache key: (ticker, amount, portfolio_value, risk_tolerance, time_horizon, user_query, analysis_action, portfolio_holdings_key)
"""

import hashlib
import time
from typing import Optional

_TTL_SECONDS = 300   # 5 minutes
_cache: dict[str, tuple[dict, float]] = {}   # key → (result, expire_at)


def _make_key(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    time_horizon: str,
    user_query: str = "",
    analysis_action: str = "buy",
    portfolio_holdings_key: str = "",
) -> str:
    raw = (
        f"{ticker}|{amount}|{portfolio_value}|{risk_tolerance}|{time_horizon}|"
        f"{user_query.strip()}|{analysis_action}|{portfolio_holdings_key}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    time_horizon: str,
    user_query: str = "",
    analysis_action: str = "buy",
    portfolio_holdings_key: str = "",
) -> Optional[dict]:
    key = _make_key(
        ticker,
        amount,
        portfolio_value,
        risk_tolerance,
        time_horizon,
        user_query,
        analysis_action,
        portfolio_holdings_key,
    )
    entry = _cache.get(key)
    if entry is None:
        return None
    result, expire_at = entry
    if time.time() > expire_at:
        del _cache[key]
        return None
    return result


def set_cached(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    time_horizon: str,
    user_query: str,
    analysis_action: str,
    portfolio_holdings_key: str,
    result: dict,
) -> None:
    key = _make_key(
        ticker,
        amount,
        portfolio_value,
        risk_tolerance,
        time_horizon,
        user_query,
        analysis_action,
        portfolio_holdings_key,
    )
    _cache[key] = (result, time.time() + _TTL_SECONDS)


def clear_cache() -> None:
    _cache.clear()
