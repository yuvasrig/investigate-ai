"""
Portfolio hidden-exposure analyzer.

Given a list of ETF holdings and a target ticker, calculates how much
the user already owns indirectly through index funds.

No API keys required — pure Python computation using a hardcoded
ETF-holdings table (sufficient for demo).
"""

from __future__ import annotations

from typing import Any

# ── Known ETF universe ────────────────────────────────────────────────────────
# Used to distinguish ETFs from individual stocks during categorization.

#: Broad-market / core buy-and-hold ETFs (low cost, highly diversified)
LONG_TERM_CORE_ETFS: set[str] = {
    "VTI", "VOO", "VT", "IVV", "SPY", "SCHB", "SPLG", "ITOT",  # US broad market
    "VXUS", "VEU", "SPDW", "IEFA", "EFA", "ACWX",              # International developed
    "BND", "AGG", "GOVT", "VGIT", "VCIT", "VGSH", "SHY",       # Investment-grade bonds
    "BNDX", "IAGG",                                              # Intl bonds
}

#: Growth / thematic ETFs — high upside but concentrated / volatile
GROWTH_ETFS: set[str] = {
    "QQQ", "QQQM", "XLK", "VGT", "IGV",                        # Tech / growth
    "ARKK", "ARKG", "ARKW", "ARKF", "ARKQ",                    # Active ARK
    "SOXX", "SMH",                                               # Semiconductors
    "CIBR", "BOTZ", "ROBO",                                     # AI / robotics / cyber
    "MSOS", "YOLO",                                              # Speculative
}

#: Bond / fixed-income ETFs
BOND_ETFS: set[str] = {
    "BND", "AGG", "TLT", "IEF", "SHY", "GOVT",
    "BNDX", "VCIT", "LQD", "HYG", "JNK",
    "VGIT", "VCSH", "IAGG",
}

#: International ETFs (developed + emerging)
INTL_ETFS: set[str] = {
    "VEA", "VWO", "EFA", "EEM", "IEFA", "VXUS", "VT",
    "SPDW", "ACWI", "ACWX", "VEU",
}

#: Any ticker we recognise as an ETF (union of all sets above + ETF_HOLDINGS keys)
ALL_KNOWN_ETFS: set[str] = LONG_TERM_CORE_ETFS | GROWTH_ETFS | BOND_ETFS | INTL_ETFS

#: Tickers commonly associated with the technology sector for concentration check
TECH_TICKERS: set[str] = {
    "NVDA", "AAPL", "MSFT", "META", "GOOGL", "GOOG",
    "AMZN", "TSLA", "AVGO", "AMD", "INTC", "QCOM", "ACN",
    "QQQ", "QQQM", "XLK", "VGT", "SOXX", "SMH",
    "ARKK", "ARKG", "ARKW",
}

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


# ══════════════════════════════════════════════════════════════════════════════
# Tier-1 Complete Portfolio Analysis
# ══════════════════════════════════════════════════════════════════════════════

