"""
Four investment agents — grounded with live market data AND RAG document context.

Every agent receives two injected blocks before being asked to reason:
  1. GROUNDING — live yfinance snapshot (price, PE, margins, consensus, news headlines)
  2. RAG       — relevant excerpts from SEC 10-K/10-Q filings and full news articles

Ollama compatibility
--------------------
Local models (llama3.1, etc.) are invoked in plain JSON mode.  Each prompt includes
the exact field skeleton so the model knows what top-level keys to output.  A
robust post-processing step extracts and validates the JSON even when the model
wraps it in an outer key.
"""

import json
import re
from typing import TypeVar, Type

from schemas import BullAnalysis, BearAnalysis, StrategistAnalysis, JudgeRecommendation
from llm_factory import get_analyst_llm, get_judge_llm
from tools import format_market_context
import config
from config import Provider

T = TypeVar("T")

# Shown in the prompt when no RAG documents were retrieved
_NO_RAG = "[No additional documents available — rely on the market data above.]"


# ── JSON extraction helpers ───────────────────────────────────────────────────

def _extract_json_text(text: str) -> dict:
    """
    Robustly extract a JSON object from a model response.

    Tries (in order):
    1. Direct parse of the whole response.
    2. Find the first {...} block (handles surrounding prose).
    3. Unwrap one level of nesting (model wrapped its output in one key).
    """
    if not isinstance(text, str):
        text = str(text)

    # 1. Direct
    try:
        obj = json.loads(text.strip())
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 2. Grep for first JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No JSON object found in model output: {text[:300]!r}")


def _parse_schema(raw, schema_cls: Type[T]) -> T:
    """
    Parse raw model output (str or already-parsed dict) into a Pydantic schema.

    If the dict has exactly one key whose value is a dict, unwrap it first
    (handles the common 'wrapping' pattern from local models).
    """
    if isinstance(raw, schema_cls):
        return raw

    if isinstance(raw, str):
        obj = _extract_json_text(raw)
    elif isinstance(raw, dict):
        obj = raw
    else:
        # Some LangChain versions return AIMessage objects
        try:
            obj = _extract_json_text(raw.content)  # type: ignore[attr-defined]
        except Exception:
            raise ValueError(f"Cannot parse {type(raw).__name__} into {schema_cls.__name__}")

    # Unwrap single-key nesting: {"bull_case": {...}} → {...}
    if len(obj) == 1:
        inner = next(iter(obj.values()))
        if isinstance(inner, dict):
            try:
                return schema_cls.model_validate(inner)
            except Exception:
                pass

    return schema_cls.model_validate(obj)


# ── Provider-aware invocation ─────────────────────────────────────────────────

def _invoke(base_llm, schema_cls: Type[T], prompt: str) -> T:
    """
    Invoke base_llm and return a validated instance of schema_cls.

    - Cloud (Anthropic / OpenAI): use with_structured_output (tool-calling) — most accurate.
    - Ollama (local): call the model directly with JSON mode and parse the response
      ourselves — local models are unreliable with tool-calling on long prompts.
    """
    if config.PROVIDER == Provider.OLLAMA:
        # json_mode tells Ollama to output JSON; our prompt supplies the field skeleton.
        llm = base_llm.with_structured_output(schema_cls, method="json_mode",
                                               include_raw=True)
        result = llm.invoke(prompt)
        # include_raw=True → {"raw": AIMessage, "parsed": ..., "parsing_error": ...}
        parsed = result.get("parsed")
        if parsed is not None and isinstance(parsed, schema_cls):
            return parsed
        # Fallback: parse from raw text
        raw_msg = result.get("raw")
        raw_text = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        return _parse_schema(raw_text, schema_cls)
    else:
        llm = base_llm.with_structured_output(schema_cls)
        return llm.invoke(prompt)


# ── Schema field skeletons (injected into Ollama prompts) ─────────────────────

