"""
Professional Investment Agents — v3 Hedge-Fund Quality

Replaces agents.py (Python uses the package when both exist in the same directory).

Each agent:
  1. Fetches peer comparisons / historical patterns via data_fetcher
  2. Builds an institutional-grade prompt grounded in live data + RAG
  3. Returns a validated Pydantic schema (Ollama + cloud compatible)
"""

import json
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import TypeVar, Type

from schemas import BullAnalysis, BearAnalysis, StrategistAnalysis, JudgeRecommendation, VerifiedClaim
from llm_factory import get_analyst_llm, get_judge_llm
from tools import format_market_context
import config
from config import Provider

from agents.data_fetcher import (
    fetch_peer_data,
    fetch_historical_patterns,
    fetch_competitive_threats,
    fetch_portfolio_metrics,
    fetch_earnings_highlights,
)

T = TypeVar("T")

_NO_RAG = "[No additional documents available — rely on market data above.]"


# ══════════════════════════════════════════════════════════════════════════════
# Shared JSON / LLM helpers
# ══════════════════════════════════════════════════════════════════════════════

def _extract_json_text(text: str) -> dict:
    if not isinstance(text, str):
        text = str(text)
    try:
        obj = json.loads(text.strip())
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No JSON object found in model output: {text[:300]!r}")


def _coerce_claim_list(value) -> list[dict]:
    """Normalize model claim lists into VerifiedClaim-compatible dicts."""
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]

    result: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            claim_text = (
                item.get("claim")
                or item.get("text")
                or item.get("threat")
                or item.get("risk")
                or str(item)
            )
            result.append(
                {
                    "claim": str(claim_text),
                    "is_speculative": bool(item.get("is_speculative", False)),
                }
            )
        else:
            result.append({"claim": str(item), "is_speculative": False})
    return result


def _normalize_schema_payload(obj: dict, schema_cls: Type[T]) -> dict:
    """Apply schema-specific compatibility fixes for noisy local model JSON."""
    data = dict(obj)

    if schema_cls is BearAnalysis:
        if "competition_threats" not in data:
            for alt in (
                "competitive_threats",
                "competitive_risks",
                "threats",
                "key_risks",
            ):
                if alt in data:
                    data["competition_threats"] = data.get(alt)
                    break
        data["competition_threats"] = _coerce_claim_list(data.get("competition_threats"))
        data["cyclical_risks"] = _coerce_claim_list(data.get("cyclical_risks"))

    if schema_cls is BullAnalysis:
        data["competitive_advantages"] = _coerce_claim_list(data.get("competitive_advantages"))
        data["growth_catalysts"] = _coerce_claim_list(data.get("growth_catalysts"))

    return data


def _parse_schema(raw, schema_cls: Type[T]) -> T:
    if isinstance(raw, schema_cls):
        return raw
    if isinstance(raw, str):
        obj = _extract_json_text(raw)
    elif isinstance(raw, dict):
        obj = raw
    else:
        try:
            obj = _extract_json_text(raw.content)
        except Exception:
            raise ValueError(f"Cannot parse {type(raw).__name__} into {schema_cls.__name__}")
    if len(obj) == 1:
        inner = next(iter(obj.values()))
        if isinstance(inner, dict):
            try:
                return schema_cls.model_validate(_normalize_schema_payload(inner, schema_cls))
            except Exception:
                pass
    return schema_cls.model_validate(_normalize_schema_payload(obj, schema_cls))


def _invoke(base_llm, schema_cls: Type[T], prompt: str) -> T:
    if config.PROVIDER == Provider.OLLAMA:
        llm = base_llm.with_structured_output(schema_cls, method="json_mode", include_raw=True)
        result = llm.invoke(prompt)
        parsed = result.get("parsed")
        if parsed is not None and isinstance(parsed, schema_cls):
            return parsed
        raw_msg = result.get("raw")
        raw_text = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        return _parse_schema(raw_text, schema_cls)
    else:
        llm = base_llm.with_structured_output(schema_cls)
        return llm.invoke(prompt)


# ── Ollama JSON skeletons ─────────────────────────────────────────────────────

_BULL_SKELETON = """\
Output ONLY a JSON object with EXACTLY these top-level fields (no extra wrapper keys):
{
  "competitive_advantages": [
    {"claim": "string", "is_speculative": true | false},
    ...
  ],
  "growth_catalysts": [
    {"claim": "string", "is_speculative": true | false},
    ...
  ],
  "valuation_justification": "string",
  "best_case_target": <number>,
  "best_case_timeline": "string",
  "confidence": <integer 0-10>,
  "pe_ratio": <number or null>
}"""

