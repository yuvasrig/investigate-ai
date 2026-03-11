"""
Portfolio hidden-exposure analyzer.

Given a list of ETF holdings and a target ticker, calculates how much
the user already owns indirectly through index funds.

No API keys required — pure Python computation using a hardcoded
ETF-holdings table (sufficient for demo).
"""

from __future__ import annotations

from typing import Any

# ── ETF holdings table ────────────────────────────────────────────────────────
# Weights are approximate as of early 2026.  Add more tickers as needed.

ETF_HOLDINGS: dict[str, dict[str, float]] = {
    "SPY": {
        "NVDA": 0.068, "AAPL": 0.070, "MSFT": 0.065,
        "AMZN": 0.038, "TSLA": 0.024, "META": 0.025,
        "GOOGL": 0.042, "GOOG": 0.018, "BRK.B": 0.018,
        "JPM": 0.015, "LLY": 0.013,
    },
    "QQQ": {
        "NVDA": 0.099, "AAPL": 0.083, "MSFT": 0.082,
        "AMZN": 0.054, "TSLA": 0.039, "META": 0.048,
        "GOOGL": 0.056, "GOOG": 0.024, "AVGO": 0.042,
        "COST": 0.025, "NFLX": 0.022,
    },
    "VOO": {
        "NVDA": 0.068, "AAPL": 0.070, "MSFT": 0.065,
        "AMZN": 0.038, "TSLA": 0.024, "META": 0.025,
        "GOOGL": 0.042, "GOOG": 0.018, "BRK.B": 0.018,
        "JPM": 0.015, "LLY": 0.013,
    },
    "VTI": {
        "NVDA": 0.054, "AAPL": 0.056, "MSFT": 0.052,
        "AMZN": 0.030, "TSLA": 0.019, "META": 0.020,
        "GOOGL": 0.034, "GOOG": 0.015, "BRK.B": 0.015,
        "JPM": 0.012, "LLY": 0.011,
    },
    "IVV": {
        "NVDA": 0.068, "AAPL": 0.070, "MSFT": 0.065,
        "AMZN": 0.038, "TSLA": 0.024, "META": 0.025,
        "GOOGL": 0.042, "GOOG": 0.018, "BRK.B": 0.018,
    },
}

# Maximum recommended single-stock concentration
CONCENTRATION_LIMIT = 0.15  # 15%


def calculate_hidden_exposure(
    portfolio: list[dict[str, Any]],
    target_ticker: str,
    proposed_amount: float,
) -> dict:
    """
    Calculate total (direct + indirect) exposure to target_ticker.

    portfolio items: {"ticker": "SPY", "value": 15000}
    Returns the structure described in AnalysisResponse.portfolio_exposure.
    """
    target = target_ticker.upper()

    # Total current portfolio value (excluding proposed new investment)
    total_value = sum(h.get("value", 0) for h in portfolio)
    if total_value <= 0:
        total_value = 1  # avoid div-by-zero

    # Direct holding
    direct_value = sum(
        h.get("value", 0) for h in portfolio
        if h.get("ticker", "").upper() == target
    )

    # Indirect holdings via ETFs
    indirect: list[dict] = []
    for h in portfolio:
        etf = h.get("ticker", "").upper()
        value = h.get("value", 0)
        if etf not in ETF_HOLDINGS:
            continue
        weight = ETF_HOLDINGS[etf].get(target, 0.0)
        if weight > 0:
            amount = round(value * weight, 2)
            indirect.append({
                "source": etf,
                "amount": amount,
                "percentage": round(weight * 100, 2),
                "etf_value": value,
            })

    total_indirect = sum(h["amount"] for h in indirect)
    total_current = direct_value + total_indirect
    current_pct = round(total_current / total_value, 4)

    # After the proposed purchase
    new_direct = direct_value + proposed_amount
    total_proposed = new_direct + total_indirect
    new_total_value = total_value + proposed_amount
    proposed_pct = round(total_proposed / new_total_value, 4)
    exceeds_limit = proposed_pct > CONCENTRATION_LIMIT

    # Maximum safe additional investment to stay under CONCENTRATION_LIMIT
    max_allowed = new_total_value * CONCENTRATION_LIMIT
    max_additional = max(0.0, round(max_allowed - total_current, 2))

    # Risk if the stock drops 20 %
    risk_20 = round(total_proposed * 0.20, 2)
    portfolio_impact_pct = round((risk_20 / new_total_value) * 100, 2)

    return {
        "current_exposure": {
            "direct": direct_value,
            "indirect": indirect,
            "total_current": round(total_current, 2),
            "current_percentage": current_pct,
        },
        "proposed_exposure": {
            "new_direct": new_direct,
            "total_indirect": total_indirect,
            "total": round(total_proposed, 2),
            "percentage": proposed_pct,
            "portfolio_value": new_total_value,
        },
        "warning": {
            "exceeds_limit": exceeds_limit,
            "limit": CONCENTRATION_LIMIT,
            "max_additional": max_additional,
            "risk_if_drops_20": risk_20,
            "portfolio_impact_pct": portfolio_impact_pct,
        },
        "has_hidden_exposure": total_indirect > 0,
    }