_BULL_SKELETON = """\
Output ONLY a JSON object with EXACTLY these top-level fields (no extra wrapper keys):
{
  "competitive_advantages": ["string", ...],
  "growth_catalysts": ["string", ...],
  "valuation_justification": "string",
  "best_case_target": <number>,
  "best_case_timeline": "string",
  "confidence": <integer 0-10>,
  "pe_ratio": <number or null>
}"""

_BEAR_SKELETON = """\
Output ONLY a JSON object with EXACTLY these top-level fields (no extra wrapper keys):
{
  "competition_threats": ["string", ...],
  "valuation_concerns": "string",
  "cyclical_risks": ["string", ...],
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
  "alternative_options": ["string", ...]
}"""

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
  "key_factors": ["string", ...],
  "evidence_assessment": {
    "bull": {"data_citations": <0-10>, "calculation_rigor": <0-10>, "historical_precedent": <0-10>, "counterargument": <0-10>, "total": <0-40>},
    "bear": {"data_citations": <0-10>, "calculation_rigor": <0-10>, "historical_precedent": <0-10>, "counterargument": <0-10>, "total": <0-40>},
    "strategist": {"data_citations": <0-10>, "calculation_rigor": <0-10>, "historical_precedent": <0-10>, "counterargument": <0-10>, "total": <0-40>},
    "bull_weighted": <number>,
    "bear_weighted": <number>,
    "strategist_weighted": <number>,
    "winner": "bull" | "bear" | "strategist",
    "winner_reasoning": "string"
  }
}"""


def _schema_hint(skeleton: str) -> str:
    """Return the skeleton only when using a local model."""
    if config.PROVIDER == Provider.OLLAMA:
        return "\n\n" + skeleton
    return ""


# ── Bull Analyst ─────────────────────────────────────────────────────────────

_BULL_BODY = """You are a BULL ANALYST for {ticker}.

You have two verified data sources below. USE THEM. Do NOT rely on training-data
guesses for prices, PE ratios, revenue figures, or growth rates.

━━━ SOURCE 1 — LIVE MARKET DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{market_context}

━━━ SOURCE 2 — SEC FILINGS & NEWS (RAG) ━━━━━━━━━━━━━━━━━━━━
{rag_context}

Using the data above, build the STRONGEST possible bull case for investing in {ticker} NOW.

Focus on:
1. Competitive advantages supported by the financials (high/expanding margins, FCF growth,
   market-share evidence from the SEC filings or news)
2. Growth catalysts visible in the data (revenue acceleration, new markets, product pipeline
   mentioned in the 10-K Business section or recent news)
3. Valuation justification — is the current P/E warranted by the PEG ratio and growth rate?
4. A specific best-case price target derived from the REAL current price shown above,
   with a credible timeline and upside percentage

Cite actual numbers.{schema_hint}"""


def run_bull_agent(ticker: str, market_data: dict, rag_context: str = "") -> BullAnalysis:
    prompt = _BULL_BODY.format(
        ticker=ticker,
        market_context=format_market_context(market_data),
        rag_context=rag_context or _NO_RAG,
        schema_hint=_schema_hint(_BULL_SKELETON),
    )
    return _invoke(get_analyst_llm(), BullAnalysis, prompt)


# ── Bear Analyst ─────────────────────────────────────────────────────────────

_BEAR_BODY = """You are a BEAR ANALYST for {ticker}.

You have two verified data sources below. USE THEM. Do NOT rely on training-data
guesses for prices, PE ratios, revenue figures, or growth rates.

━━━ SOURCE 1 — LIVE MARKET DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{market_context}

━━━ SOURCE 2 — SEC FILINGS & NEWS (RAG) ━━━━━━━━━━━━━━━━━━━━
{rag_context}

Using the data above, build the STRONGEST possible bear case AGAINST investing in {ticker} NOW.

Focus on:
1. Valuation risk — is the current P/E and PEG ratio justified? Compare to revenue growth rate
2. Competitive threats — look for customer concentration, competitor mentions,
   or market-share risk in the 10-K Risk Factors section
3. Financial concerns — debt levels, FCF sustainability, high short interest signals
4. Macro/cyclical risks disclosed in the SEC filings (regulatory, geopolitical, supply chain)
5. A specific worst-case price target derived from the REAL current price shown above,
   with a credible timeline and downside percentage