_BEAR_SKELETON = """\
Output ONLY a JSON object with EXACTLY these top-level fields (no extra wrapper keys):
{
  "competition_threats": [
    {"claim": "string", "is_speculative": true | false},
    ...
  ],
  "valuation_concerns": "string",
  "cyclical_risks": [
    {"claim": "string", "is_speculative": true | false},
    ...
  ],
  "worst_case_target": <number>,
  "worst_case_timeline": "string",
  "confidence": <integer 0-10>,
  "pe_ratio": <number or null>
}"""

_STRATEGIST_SKELETON = """\
Output ONLY a JSON object with EXACTLY these top-level fields (no extra wrapper keys):
{
  "current_exposure": "string",
  "concentration_risk": "LOW" | "MODERATE" | "HIGH" | "VERY HIGH",
  "concentration_explanation": "string",
  "recommended_allocation": <number>,
  "reasoning": "string",
  "alternative_options": ["plain text string describing one alternative", ...]
}

IMPORTANT: alternative_options must be a list of PLAIN TEXT STRINGS only.
WRONG:  "alternative_options": [{"ticker": "VWO", "amount": "$20"}]
CORRECT: "alternative_options": ["Consider VWO (Vanguard Emerging Markets ETF) as a diversified alternative"]
Each element must be a single human-readable sentence, NOT an object or dict."""

_JUDGE_SKELETON = """\
Output ONLY a JSON object with EXACTLY these top-level fields (no extra wrapper keys):
{
  "action": "buy" | "hold" | "sell",
  "recommended_amount": <number>,
  "reasoning": "string",
  "confidence_overall": <integer 0-100>,
  "confidence_breakdown": {
    "growth_potential": <integer 0-100>,
    "risk_level": <integer 0-100>,
    "portfolio_fit": <integer 0-100>,
    "timing": <integer 0-100>,
    "execution_clarity": <integer 0-100>
  },
  "entry_strategy": "string",
  "risk_management": "string",
  "traffic_light_color": "red" | "yellow" | "green",
  "evaluated_scenarios": [
    {"scenario_name": "string", "verified_analog_used": "string"},
    ...
  ],
  "key_factors": ["string", ...],
  "evidence_assessment": {
    "bull": {"data_citations": 0, "calculation_rigor": 0, "historical_precedent": 0, "counterargument": 0, "total": 0},
    "bear": {"data_citations": 0, "calculation_rigor": 0, "historical_precedent": 0, "counterargument": 0, "total": 0},
    "strategist": {"data_citations": 0, "calculation_rigor": 0, "historical_precedent": 0, "counterargument": 0, "total": 0},
    "bull_weighted": 0.0,
    "bear_weighted": 0.0,
    "strategist_weighted": 0.0,
    "winner": "bull" | "bear" | "strategist",
    "winner_reasoning": "string"
  }
}"""


def _schema_hint(skeleton: str) -> str:
    return ("\n\n" + skeleton) if config.PROVIDER == Provider.OLLAMA else ""


# ── Market data helper ────────────────────────────────────────────────────────

def _md(market_data: dict, *keys, default=0):
    """Try multiple key names; return first non-None value or default."""
    for k in keys:
        v = market_data.get(k)
        if v is not None:
            return v
    return default


# ── Peer formatter ────────────────────────────────────────────────────────────

def _format_peers(peer_data: dict) -> str:
    peers = peer_data.get("peers", [])
    medians = peer_data.get("median_metrics", {})
    if not peers:
        return "[Peer data unavailable — use sector knowledge]"
    lines = ["Ticker   Fwd P/E   Rev Growth   Gross Margin   ROE"]
    for p in peers:
        lines.append(
            f"{p['ticker']:6s}   {p['forward_pe']:5.1f}x   "
            f"{p['revenue_growth_pct']:+6.1f}%       "
            f"{p['gross_margin_pct']:5.1f}%       "
            f"{p['roe_pct']:5.1f}%"
        )
    if medians:
        lines.append(
            f"{'MEDIAN':6s}   {medians.get('median_forward_pe',0):5.1f}x   "
            f"{medians.get('median_revenue_growth_pct',0):+6.1f}%       "
            f"{medians.get('median_gross_margin_pct',0):5.1f}%       "
            f"{medians.get('median_roe_pct',0):5.1f}%"
        )
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 🐂 BULL ANALYST — Senior Equity Analyst
# ══════════════════════════════════════════════════════════════════════════════

