#!/usr/bin/env python3
"""
InvestiGate Demo Script
=======================
Runs a complete end-to-end analysis and pretty-prints the results.

Usage:
  python demo.py                       # NVDA, $5,000, $100,000 portfolio
  python demo.py AAPL 10000 200000     # custom ticker / amount / portfolio
  python demo.py TSLA 3000 50000 --json  # raw JSON output

Requires backend/.env to be configured (./start.sh sets this up automatically).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

# ── Path setup ────────────────────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_DIR, ".env"))

import config
config.validate()


# ── Terminal colours ──────────────────────────────────────────────────────────

def _c(code: str, t: str) -> str:
    return f"\033[{code}m{t}\033[0m"

green  = lambda t: _c("32", t)
red    = lambda t: _c("31", t)
yellow = lambda t: _c("33", t)
bold   = lambda t: _c("1",  t)
cyan   = lambda t: _c("36", t)
dim    = lambda t: _c("2",  t)
blue   = lambda t: _c("34", t)


# ── Demo portfolio (used for hidden-exposure check) ───────────────────────────

DEMO_HOLDINGS = [
    {"ticker": "SPY",  "value": 40_000},
    {"ticker": "QQQ",  "value": 25_000},
    {"ticker": "AAPL", "value": 15_000},
    {"ticker": "MSFT", "value": 10_000},
    {"ticker": "BND",  "value": 10_000},
]


# ── Main ──────────────────────────────────────────────────────────────────────

def run_demo(
    ticker: str          = "NVDA",
    amount: float        = 5_000.0,
    portfolio_value: float = 100_000.0,
    risk_tolerance: str  = "moderate",
    time_horizon: str    = "3 years",
    output_json: bool    = False,
) -> None:

    from workflow import run_analysis
    from portfolio_analyzer import calculate_hidden_exposure
    from kelly import compute_kelly_sizing

    print()
    print(bold(cyan("╔══════════════════════════════════════════════════╗")))
    print(bold(cyan("║       InvestiGate — End-to-End Demo Analysis     ║")))
    print(bold(cyan("╚══════════════════════════════════════════════════╝")))
    print()
    print(f"  {bold('Ticker:')}           {ticker}")
    print(f"  {bold('Investment:')}       ${amount:,.0f}")
    print(f"  {bold('Portfolio:')}        ${portfolio_value:,.0f}")
    print(f"  {bold('Risk tolerance:')}   {risk_tolerance}")
    print(f"  {bold('Time horizon:')}     {time_horizon}")
    print(f"  {bold('LLM provider:')}     {config.PROVIDER.value}")
    print()
    print(dim("  ⏳  Running multi-agent debate … (60-120s with local Ollama)"))
    print()

    t0 = time.time()
    try:
        state = run_analysis(
            ticker=ticker.upper(),
            amount=amount,
            portfolio_value=portfolio_value,
            risk_tolerance=risk_tolerance,
            time_horizon=time_horizon,
        )
    except Exception as e:
        print(red(f"  ✗  Analysis failed: {e}"))
        sys.exit(1)

    elapsed = round(time.time() - t0, 1)

    bull   = state["bull_analysis"]
    bear   = state["bear_analysis"]
    strat  = state["strategist_analysis"]
    judge  = state["final_recommendation"]
    mdata  = state.get("market_data") or {}

    kelly = compute_kelly_sizing(bull, bear, strat, mdata, amount, portfolio_value)

    try:
        exposure = calculate_hidden_exposure(DEMO_HOLDINGS, ticker.upper(), amount)
    except Exception:
        exposure = {}

    # ── JSON mode ──────────────────────────────────────────────────────────────
    if output_json:
        print(json.dumps({
            "ticker":           ticker,
            "amount":           amount,
            "portfolio_value":  portfolio_value,
            "elapsed_seconds":  elapsed,
            "bull":             bull.model_dump(),
            "bear":             bear.model_dump(),
            "strategist":       strat.model_dump(),
            "judge":            judge.model_dump(),
            "kelly":            kelly,
            "exposure":         exposure,
        }, indent=2))
        return

    # ── Pretty print ──────────────────────────────────────────────────────────
    price = mdata.get("currentPrice") or mdata.get("current_price") or "N/A"
    print(bold(f"  ══ {ticker}  ·  ${price}  ══"))
    print()

    # Traffic light
    bull_c = bull.confidence * 10
    bear_c = bear.confidence * 10
    gap    = abs(bull_c - bear_c)
    net    = bull_c - bear_c
    action = (judge.action or "hold").lower()
    if action == "sell" or net < -20:
        light = red("🔴  HIGH RISK")
    elif net > 20 and bull_c >= 60 and action == "buy":
        light = green("🟢  LOW RISK")
    else:
        light = yellow("🟡  CAUTION")

    print(f"  Traffic Light:    {light}")
    print(f"  Conviction gap:   {gap:.0f} pts  (Bull {bull_c:.0f} / Bear {bear_c:.0f})")
    print()

    # Judge verdict
    act_str = action.upper()
    act_col = green(act_str) if act_str == "BUY" else (red(act_str) if act_str == "SELL" else yellow(act_str))
    print(bold("  ⚖️   JUDGE / CIO VERDICT"))
    print(f"    Action:              {act_col}")
    print(f"    Recommended amount:  ${judge.recommended_amount:,.0f}")
    print(f"    Overall confidence:  {judge.confidence_overall}%")
    print(f"    Entry strategy:      {judge.entry_strategy}")
    print(f"    Risk management:     {judge.risk_management}")
    print()
    print(f"    {dim(judge.reasoning[:260])}...")
    print()

    # Kelly sizing
    print(bold("  📐  KELLY CRITERION SIZING"))
    print(f"    Raw Kelly fraction:    {kelly['kelly_fraction']:.1%}")
    print(f"    Raw Kelly amount:      ${kelly['raw_kelly_amount']:,.0f}")
    print(f"    Correlation adjusted:  ${kelly['correlation_adjusted_amount']:,.0f}")
    final_amt = f"${kelly['final_amount']:,.0f}"
    print(f"    ► Final recommended:   {bold(final_amt)}")
    print(f"    {dim(kelly['sizing_rationale'])}")
    print()

    # Bull
    print(bold("  🐂  BULL ANALYST  ") + f"(conviction {bull.confidence}/10)")
    print(f"    Target: ${bull.best_case_target:,.0f} in {bull.best_case_timeline}")
    for a in bull.competitive_advantages[:3]:
        print(f"    {green('✓')} {a}")
    print()

    # Bear
    print(bold("  🐻  BEAR ANALYST  ") + f"(conviction {bear.confidence}/10)")
    print(f"    Worst case: ${bear.worst_case_target:,.0f} in {bear.worst_case_timeline}")
    for t in bear.competition_threats[:3]:
        print(f"    {red('✗')} {t}")
    print()

    # Strategist
    print(bold("  📊  PORTFOLIO STRATEGIST"))
    print(f"    Concentration risk:    {strat.concentration_risk}")
    print(f"    Recommended alloc:     ${strat.recommended_allocation:,.0f}")
    print(f"    {dim(strat.reasoning[:220])}...")
    print()

    # Hidden exposure
    if exposure:
        print(bold("  🔍  HIDDEN EXPOSURE"))
        print(f"    Current exposure (direct + ETF):  ${exposure.get('total_current',0):,.0f}  ({exposure.get('current_pct',0):.1f}%)")
        print(f"    After purchase:                   ${exposure.get('new_exposure',0):,.0f}  ({exposure.get('proposed_pct',0):.1f}%)")
        if exposure.get("exceeds_15pct"):
            print(f"    {red('⚠️   Exceeds 15% single-stock guideline!')}")
        print()

    # Confidence breakdown
    print(bold("  📈  CONFIDENCE BREAKDOWN"))
    cb = judge.confidence_breakdown
    for field, val in cb.model_dump().items():
        label = field.replace("_", " ").title()
        filled = int(val / 5)
        bar = blue("█" * filled) + dim("░" * (20 - filled))
        print(f"    {label:<22} {bar}  {val}%")
    print()

    print(dim(f"  ✓  Completed in {elapsed}s  ·  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    print()


if __name__ == "__main__":
    raw = sys.argv[1:]

    output_json = "--json" in raw
    args = [a for a in raw if a != "--json"]

    ticker          = args[0] if len(args) > 0 else "NVDA"
    amount          = float(args[1]) if len(args) > 1 else 5_000.0
    portfolio_value = float(args[2]) if len(args) > 2 else 100_000.0

    run_demo(
        ticker=ticker,
        amount=amount,
        portfolio_value=portfolio_value,
        output_json=output_json,
    )
