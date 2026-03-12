"""
Tax-Loss Harvesting Analyzer

Given a list of holdings with cost_basis, identifies positions at a loss,
calculates potential tax savings, and recommends wash-sale-safe replacements.

US tax rates used by default (configurable via env vars).
"""

from __future__ import annotations

import os
from typing import Optional

# ── Tax rate constants ────────────────────────────────────────────────────────

SHORT_TERM_RATE = float(os.getenv("TAX_SHORT_TERM_RATE", "0.37"))  # ordinary income
LONG_TERM_RATE  = float(os.getenv("TAX_LONG_TERM_RATE",  "0.20"))  # LTCG

# ── Wash-sale-safe replacements ───────────────────────────────────────────────
# Maps ticker → similar but NOT substantially-identical alternatives

REPLACEMENT_MAP: dict[str, list[str]] = {
    "SPY":   ["IVV", "VOO", "SPLG"],
    "QQQ":   ["QQQM", "ONEQ", "SCHG"],
    "VTI":   ["ITOT", "SCHB", "SPTM"],
    "VOO":   ["IVV", "SPY", "SCHX"],
    "IVV":   ["SPY", "VOO", "SPLG"],
    "NVDA":  ["AMD", "SMCI", "AVGO"],
    "AAPL":  ["MSFT", "GOOGL", "META"],
    "MSFT":  ["AAPL", "GOOGL", "CRM"],
    "GOOGL": ["META", "SNAP", "TTD"],
    "META":  ["GOOGL", "SNAP", "PINS"],
    "TSLA":  ["RIVN", "LCID", "NIO"],
    "AMZN":  ["SHOP", "BABA", "EBAY"],
    "AMD":   ["NVDA", "INTC", "QCOM"],
    "INTC":  ["AMD", "QCOM", "AVGO"],
    "BABA":  ["JD", "PDD", "SE"],
}

DEFAULT_REPLACEMENTS = ["BRK-B", "VIG", "SCHD"]  # diversified fallback


# ── Main function ─────────────────────────────────────────────────────────────

def analyse_tax_loss_opportunities(
    holdings: list[dict],
    tax_year: Optional[int] = None,
) -> dict:
    """
    Analyse holdings for tax-loss harvesting opportunities.

    Each holding dict:
      ticker              str   required
      value               float required  (current market value)
      cost_basis          float optional  (total purchase cost)
      holding_period_days int   optional  (determines ST vs LT rate)
      name                str   optional

    Returns:
      opportunities            list  — candidates sorted by tax_savings desc
      total_potential_savings  float
      gain_loss_summary        dict
      summary                  str
      wash_sale_warning        str
    """
    import datetime
    current_year = tax_year or datetime.date.today().year

    opportunities = []
    total_savings = 0.0

    for h in holdings:
        ticker       = h.get("ticker", "").upper()
        current_val  = float(h.get("value", 0))
        cost_basis   = h.get("cost_basis")
        holding_days = h.get("holding_period_days")

        if cost_basis is None:
            continue   # can't calculate without basis

        cost_basis = float(cost_basis)
        unrealised  = current_val - cost_basis

        if unrealised >= 0:
            continue   # gain — not a harvesting candidate

        loss = abs(unrealised)

        if holding_days is not None and holding_days <= 365:
            term     = "short-term"
            tax_rate = SHORT_TERM_RATE
        else:
            term     = "long-term"
            tax_rate = LONG_TERM_RATE

        savings = loss * tax_rate
        total_savings += savings
        loss_pct = (loss / cost_basis * 100) if cost_basis > 0 else 0.0

        replacements = REPLACEMENT_MAP.get(ticker, DEFAULT_REPLACEMENTS)

        opportunities.append({
            "ticker":                 ticker,
            "name":                   h.get("name", ticker),
            "current_value":          round(current_val, 2),
            "cost_basis":             round(cost_basis, 2),
            "unrealised_loss":        round(unrealised, 2),       # negative
            "loss_pct":               round(loss_pct, 1),
            "holding_period_days":    holding_days,
            "term":                   term,
            "tax_rate_applied":       tax_rate,
            "estimated_tax_savings":  round(savings, 2),
            "replacement_securities": replacements,
            "wash_sale_window_days":  30,
            "action": (
                f"Sell {ticker}, realise ${loss:,.0f} {term} loss "
                f"(saves ~${savings:,.0f} in taxes at {tax_rate:.0%} rate). "
                f"Replace immediately with {replacements[0]} (different issuer, "
                f"no wash-sale risk) or wait 31 days to buy {ticker} back."
            ),
        })

    opportunities.sort(key=lambda x: x["estimated_tax_savings"], reverse=True)

    # Gain/loss summary
    glsummary = get_gain_loss_summary(holdings)

    if not opportunities:
        summary = (
            "No tax-loss harvesting opportunities identified. "
            "All positions are at a gain, or cost basis data is missing."
        )
    else:
        top = opportunities[0]
        summary = (
            f"Found {len(opportunities)} harvesting "
            f"opportunit{'y' if len(opportunities)==1 else 'ies'} "
            f"with ~${total_savings:,.0f} total potential tax savings. "
            f"Largest: {top['ticker']} saves ~${top['estimated_tax_savings']:,.0f} "
            f"({top['term']} rate)."
        )

    return {
        "opportunities": opportunities,
        "total_potential_tax_savings": round(total_savings, 2),
        "positions_analysed": len(holdings),
        "positions_with_losses": len(opportunities),
        "short_term_rate_used": SHORT_TERM_RATE,
        "long_term_rate_used": LONG_TERM_RATE,
        "tax_year": current_year,
        "gain_loss_summary": glsummary,
        "summary": summary,
        "wash_sale_warning": (
            "⚠️  WASH-SALE RULE: Do not repurchase the same or substantially "
            "identical security within 30 days before or after the sale. "
            "Using the listed replacement securities avoids this restriction."
        ),
    }


def get_gain_loss_summary(holdings: list[dict]) -> dict:
    """Quick gain/loss totals across all holdings with a cost basis."""
    total_gain = 0.0
    total_loss = 0.0
    with_basis = 0

    for h in holdings:
        cb = h.get("cost_basis")
        if cb is None:
            continue
        with_basis += 1
        pnl = float(h.get("value", 0)) - float(cb)
        if pnl > 0:
            total_gain += pnl
        else:
            total_loss += abs(pnl)

    return {
        "total_unrealised_gain": round(total_gain, 2),
        "total_unrealised_loss": round(total_loss, 2),
        "net_unrealised_pnl":    round(total_gain - total_loss, 2),
        "positions_with_cost_basis": with_basis,
        "positions_total": len(holdings),
    }