def run_bull_agent(
    ticker: str,
    market_data: dict,
    rag_context: str = "",
    amount: float = 0,
    portfolio_value: float = 0,
    analysis_action: str = "buy",
    scenarios: list[str] = None,
) -> BullAnalysis:
    """Professional bull analyst with peer comparisons and institutional-grade prompts."""

    scenarios = scenarios or []
    scenario_text = "\n".join(f"- {s}" for s in scenarios) if scenarios else "None."

    peer_data    = fetch_peer_data(ticker)
    peers_text   = _format_peers(peer_data)
    earnings_txt = fetch_earnings_highlights(ticker, market_data)

    price        = _md(market_data, "currentPrice", "current_price")
    fwd_pe       = _md(market_data, "forwardPE",    "forward_pe")
    trailing_pe  = _md(market_data, "trailingPE",   "trailing_pe")
    peg          = _md(market_data, "pegRatio")
    rev_growth   = _md(market_data, "revenueGrowth")  * 100
    earn_growth  = _md(market_data, "earningsGrowth") * 100
    gross_m      = _md(market_data, "grossMargins")    * 100
    op_m         = _md(market_data, "operatingMargins")* 100
    net_m        = _md(market_data, "profitMargins")   * 100
    roe          = _md(market_data, "returnOnEquity")  * 100
    fcf_b        = _md(market_data, "freeCashflow") / 1e9
    rev_b        = _md(market_data, "totalRevenue") / 1e9
    cap_b        = _md(market_data, "marketCap") / 1e9
    beta         = _md(market_data, "beta", default=1.0)
    hi52         = _md(market_data, "fiftyTwoWeekHigh")
    lo52         = _md(market_data, "fiftyTwoWeekLow")
    cash_b       = _md(market_data, "totalCash") / 1e9
    debt_b       = _md(market_data, "totalDebt") / 1e9
    debt_eq      = _md(market_data, "debtToEquity")
    ev_rev       = _md(market_data, "enterpriseToRevenue")
    ev_ebitda    = _md(market_data, "enterpriseToEbitda")
    tgt_mean     = _md(market_data, "targetMeanPrice")
    tgt_hi       = _md(market_data, "targetHighPrice")
    tgt_lo       = _md(market_data, "targetLowPrice")
    n_analysts   = int(_md(market_data, "numberOfAnalystOpinions"))
    rec_key      = (market_data.get("recommendationKey") or "N/A").upper()
    fwd_eps      = _md(market_data, "forwardEps")
    proposed_pct = (amount / portfolio_value * 100) if portfolio_value > 0 else 0

    # ── Action-specific framing ───────────────────────────────────────────────
    if analysis_action == "sell":
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is considering SELLING their {ticker} position.
  Your role: Argue AGAINST selling — make the strongest case that the bull thesis is still alive
  and the investor should HOLD or ADD to the position rather than sell.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Write the STRONGEST case for why the investor should NOT sell {ticker} — upside remains."
    elif analysis_action == "hold":
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is deciding whether to HOLD or exit their {ticker} position.
  Your role: Argue FOR HOLDING — the long-term investment thesis remains compelling.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Write the STRONGEST case for why the investor should HOLD {ticker} long-term."
    else:  # buy
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is considering BUYING ${amount:,.0f} of {ticker} ({proposed_pct:.1f}% of ${portfolio_value:,.0f} portfolio).
  Your role: Argue FOR buying — make the strongest bull case.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Write the STRONGEST possible bull case for {ticker}."

    prompt = f"""You are a Managing Director — Senior Equity Analyst at a top-tier hedge fund ($50B AUM).
Your investment memos have generated $2B+ in alpha over 10 years.

{action_header}

━━━ LIVE MARKET DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALUATION:
• Current Price:      ${price:.2f}
• Market Cap:         ${cap_b:.1f}B
• Forward P/E:        {fwd_pe:.1f}x   |  Trailing P/E: {trailing_pe:.1f}x
• PEG Ratio:          {peg:.2f}       |  EV/Revenue: {ev_rev:.2f}x  |  EV/EBITDA: {ev_ebitda:.2f}x
• 52-week Range:      ${lo52:.2f} – ${hi52:.2f}

GROWTH & PROFITABILITY:
• Revenue (TTM):      ${rev_b:.1f}B   |  Rev Growth: {rev_growth:+.1f}% YoY
• Earnings Growth:    {earn_growth:+.1f}% YoY
• Gross Margin:       {gross_m:.1f}%  |  Operating Margin: {op_m:.1f}%  |  Net Margin: {net_m:.1f}%
• ROE:                {roe:.1f}%      |  Beta: {beta:.2f}

BALANCE SHEET & CASH FLOW:
• Free Cash Flow:     ${fcf_b:.1f}B TTM
• Cash:               ${cash_b:.1f}B  |  Debt: ${debt_b:.1f}B  |  D/E: {debt_eq:.2f}
• Forward EPS:        ${fwd_eps:.2f}

ANALYST CONSENSUS ({n_analysts} analysts):
• Mean Target: ${tgt_mean:.2f}  |  Range: ${tgt_lo:.2f}–${tgt_hi:.2f}  |  Rating: {rec_key}

━━━ RECENT EARNINGS & GUIDANCE HIGHLIGHTS ━━━━━━━━━━━━━━━━
{earnings_txt}

━━━ SEC FILINGS & NEWS (RAG) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rag_context or _NO_RAG}

━━━ PEER COMPARISON ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{peers_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR TASK: {task_line}

ANALYSIS REQUIREMENTS & CHAIN-OF-VERIFICATION (CoVe):
1. Investment thesis (2-3 sentences: expected return, timeline, key catalyst).
2. Revenue model & factors.
3. Valuation justification.
4. Specific price target derived from REAL current price (${price:.2f}).
5. 3-5 key risks monitored.
6. Conviction 0-10.
7. SCENARIO EVALUATION: For any macro stress-test scenarios provided below, evaluate the asset utilizing historical analogs from the RAG context.
8. CHAIN-OF-VERIFICATION: You MUST verify every numerical claim (margins, growth rates, etc.) against the LIVE MARKET DATA or SEC FILINGS (RAG) sections. Unverified claims MUST be flagged as `is_speculative: true` in your JSON output.

STRESS-TEST SCENARIOS TO EVALUATE:
{scenario_text}

Use specific numbers. Cite sources ("per management guidance", "SEC 10-K", "consensus estimate").
Cite recent earnings headlines above when relevant.
Goldman Sachs equity research quality. Dense, professional, data-driven.{_schema_hint(_BULL_SKELETON)}"""

    return _invoke(get_analyst_llm(), BullAnalysis, prompt)


