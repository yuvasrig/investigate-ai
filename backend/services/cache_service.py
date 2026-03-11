"""
Simple in-memory result cache with a 5-minute TTL.

Cache key: (ticker, amount, portfolio_value, risk_tolerance, time_horizon)
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
) -> str:
    raw = f"{ticker}|{amount}|{portfolio_value}|{risk_tolerance}|{time_horizon}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    time_horizon: str,
) -> Optional[dict]:
    key = _make_key(ticker, amount, portfolio_value, risk_tolerance, time_horizon)
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
    result: dict,
) -> None:
    key = _make_key(ticker, amount, portfolio_value, risk_tolerance, time_horizon)
    _cache[key] = (result, time.time() + _TTL_SECONDS)


def clear_cache() -> None:
    _cache.clear()
