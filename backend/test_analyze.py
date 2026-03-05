"""
Quick smoke-test: analyze NVDA with $50K in a $500K portfolio.
Run from backend/:  python test_analyze.py
"""
import json
from dotenv import load_dotenv
load_dotenv()

from tools import fetch_full_market_data, format_market_context
from workflow import run_analysis


def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def main():
    ticker = "NVDA"

    # ── 1. Show the raw market data that agents will receive ──────────────────
    section("LIVE MARKET DATA (what agents see)")
    market_data = fetch_full_market_data(ticker)
    print(format_market_context(market_data))

    # ── 2. Run the full workflow ──────────────────────────────────────────────
    section("RUNNING ANALYSIS WORKFLOW")
    print(f"Ticker: {ticker} | Amount: $50,000 | Portfolio: $500,000 | Risk: moderate\n")

    result = run_analysis(
        ticker=ticker,
        amount=50_000,
        portfolio_value=500_000,
        risk_tolerance="moderate",
        time_horizon="5Y",
    )

    # ── 3. Bull ───────────────────────────────────────────────────────────────
    section("BULL ANALYST")
    bull = result["bull_analysis"]
    print(f"Confidence:          {bull.confidence}/10")
    print(f"Best-Case Target:    ${bull.best_case_target:,.2f}  ({bull.best_case_timeline})")
    if bull.pe_ratio:
        print(f"PE Used in Analysis: {bull.pe_ratio:.1f}x")
    print("\nCompetitive Advantages:")
    for a in bull.competitive_advantages:
        print(f"  ✓ {a}")
    print("\nGrowth Catalysts:")
    for c in bull.growth_catalysts:
        print(f"  → {c}")

    # ── 4. Bear ───────────────────────────────────────────────────────────────
    section("BEAR ANALYST")
    bear = result["bear_analysis"]
    print(f"Confidence:          {bear.confidence}/10")
    print(f"Worst-Case Target:   ${bear.worst_case_target:,.2f}  ({bear.worst_case_timeline})")
    if bear.pe_ratio:
        print(f"PE Used in Analysis: {bear.pe_ratio:.1f}x")
    print("\nCompetition Threats:")
    for t in bear.competition_threats:
        print(f"  ✗ {t}")
    print(f"\nValuation Concerns: {bear.valuation_concerns}")
    print("\nCyclical Risks:")
    for r in bear.cyclical_risks:
        print(f"  ⚠ {r}")

    # ── 5. Portfolio Strategist ───────────────────────────────────────────────
    section("PORTFOLIO STRATEGIST")
    strat = result["strategist_analysis"]
    print(f"Current Exposure:         {strat.current_exposure}")
    print(f"Concentration Risk:       {strat.concentration_risk}")
    print(f"Concentration Reasoning:  {strat.concentration_explanation}")
    print(f"Recommended Allocation:   ${strat.recommended_allocation:,.0f}")
    print(f"\nReasoning: {strat.reasoning}")
    if strat.alternative_options:
        print("\nAlternatives:")
        for alt in strat.alternative_options:
            print(f"  • {alt}")

    # ── 6. Final recommendation ───────────────────────────────────────────────
    section("FINAL RECOMMENDATION (Judge)")
    rec = result["final_recommendation"]
    print(f"Action:               {rec.action.upper()}")
    print(f"Recommended Amount:   ${rec.recommended_amount:,.0f}")
    print(f"Overall Confidence:   {rec.confidence_overall}%")
    print(f"Entry Strategy:       {rec.entry_strategy}")
    print(f"Risk Management:      {rec.risk_management}")
    print(f"\nReasoning:\n  {rec.reasoning}")
    print("\nConfidence Breakdown:")
    bd = rec.confidence_breakdown
    for label, val in [
        ("Growth Potential", bd.growth_potential),
        ("Risk Level",       bd.risk_level),
        ("Portfolio Fit",    bd.portfolio_fit),
        ("Timing",           bd.timing),
        ("Execution Clarity",bd.execution_clarity),
    ]:
        bar = "█" * (val // 5) + "░" * (20 - val // 5)
        print(f"  {label:<20} [{bar}] {val}%")
    print("\nKey Decision Factors:")
    for i, f in enumerate(rec.key_factors, 1):
        print(f"  {i}. {f}")

    section("DONE")


if __name__ == "__main__":
    main()