# ══════════════════════════════════════════════════════════════════════════════
# 🐻 BEAR ANALYST — Veteran Short Seller
# ══════════════════════════════════════════════════════════════════════════════

def run_bear_agent(
    ticker: str,
    market_data: dict,
    rag_context: str = "",
    amount: float = 0,
    portfolio_value: float = 0,
    analysis_action: str = "buy",
    scenarios: list[str] = None,
) -> BearAnalysis:
    """Professional bear analyst with historical pattern analysis and competitive threats."""

    scenarios = scenarios or []
    scenario_text = "\n".join(f"- {s}" for s in scenarios) if scenarios else "None."

    hist         = fetch_historical_patterns(ticker)
    peer_data    = fetch_peer_data(ticker)
    peers_text   = _format_peers(peer_data)
    comp_threats = fetch_competitive_threats(ticker, market_data)

    price        = _md(market_data, "currentPrice", "current_price")
    fwd_pe       = _md(market_data, "forwardPE",    "forward_pe")
    peg          = _md(market_data, "pegRatio")
    rev_growth   = _md(market_data, "revenueGrowth")   * 100
    gross_m      = _md(market_data, "grossMargins")     * 100
    op_m         = _md(market_data, "operatingMargins") * 100
    ev_rev       = _md(market_data, "enterpriseToRevenue")
    short_pct    = _md(market_data, "shortPercentOfFloat") * 100
    debt_b       = _md(market_data, "totalDebt") / 1e9
    debt_eq      = _md(market_data, "debtToEquity")

    hist_text = (
        f"5Y High: ${hist.get('high_5y',0):.2f}  |  5Y Low: ${hist.get('low_5y',0):.2f}  |  "
        f"Current vs 5Y High: {hist.get('pct_from_5y_high',0):+.1f}%  |  "
        f"1Y Return: {hist.get('return_1y_pct',0):+.1f}%  |  "
        f"Annualised Vol: {hist.get('volatility_annualised_pct',0):.1f}%"
    ) if hist else "[Historical data unavailable]"

    # ── Action-specific framing ───────────────────────────────────────────────
    if analysis_action == "sell":
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is considering SELLING their {ticker} position.
  Your role: Argue FOR SELLING — make the strongest case that now is the right time to exit.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Write the STRONGEST case for why the investor should SELL {ticker} now."
    elif analysis_action == "hold":
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is deciding whether to HOLD or exit their {ticker} position.
  Your role: Argue AGAINST holding — make the case for REDUCING or EXITING the position.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Write the STRONGEST case for why the investor should EXIT or REDUCE {ticker}."
    else:  # buy
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is considering BUYING {ticker}.
  Your role: Argue AGAINST buying — make the strongest bear case.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Write the most DEVASTATING possible bear case for {ticker}."

    prompt = f"""You are a veteran Short Seller with a 20-year track record at a top hedge fund.
You've successfully called: Dot-com bubble (2000), Housing crisis (2008), Crypto winter (2022).
Your job: Find flaws in the bull thesis. Be the voice of rigorous, evidence-based skepticism.

{action_header}

━━━ LIVE MARKET DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Current Price:      ${price:.2f}
• Forward P/E:        {fwd_pe:.1f}x   |  PEG Ratio: {peg:.2f}
• Revenue Growth:     {rev_growth:+.1f}% YoY  (sustainable or cyclical peak?)
• Gross Margin:       {gross_m:.1f}%   |  Operating Margin: {op_m:.1f}%  (at cyclical peak?)
• EV/Revenue:         {ev_rev:.2f}x    (stretched vs peers?)
• Short Interest:     {short_pct:.1f}% of float
• Total Debt:         ${debt_b:.1f}B   |  D/E: {debt_eq:.2f}

━━━ HISTORICAL CONTEXT (5-Year) ━━━━━━━━━━━━━━━━━━━━━━━━━
{hist_text}

━━━ COMPETITIVE THREATS (from news) ━━━━━━━━━━━━━━━━━━━━━━
{comp_threats}

━━━ SEC FILINGS & NEWS (RAG) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rag_context or _NO_RAG}

━━━ PEER COMPARISON ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{peers_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR TASK: {task_line}

ANALYSIS REQUIREMENTS & CHAIN-OF-VERIFICATION (CoVe):
1. Counter-thesis (2-3 sentences: core bear case, downside, catalyst).
2. Challenge bull assumptions.
3. Structural headwinds.
4. Downside scenario price target.
5. Conviction 0-10.
6. SCENARIO EVALUATION: For any macro stress-test scenarios provided below, evaluate the asset utilizing historical analogs from the RAG context (e.g., 2008 GFC, 1970s stagflation). 
7. CHAIN-OF-VERIFICATION: You MUST verify every numerical claim against the LIVE MARKET DATA or SEC FILINGS (RAG) sections. Unverified claims MUST be flagged as `is_speculative: true` in your JSON output.

STRESS-TEST SCENARIOS TO EVALUATE:
{scenario_text}

"History suggests..." not "I believe...". Use historical data above.
Acknowledge bull's valid points — a fair bear case is more credible than a one-sided hit piece.{_schema_hint(_BEAR_SKELETON)}"""

    return _invoke(get_analyst_llm(), BearAnalysis, prompt)