Be skeptical. Stress-test every bullish assumption.{schema_hint}"""


def run_bear_agent(ticker: str, market_data: dict, rag_context: str = "") -> BearAnalysis:
    prompt = _BEAR_BODY.format(
        ticker=ticker,
        market_context=format_market_context(market_data),
        rag_context=rag_context or _NO_RAG,
        schema_hint=_schema_hint(_BEAR_SKELETON),
    )
    return _invoke(get_analyst_llm(), BearAnalysis, prompt)


# ── Portfolio Strategist ──────────────────────────────────────────────────────

_STRATEGIST_BODY = """You are a PORTFOLIO STRATEGIST evaluating a position in {ticker}.

You have two verified data sources below. USE THEM.

━━━ SOURCE 1 — LIVE MARKET DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{market_context}

━━━ SOURCE 2 — SEC FILINGS & NEWS (RAG) ━━━━━━━━━━━━━━━━━━━━
{rag_context}

USER PORTFOLIO CONTEXT:
  Proposed investment:   ${amount:,.0f}
  Total portfolio value: ${portfolio_value:,.0f}
  Proposed allocation:   {proposed_pct:.1f}% of portfolio
  Risk tolerance:        {risk_tolerance}

Using ALL sources above, determine the RIGHT position size:
1. Current indirect exposure via S&P 500 / Nasdaq index fund holdings
2. Concentration risk (LOW / MODERATE / HIGH / VERY HIGH)
3. Recommended allocation in dollars (number only — no $, no commas, no math)
4. Alternative options for similar exposure with less concentration risk{schema_hint}"""


def run_strategist_agent(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    market_data: dict,
    rag_context: str = "",
) -> StrategistAnalysis:
    proposed_pct = (amount / portfolio_value * 100) if portfolio_value > 0 else 0
    prompt = _STRATEGIST_BODY.format(
        ticker=ticker,
        amount=amount,
        portfolio_value=portfolio_value,
        proposed_pct=proposed_pct,
        risk_tolerance=risk_tolerance,
        market_context=format_market_context(market_data),
        rag_context=rag_context or _NO_RAG,
        schema_hint=_schema_hint(_STRATEGIST_SKELETON),
    )
    return _invoke(get_analyst_llm(), StrategistAnalysis, prompt)


# ── Judge Agent ───────────────────────────────────────────────────────────────

_JUDGE_BODY = """You are the CHIEF INVESTMENT OFFICER making the final decision on {ticker}.

Your role: Evaluate argument QUALITY alongside conviction levels — strong opinions backed by
weak evidence get downweighted; rigorous, data-driven arguments earn more influence.

━━━ LIVE MARKET DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{market_context}

━━━ BULL ANALYST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bull_analysis}

━━━ BEAR ANALYST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bear_analysis}

━━━ PORTFOLIO STRATEGIST ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{strategist_analysis}

━━━ EVIDENCE EVALUATION FRAMEWORK ━━━━━━━━━━━━━━━━━━━━━━━━━━

Score each analyst on these 4 dimensions (0-10 each, max 40 total):

1. DATA CITATIONS (0-10)
   10 = Multiple specific figures with attribution (e.g. "$47B TTM revenue per Q3 10-K", "75% GM per earnings call")
    7 = Some data points but attribution missing (e.g. "revenue growing rapidly")
    4 = Vague claims only (e.g. "strong growth", "high margins")
    0 = Pure opinion, zero data

2. CALCULATION RIGOR (0-10)
   10 = Shows full methodology (DCF with WACC breakdown, margin sensitivity table)
    7 = Mentions methodology without details (e.g. "my DCF supports this")
    4 = States conclusion only (e.g. "fair value is $165")
    0 = No valuation methodology at all

3. HISTORICAL PRECEDENT (0-10)
   10 = Specific named comparables with dates and numbers (e.g. "In 2018 cycle, GM compressed 65%→58% over 18 months")
    7 = Generic historical references (e.g. "historically margins mean-revert")
    4 = Vague (e.g. "past performance suggests...")
    0 = No historical context whatsoever

