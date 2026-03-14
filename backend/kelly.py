"""
Kelly Criterion Position Sizing — Mathematical Implementation

Modified Kelly formula:
  f* = (p × b - q) / b
  where:
    p = probability of winning (bull conviction normalised 0-1)
    q = 1 - p
    b = upside / downside ratio (from bull/bear price targets)

We apply a half-Kelly safety factor and cap by the strategist's allocation.
"""

from __future__ import annotations


# ── Core math ─────────────────────────────────────────────────────────────────

def kelly_fraction(
    bull_conviction: float,   # 0-100
    bear_conviction: float,   # 0-100
    bull_target: float,       # bull best-case price target
    bear_target: float,       # bear worst-case price target
    current_price: float,     # live market price
    half_kelly: bool = True,  # apply 0.5× safety multiplier
) -> float:
    """
    Compute the raw Kelly fraction (0.0–1.0) of capital to deploy.
    Returns 0.0 if there is no positive edge.
    """
    if current_price <= 0 or bull_target <= current_price or bear_target >= current_price:
        return 0.0

    total_conv = bull_conviction + bear_conviction
    if total_conv <= 0:
        return 0.0

    p = bull_conviction / total_conv          # win probability
    q = 1.0 - p

    upside   = (bull_target - current_price) / current_price   # e.g. 0.40 = 40% upside
    downside = (current_price - bear_target) / current_price   # e.g. 0.25 = 25% downside

    if downside <= 0:
        return 0.0

    b = upside / downside  # reward / risk ratio

    f_star = (p * b - q) / b
    f_star = max(0.0, min(1.0, f_star))

    if half_kelly:
        f_star *= 0.5

    return f_star


def kelly_position_size(
    bull_conviction: float,
    bear_conviction: float,
    bull_target: float,
    bear_target: float,
    current_price: float,
    proposed_amount: float,
    portfolio_value: float,
    strategist_cap: float,
    correlation: float = 0.65,
    half_kelly: bool = True,
) -> dict:
    """
    Calculate the recommended position size using Modified Kelly.

    Returns a dict with:
      kelly_fraction              — raw f* (0-1)
      raw_kelly_amount            — f* × portfolio_value
      correlation_adjusted_amount — reduced by correlation factor
      final_amount                — min(corr_adjusted, strategist_cap, proposed)
      sizing_rationale            — human-readable explanation
      scale_factor                — 0-1 multiplier vs proposed_amount
    """
    f_star = kelly_fraction(
        bull_conviction, bear_conviction,
        bull_target, bear_target, current_price, half_kelly,
    )

    raw_kelly_amount = f_star * portfolio_value

    # Correlation discount: corr=1.0 → 50% multiplier; corr=0.0 → 100% multiplier
    correlation_factor = 1.0 - (correlation * 0.5)
    corr_adjusted = raw_kelly_amount * correlation_factor

    final = min(corr_adjusted, strategist_cap, proposed_amount)
    final = max(0.0, final)

    scale = (final / proposed_amount) if proposed_amount > 0 else 0.0

    if f_star == 0.0:
        rationale = "Kelly model finds no positive edge — no position recommended."
    elif scale >= 0.90:
        rationale = (
            f"Strong positive edge (Kelly f*={f_star:.1%}). "
            "Full proposed amount supported."
        )
    elif scale >= 0.60:
        rationale = (
            f"Moderate edge (Kelly f*={f_star:.1%}). "
            f"Position scaled to {scale:.0%} of proposed due to correlation/strategist cap."
        )
    else:
        rationale = (
            f"Weak or diluted edge (Kelly f*={f_star:.1%}). "
            f"Position reduced to {scale:.0%} — high correlation ({correlation:.0%}) "
            "or strategist cap limits size."
        )

    return {
        "kelly_fraction": round(f_star, 4),
        "raw_kelly_amount": round(raw_kelly_amount, 2),
        "correlation_adjusted_amount": round(corr_adjusted, 2),
        "final_amount": round(final, 2),
        "sizing_rationale": rationale,
        "scale_factor": round(scale, 4),
    }


# ── High-level wrapper ────────────────────────────────────────────────────────

def compute_kelly_sizing(
    bull_analysis,
    bear_analysis,
    strategist_analysis,
    market_data: dict,
    proposed_amount: float,
    portfolio_value: float,
) -> dict:
    """
    High-level wrapper that extracts fields from Pydantic models.
    Called from server.py after agents complete.
    """
    current_price = (
        market_data.get("currentPrice")
        or market_data.get("current_price")
        or 0.0
    )

    bull_conv = float(bull_analysis.confidence) * 10   # 0-10 → 0-100
    bear_conv = float(bear_analysis.confidence) * 10

    strategist_cap = float(strategist_analysis.recommended_allocation)

    _corr_map = {"LOW": 0.40, "MODERATE": 0.60, "HIGH": 0.75, "VERY HIGH": 0.90}
    correlation = _corr_map.get(strategist_analysis.concentration_risk, 0.65)

    bull_target = float(bull_analysis.best_case_target)
    bear_target = float(bear_analysis.worst_case_target)

    # Graceful fallback when LLM outputs invalid/zero targets:
    # estimate ±(confidence/10 × 25%) from current price
    if current_price > 0:
        if bull_target <= current_price:
            bull_target = current_price * (1 + bull_conv / 100 * 0.25)
        if bear_target >= current_price:
            bear_target = current_price * (1 - bear_conv / 100 * 0.25)

    # If strategist recommends 0, use proposed_amount as cap
    if strategist_cap <= 0:
        strategist_cap = proposed_amount

    return kelly_position_size(
        bull_conviction=bull_conv,
        bear_conviction=bear_conv,
        bull_target=bull_target,
        bear_target=bear_target,
        current_price=float(current_price),
        proposed_amount=proposed_amount,
        portfolio_value=portfolio_value,
        strategist_cap=strategist_cap,
        correlation=correlation,
    )