# ══════════════════════════════════════════════════════════════════════════════
# 📊 PORTFOLIO STRATEGIST — Head of Portfolio Construction
# ══════════════════════════════════════════════════════════════════════════════

def run_strategist_agent(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    market_data: dict,
    rag_context: str = "",
    portfolio_holdings: list | None = None,
    analysis_action: str = "buy",
    scenarios: list[str] = None,
) -> StrategistAnalysis:
    """Professional portfolio strategist with portfolio hidden-exposure logic."""

    pm = {}
    if portfolio_holdings:
        pm = fetch_portfolio_metrics(portfolio_holdings, ticker, amount)

    proposed_pct = (amount / portfolio_value * 100) if portfolio_value > 0 else 0

    if pm.get("exposure"):
        exp  = pm["exposure"]
        corr = pm.get("correlation", {})
        indirect_lines = "\n".join(
            f"    • {r['etf']}: ${r['amount']:,.0f} ({r['weight_pct']:.1f}% of ETF)"
            for r in exp.get("indirect_rows", [])
        ) or "    • None detected"
        sector_lines = "\n".join(
            f"  • {s}: {p:.1f}%" for s, p in pm.get("sector_allocation", {}).items()
        )
        portfolio_block = f"""CURRENT PORTFOLIO:
• Total Value:        ${pm.get('total_value', portfolio_value):,.0f}
• Holdings:           {pm.get('num_holdings', '?')}
• Concentration:      {pm.get('concentration_label', 'UNKNOWN')}
  Top 1:  {pm.get('top_1_pct', 0):.1f}% | Top 3: {pm.get('top_3_pct', 0):.1f}% | Top 5: {pm.get('top_5_pct', 0):.1f}%
• International:      {pm.get('international_pct', 0):.1f}%
• Bonds:              {pm.get('bond_pct', 0):.1f}%

SECTOR ALLOCATION:
{sector_lines}

{ticker} EXPOSURE (direct + via ETFs):
• Direct:             ${exp.get('direct', 0):,.0f}
• Via ETFs:           ${exp.get('total_indirect', 0):,.0f}
{indirect_lines}
• TOTAL CURRENT:      ${exp.get('total_current', 0):,.0f} ({exp.get('current_pct', 0):.1f}%)
• AFTER PURCHASE:     ${exp.get('new_exposure', 0):,.0f} ({exp.get('proposed_pct', 0):.1f}%)
• Exceeds 15% limit:  {"⚠️  YES" if exp.get('exceeds_15pct') else "✓  NO"}

CORRELATION:
• Avg with portfolio: {corr.get('avg_with_portfolio', 0.65):.2f}
• Diversif. benefit:  {corr.get('diversification_benefit', 'MEDIUM')}
• New position sector:{corr.get('new_position_sector', 'Unknown')}"""
    else:
        portfolio_block = f"""PORTFOLIO CONTEXT:
• Portfolio Value:    ${portfolio_value:,.0f}
• Proposed:          ${amount:,.0f} ({proposed_pct:.1f}%)
• Risk Tolerance:    {risk_tolerance}"""

    # ── Action-specific framing ───────────────────────────────────────────────
    if analysis_action == "sell":
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is considering SELLING their {ticker} position.
  Your role: Evaluate the portfolio impact of selling — does it improve or hurt diversification?
  Consider tax implications, freed capital redeployment, and concentration relief.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Analyse whether selling {ticker} would improve portfolio health. Where should the freed capital go?"
    elif analysis_action == "hold":
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is deciding whether to HOLD or exit their {ticker} position.
  Your role: Assess the portfolio construction case for holding vs trimming.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Analyse whether the current {ticker} position size is appropriate to maintain."
    else:  # buy
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ The investor is considering adding ${amount:,.0f} to {ticker}.
  Your role: Analyse concentration, correlation, and rebalancing implications.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        task_line = f"Analyse the portfolio-level implications of adding ${amount:,.0f} to {ticker}."

    prompt = f"""You are the Head of Portfolio Construction at a $50B multi-strategy hedge fund.
Philosophy: Diversification is the only free lunch. Risk management > return maximisation.

{action_header}

━━━ LIVE MARKET DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{format_market_context(market_data)}

━━━ SEC FILINGS & NEWS (RAG) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rag_context or _NO_RAG}

━━━ PORTFOLIO ANALYSIS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{portfolio_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR TASK: {task_line}

YOUR ANALYSIS FRAMEWORK:

1. PORTFOLIO HEALTH (The Look-Through Engine)
   Red flags: single stock >15%, sector >30%, zero international, 100% equities, zero bonds.
   Mandate: Calculate "Hidden Exposure". Look inside diversified ETFs (SPY, QQQ) using the portfolio analysis metrics provided above to find overlapping concentration. Highlight this clearly in the `concentration_explanation`.

2. REBALANCING STRATEGIES (2-3 options)
   Strategy A: Trim concentrated position → free up room for {ticker}
     • Sell $X of [specific ETF/ticker], redeploy to [diversifier]
     • Result: {ticker} exposure drops from X% to Y%
   Strategy B: Dilute risk via uncorrelated asset (no sales required)
     • Add $X to [specific low-correlation ticker] alongside {ticker}
   Strategy C: Accept risk + monitor
     • Proceed with ${amount:,.0f} | Set alert at -10% | Review quarterly

3. FINAL RECOMMENDATION
   • Dollar amount to invest (may differ from proposed ${amount:,.0f} if limits exceeded)
   • Concentration risk: LOW / MODERATE / HIGH / VERY HIGH
   • Explanation of risk vs the 15% guideline
   • Alternative tickers (SPECIFIC symbols, not vague "diversify")

Every recommendation must have EXACT DOLLAR AMOUNTS and EXACT TICKERS.
Risk tolerance: {risk_tolerance}{_schema_hint(_STRATEGIST_SKELETON)}"""

    return _invoke(get_analyst_llm(), StrategistAnalysis, prompt)