4. COUNTERARGUMENT STRENGTH (0-10)
   10 = Explicitly identifies and addresses the opposing view (e.g. "Bull's CUDA moat point is valid, but...")
    7 = Briefly acknowledges the other side
    4 = Largely ignores opposing arguments
    0 = Purely one-sided, no acknowledgement of opposing view

WEIGHTED DECISION FORMULA:
  Weighted_Score = Conviction(0-10) × (Evidence_Total / 40)
  → The analyst with the HIGHEST weighted score anchors your recommendation.
  → High conviction + poor evidence = heavily discounted
  → Strong evidence can elevate a moderate conviction over a louder but weaker argument

Example:
  Bull: conviction 8, evidence 35/40 → weighted = 8 × 0.875 = 7.0
  Bear: conviction 7, evidence 20/40 → weighted = 7 × 0.500 = 3.5
  → Bull wins despite similar conviction gap because evidence is substantially stronger

━━━ OUTPUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Produce your final decision with ALL of these fields:
1. action: buy / hold / sell
2. recommended_amount ≤ strategist's recommended_allocation
3. reasoning: synthesise the three reports; explicitly reference which analyst's evidence quality drove the decision
4. confidence_overall: 0-100
5. confidence_breakdown (5 dimensions: growth_potential, risk_level, portfolio_fit, timing, execution_clarity)
6. entry_strategy (e.g. "DCA $X/month for 3 months")
7. risk_management (e.g. "stop-loss at $Y, revisit if thesis changes")
8. key_factors: 3-5 top decision factors as a list
9. evidence_assessment: score all three analysts on the 4 dimensions, compute weighted scores, identify the winner{schema_hint}"""


def _condense_bull(bull: BullAnalysis) -> str:
    return (
        f"Confidence: {bull.confidence}/10 | Target: ${bull.best_case_target:,.0f} ({bull.best_case_timeline})\n"
        f"Advantages: {'; '.join(bull.competitive_advantages[:3])}\n"
        f"Catalysts: {'; '.join(bull.growth_catalysts[:2])}"
    )


def _condense_bear(bear: BearAnalysis) -> str:
    return (
        f"Confidence: {bear.confidence}/10 | Worst case: ${bear.worst_case_target:,.0f} ({bear.worst_case_timeline})\n"
        f"Threats: {'; '.join(bear.competition_threats[:3])}\n"
        f"Valuation: {bear.valuation_concerns[:200]}"
    )


def _condense_strategist(strat: StrategistAnalysis) -> str:
    return (
        f"Risk: {strat.concentration_risk} | Allocation: ${strat.recommended_allocation:,.0f}\n"
        f"Reasoning: {strat.reasoning[:250]}"
    )


def run_judge_agent(
    ticker: str,
    bull: BullAnalysis,
    bear: BearAnalysis,
    strategist: StrategistAnalysis,
    market_data: dict,
    rag_context: str = "",
) -> JudgeRecommendation:
    # Use condensed summaries for local models to keep the prompt manageable
    if config.PROVIDER == Provider.OLLAMA:
        bull_txt = _condense_bull(bull)
        bear_txt = _condense_bear(bear)
        strat_txt = _condense_strategist(strategist)
    else:
        bull_txt = bull.model_dump_json(indent=2)
        bear_txt = bear.model_dump_json(indent=2)
        strat_txt = strategist.model_dump_json(indent=2)

    prompt = _JUDGE_BODY.format(
        ticker=ticker,
        market_context=format_market_context(market_data),
        bull_analysis=bull_txt,
        bear_analysis=bear_txt,
        strategist_analysis=strat_txt,
        schema_hint=_schema_hint(_JUDGE_SKELETON),
    )
    return _invoke(get_judge_llm(), JudgeRecommendation, prompt)


# Backwards-compat aliases used in tests / workflow
BULL_SYSTEM = _BULL_BODY
BEAR_SYSTEM = _BEAR_BODY
STRATEGIST_SYSTEM = _STRATEGIST_BODY
JUDGE_SYSTEM = _JUDGE_BODY