def analyze_complete_portfolio(portfolio: dict[str, Any]) -> dict:
    """
    Analyse a full portfolio and return a structured Tier-1 report:

    - long_term_core   – broad-market ETFs to hold forever
    - growth_positions – concentrated ETFs + individual stocks to monitor
    - concentration_risks – single stock >15 % or sector >40 %
    - missing_protections – absent bond / international allocation
    - overall_risk_score  – 0–10 (10 = highest risk)
    - summary             – quick aggregates
    """
    holdings: list[dict] = portfolio.get("holdings", [])
    total_value: float = portfolio.get("total_value", 0) or sum(
        h.get("value", 0) for h in holdings
    )
    if total_value <= 0:
        total_value = 1

    # Resolve full ETF universe (include ETF_HOLDINGS keys too)
    all_etfs = ALL_KNOWN_ETFS | set(ETF_HOLDINGS.keys())

    long_term_core:      list[dict] = []
    growth_positions:    list[dict] = []
    concentration_risks: list[dict] = []
    missing_protections: list[dict] = []

    bond_value  = 0.0
    intl_value  = 0.0
    tech_value  = 0.0

    for h in holdings:
        ticker  = h.get("ticker", "").upper()
        value   = float(h.get("value", 0))
        pct     = value / total_value * 100
        name    = h.get("name") or ticker

        # Running totals for penalty calculations
        if ticker in BOND_ETFS:
            bond_value += value
        if ticker in INTL_ETFS:
            intl_value += value
        if ticker in TECH_TICKERS:
            tech_value += value

        # ── Categorise ────────────────────────────────────────────────────────
        is_etf = ticker in all_etfs

        if ticker in LONG_TERM_CORE_ETFS:
            long_term_core.append({
                "ticker": ticker,
                "name": name,
                "value": value,
                "percentage": round(pct, 1),
                "reason": "Diversified, low-cost — buy & hold through cycles",
            })
        elif ticker in GROWTH_ETFS:
            growth_positions.append({
                "ticker": ticker,
                "name": name,
                "value": value,
                "percentage": round(pct, 1),
                "reason": "Concentrated theme ETF — high upside, monitor momentum",
            })
        elif not is_etf:
            # Individual stock
            growth_positions.append({
                "ticker": ticker,
                "name": name,
                "value": value,
                "percentage": round(pct, 1),
                "reason": "Individual stock — full single-company risk",
            })
            # Single-stock concentration check
            if pct > 15:
                concentration_risks.append({
                    "type": "single_stock",
                    "ticker": ticker,
                    "name": name,
                    "exposure": round(pct, 1),
                    "limit": 15,
                    "severity": "high" if pct > 20 else "medium",
                    "message": (
                        f"{ticker} is {pct:.1f}% of your portfolio "
                        f"(limit: 15%). Consider trimming to reduce single-stock risk."
                    ),
                })
        else:
            # Other known ETF (sector ETF, bond, international already caught above)
            if ticker in BOND_ETFS or ticker in INTL_ETFS:
                long_term_core.append({
                    "ticker": ticker,
                    "name": name,
                    "value": value,
                    "percentage": round(pct, 1),
                    "reason": (
                        "Bond allocation — volatility buffer"
                        if ticker in BOND_ETFS
                        else "International diversification"
                    ),
                })
            else:
                growth_positions.append({
                    "ticker": ticker,
                    "name": name,
                    "value": value,
                    "percentage": round(pct, 1),
                    "reason": "Sector / thematic ETF — monitor concentration",
                })

    # ── Sector concentration risk ─────────────────────────────────────────────
    tech_pct = tech_value / total_value * 100
    if tech_pct > 40:
        concentration_risks.append({
            "type": "sector",
            "ticker": "TECH",
            "name": "Technology sector",
            "exposure": round(tech_pct, 1),
            "limit": 40,
            "severity": "high" if tech_pct > 55 else "medium",
            "message": (
                f"Technology makes up {tech_pct:.1f}% of your portfolio "
                f"(recommended max: 40%). A single sector downturn could "
                f"significantly impact returns."
            ),
        })

    # ── Missing protections ───────────────────────────────────────────────────
    bond_pct = bond_value / total_value * 100
    intl_pct = intl_value / total_value * 100

    if bond_pct < 5:
        missing_protections.append({
            "type": "bonds",
            "current": round(bond_pct, 1),
            "recommended_min": 10,
            "recommended_max": 20,
            "message": (
                f"Only {bond_pct:.1f}% in bonds. "
                "Add BND or AGG for a volatility buffer during market downturns."
            ),
            "tickers": ["BND", "AGG", "VGIT"],
        })

    if intl_pct < 10:
        missing_protections.append({
            "type": "international",
            "current": round(intl_pct, 1),
            "recommended_min": 20,
            "recommended_max": 30,
            "message": (
                f"Only {intl_pct:.1f}% in international stocks. "
                "Add VEA or VXUS to reduce US-market concentration."
            ),
            "tickers": ["VEA", "VXUS", "EFA"],
        })

    # ── Risk score (0–10) ─────────────────────────────────────────────────────
    # Concentration penalty (max 3)
    single_stock_risks = [r for r in concentration_risks if r["type"] == "single_stock"]
    concentration_penalty = min(3.0, len(single_stock_risks) * 1.5)

    # Sector concentration penalty (max 2)
    sector_penalty = min(2.0, max(0.0, (tech_pct - 40) / 15))

    # Growth-heavy penalty (max 2) — ratio of growth vs core by value
    growth_value = sum(p["value"] for p in growth_positions)
    core_value   = sum(p["value"] for p in long_term_core)
    growth_ratio = growth_value / max(1, growth_value + core_value)
    volatility_penalty = min(2.0, growth_ratio * 2.5)

    # Missing diversification penalty (max 3)
    diversification_penalty = (
        (1 if bond_pct < 5 else 0)
        + (1 if intl_pct < 10 else 0)
        + (1 if len(holdings) < 5 else 0)
    )

    overall_risk_score = min(10.0, round(
        concentration_penalty
        + sector_penalty
        + volatility_penalty
        + diversification_penalty,
        1,
    ))

    risk_level = (
        "LOW"       if overall_risk_score < 3 else
        "MODERATE"  if overall_risk_score < 5 else
        "HIGH"      if overall_risk_score < 7 else
        "VERY HIGH"
    )

    long_term_pct = round(sum(p["percentage"] for p in long_term_core), 1)
    growth_pct    = round(sum(p["percentage"] for p in growth_positions), 1)

    return {
        "long_term_core":      long_term_core,
        "growth_positions":    growth_positions,
        "concentration_risks": concentration_risks,
        "missing_protections": missing_protections,
        "overall_risk_score":  overall_risk_score,
        "summary": {
            "total_holdings": len(holdings),
            "long_term_pct":  long_term_pct,
            "growth_pct":     growth_pct,
            "bond_pct":       round(bond_pct, 1),
            "intl_pct":       round(intl_pct, 1),
            "tech_pct":       round(tech_pct, 1),
            "risk_level":     risk_level,
            "risk_score":     overall_risk_score,
        },
    }
    num_flagged = sum(1 for r in concentration_risks if r["type"] == "single_stock")
    concentration_penalty = min(3.0, num_flagged * 1.5)
    sector_penalty = min(2.0, max(0.0, (tech_pct - 40) / 15))

    long_term_pct = sum(e["percentage"] for e in long_term_core)
    growth_pct    = sum(e["percentage"] for e in growth_positions)
    growth_ratio  = growth_pct / max(1.0, growth_pct + long_term_pct)
    volatility_penalty = min(2.0, growth_ratio * 2.5)

    diversification_penalty = (
        (1 if bond_pct < 5 else 0)
        + (1 if intl_pct < 10 else 0)
        + (1 if len(holdings) < 5 else 0)
    )

    overall_risk_score = min(10, int(round(
        concentration_penalty + sector_penalty + volatility_penalty + diversification_penalty,
        0,
    )))

    risk_level = (
        "LOW"       if overall_risk_score < 3 else
        "MODERATE"  if overall_risk_score < 5 else
        "HIGH"      if overall_risk_score < 7 else
        "VERY HIGH"
    )

    return {
        "long_term_core": long_term_core,
        "growth_positions": growth_positions,
        "concentration_risks": concentration_risks,
        "missing_protections": missing_protections,
        "overall_risk_score": overall_risk_score,
        "summary": {
            "total_holdings": len(holdings),
            "long_term_pct": round(long_term_pct, 1),
            "growth_pct": round(growth_pct, 1),
            "bond_pct": round(bond_pct, 1),
            "intl_pct": round(intl_pct, 1),
            "tech_pct": round(tech_pct, 1),
            "risk_level": risk_level,
            "risk_score": overall_risk_score,
        },
    }