# ══════════════════════════════════════════════════════════════════════════════
# ⚖️ JUDGE — Chief Investment Officer
# ══════════════════════════════════════════════════════════════════════════════

def _condense_bull(bull: BullAnalysis) -> str:
    adv = [a.claim for a in bull.competitive_advantages[:2]] if bull.competitive_advantages else []
    cat = [c.claim for c in bull.growth_catalysts[:2]] if bull.growth_catalysts else []
    return (
        f"Conviction: {bull.confidence}/10  |  Target: ${bull.best_case_target:,.0f} ({bull.best_case_timeline})\n"
        f"Advantages: {'; '.join(adv)}\n"
        f"Catalysts:  {'; '.join(cat)}\n"
        f"Valuation:  {bull.valuation_justification[:200]}"
    )


def _condense_bear(bear: BearAnalysis) -> str:
    threats = [t.claim for t in bear.competition_threats[:2]] if bear.competition_threats else []
    return (
        f"Conviction: {bear.confidence}/10  |  Worst case: ${bear.worst_case_target:,.0f} ({bear.worst_case_timeline})\n"
        f"Threats:    {'; '.join(threats)}\n"
        f"Valuation:  {bear.valuation_concerns[:200]}"
    )


def _condense_strategist(strat: StrategistAnalysis) -> str:
    return (
        f"Risk: {strat.concentration_risk}  |  Recommended: ${strat.recommended_allocation:,.0f}\n"
        f"Reasoning: {strat.reasoning[:250]}"
    )


def run_judge_agent(
    ticker: str,
    bull: BullAnalysis,
    bear: BearAnalysis,
    strategist: StrategistAnalysis,
    market_data: dict,
    rag_context: str = "",
    analysis_action: str = "buy",
    scenarios: list[str] = None,
) -> JudgeRecommendation:
    """CIO-level synthesis using Evidence-Based Scoring and Hallucination Penalties."""

    scenarios = scenarios or []
    scenario_text = "\n".join(f"- {s}" for s in scenarios) if scenarios else "None."

    price     = _md(market_data, "currentPrice", "current_price")
    bull_conv = bull.confidence * 10
    bear_conv = bear.confidence * 10
    conv_gap  = abs(bull_conv - bear_conv)
    net_bull  = bull_conv - bear_conv
    signal    = "STRONG BULL" if net_bull > 20 else "STRONG BEAR" if net_bull < -20 else "MIXED"

    if config.PROVIDER == Provider.OLLAMA:
        bull_txt  = _condense_bull(bull)
        bear_txt  = _condense_bear(bear)
        strat_txt = _condense_strategist(strategist)
    else:
        bull_txt  = bull.model_dump_json(indent=2)
        bear_txt  = bear.model_dump_json(indent=2)
        strat_txt = strategist.model_dump_json(indent=2)

    # ── Action-specific framing ───────────────────────────────────────────────
    if analysis_action == "sell":
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ SHOULD THE INVESTOR SELL {ticker}?
  Bull argued: do NOT sell (upside remains)
  Bear argued: YES, sell now (risks dominate)
  Your decision: sell / hold / trim
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        action_note = 'action: "sell" means exit the position; "hold" means maintain it; "buy" means add more'
    elif analysis_action == "hold":
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ SHOULD THE INVESTOR HOLD OR EXIT {ticker}?
  Bull argued: HOLD — compelling long-term case
  Bear argued: EXIT — risks outweigh upside
  Your decision: hold / sell / buy (add more)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        action_note = 'action: "hold" means maintain position; "sell" means exit; "buy" means add more'
    else:  # buy
        action_header = f"""━━━ DEBATE QUESTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ SHOULD THE INVESTOR BUY {ticker}?
  Bull argued: YES — strong upside case
  Bear argued: NO — risks dominate
  Your decision: buy / hold / sell
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        action_note = 'action: "buy" means proceed with purchase; "hold" means wait; "sell" means avoid/exit'

    prompt = f"""You are the Chief Investment Officer allocating capital across a $10B portfolio.
Synthesise Bull, Bear, and Portfolio Strategist into ONE decisive, actionable recommendation.

{action_header}

━━━ SIGNAL SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ticker: {ticker}  |  Price: ${price:.2f}  |  Consensus: {signal}  |  Conviction gap: {conv_gap:.0f} pts
Bull conviction: {bull_conv:.0f}/100  |  Bear conviction: {bear_conv:.0f}/100

━━━ 🐂 BULL ANALYST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bull_txt}

━━━ 🐻 BEAR ANALYST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bear_txt}

━━━ 📊 PORTFOLIO STRATEGIST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{strat_txt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DECISION FRAMEWORK:

EVIDENCE EVALUATION FRAMEWORK:
CRITICAL: You must evaluate argument QUALITY, not just conviction levels.
For each analyst (Bull, Bear, Strategist), score their argument quality on these dimensions:
1. DATA CITATIONS (0-10 points): Multiple specific data points with sources (10), some data (7), vague claims (4), no data (0).
2. CALCULATION RIGOR (0-10 points): Shows work/methodology (10), mentions methodology broadly (7), states conclusion only (4), no rigor (0).
3. HISTORICAL PRECEDENT (0-10 points): Specific comparables (10), generic history (7), vague (4), no context (0).
4. COUNTERARGUMENT STRENGTH (0-10 points): Addresses opposing view directly (10), mentions opposition (7), ignores (4), one-sided (0).
TOTAL EVIDENCE SCORE = sum of 4 dimensions (max 40)

HALLUCINATION PENALTY:
Check the `is_speculative` flag on numerical claims used by the Bull and Bear.
DEDUCT 20 POINTS from the Analyst's Total Evidence Score for utilizing unverified numerical claims.

DECISION WEIGHTING FORMULA (use for evidence_assessment logic):
Weighted Score = (Analyst_Conviction × Analyst_Total_Evidence_Score) / 40
Example: 87 conviction × (35/40 evidence) = 76.1 weighted score.
Populate the `evidence_assessment` fields with these scores. The recommendation must heavily weight the analyst with the highest weighted score.
Please output the evaluated scenarios and explicitly state what verified historical analog was used to score them.

POSITION SIZING (Modified Kelly):
• Bull conv >80, Bear conv <60 + low correlation   → 100% of planned size
• Bull conv 70-80, Bear conv 60-70 + med correlation → 60-75% of size
• Mixed/high correlation                             → 30-50% or reduce to strategist cap

HARD CONSTRAINTS (must not violate):
• recommended_amount ≤ strategist's recommended_allocation
• Max 15% single-stock portfolio concentration
• {action_note}

TRAFFIC LIGHT LOGIC & SCENARIO EVALUATION:
CRITICAL: If ANY stress scenario provided below correlates with an expected >2sigma historical drawdown based on RAG precedent, the Traffic Light MUST be RED regardless of other factors.
🟢 GREEN: conviction gap <15 pts, bull dominant, low portfolio correlation
🟡 YELLOW: gap 15-30 pts, or valuation stretched but growth intact, or borderline concentration
🔴 RED: gap >30 pts, or >20% portfolio concentration, or structural headwinds dominant, OR >2sigma drawdown scenario detected.

STRESS-TEST SCENARIOS DETECTED FROM USER:
{scenario_text}

REQUIRED OUTPUT FIELDS:
• action: "buy" / "hold" / "sell"
• recommended_amount: specific dollar amount
• reasoning: 2-3 sentences integrating all three perspectives
• confidence_overall: 0-100
• confidence_breakdown: growth_potential, risk_level, portfolio_fit, timing, execution_clarity (each 0-100)
• entry_strategy: "DCA $X/month for N months" or "Single purchase at market"
• risk_management: specific price levels (-10% alert, -20% stop-loss) + traffic light color + reason
• key_factors: top 3-5 factors that drove the decision{_schema_hint(_JUDGE_SKELETON)}"""

    return _invoke(get_judge_llm(), JudgeRecommendation, prompt)


# ── Backwards-compat aliases ─────────────────────────────────────────────────

run_bull_analyst   = run_bull_agent
run_bear_analyst   = run_bear_agent
run_strategist     = run_strategist_agent
run_judge          = run_judge_agent

BULL_SYSTEM        = "Professional Bull Analyst v3"
BEAR_SYSTEM        = "Professional Bear Analyst v3"
STRATEGIST_SYSTEM  = "Professional Portfolio Strategist v3"
JUDGE_SYSTEM       = "Professional Judge / CIO v3"
