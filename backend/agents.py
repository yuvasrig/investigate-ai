"""
Four investment agents — grounded with live market data AND RAG document context.

Every agent receives two injected blocks before being asked to reason:
  1. GROUNDING — live yfinance snapshot (price, PE, margins, consensus, news headlines)
  2. RAG       — relevant excerpts from SEC 10-K/10-Q filings and full news articles

This combination ensures:
  - Numbers are anchored to real current data (grounding)
  - Reasoning is backed by actual disclosed risks and management commentary (RAG)
"""

from schemas import BullAnalysis, BearAnalysis, StrategistAnalysis, JudgeRecommendation
from llm_factory import get_analyst_llm, get_judge_llm
from tools import format_market_context

# Shown in the prompt when no RAG documents were retrieved
_NO_RAG = "[No additional documents available — rely on the market data above.]"


# ── Bull Analyst ─────────────────────────────────────────────────────────────

BULL_SYSTEM = """You are a BULL ANALYST for {ticker}.

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

Cite actual numbers. Reference SEC section or news source when you use document content.
Output only valid JSON matching the BullAnalysis schema."""


def run_bull_agent(ticker: str, market_data: dict, rag_context: str = "") -> BullAnalysis:
    llm = get_analyst_llm().with_structured_output(BullAnalysis)
    return llm.invoke(BULL_SYSTEM.format(
        ticker=ticker,
        market_context=format_market_context(market_data),
        rag_context=rag_context or _NO_RAG,
    ))


# ── Bear Analyst ─────────────────────────────────────────────────────────────

BEAR_SYSTEM = """You are a BEAR ANALYST for {ticker}.

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

Be skeptical. Stress-test every bullish assumption. Use the disclosed risk factors from the
SEC filings as your primary ammunition — they are legally binding disclosures.
Output only valid JSON matching the BearAnalysis schema."""


def run_bear_agent(ticker: str, market_data: dict, rag_context: str = "") -> BearAnalysis:
    llm = get_analyst_llm().with_structured_output(BearAnalysis)
    return llm.invoke(BEAR_SYSTEM.format(
        ticker=ticker,
        market_context=format_market_context(market_data),
        rag_context=rag_context or _NO_RAG,
    ))


# ── Portfolio Strategist ──────────────────────────────────────────────────────

STRATEGIST_SYSTEM = """You are a PORTFOLIO STRATEGIST evaluating a position in {ticker}.

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

1. Current indirect exposure — estimate via S&P 500 / Nasdaq index fund holdings
   (use the sector and market cap from the data above to calibrate)
2. Concentration risk (LOW / MODERATE / HIGH):
   - HIGH beta (>1.5) or high short interest (>10%) = tighter sizing
   - Analyst mean target below current price = flag explicitly
   - Customer concentration in SEC filings = raise risk rating
3. Recommended allocation — may differ from the proposed amount if risk warrants it.
   Provide the exact dollar figure and the reasoning behind any reduction.
4. Alternative options that could provide similar exposure with less concentration risk

Output only valid JSON matching the StrategistAnalysis schema."""


def run_strategist_agent(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    market_data: dict,
    rag_context: str = "",
) -> StrategistAnalysis:
    llm = get_analyst_llm().with_structured_output(StrategistAnalysis)
    proposed_pct = (amount / portfolio_value * 100) if portfolio_value > 0 else 0
    return llm.invoke(STRATEGIST_SYSTEM.format(
        ticker=ticker,
        amount=amount,
        portfolio_value=portfolio_value,
        proposed_pct=proposed_pct,
        risk_tolerance=risk_tolerance,
        market_context=format_market_context(market_data),
        rag_context=rag_context or _NO_RAG,
    ))


# ── Judge Agent ───────────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are the INVESTMENT JUDGE for {ticker}.

All three analysts worked from the same live market data and document excerpts shown below.
Use them as the authoritative ground truth when settling factual disputes between analysts.

━━━ SOURCE 1 — LIVE MARKET DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{market_context}

━━━ SOURCE 2 — SEC FILINGS & NEWS (RAG) ━━━━━━━━━━━━━━━━━━━━
{rag_context}

━━━ BULL ANALYST REPORT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bull_analysis}

━━━ BEAR ANALYST REPORT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bear_analysis}

━━━ PORTFOLIO STRATEGIST REPORT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{strategist_analysis}

Your synthesis:
1. Identify where bull and bear agree vs conflict — use the real data to arbitrate
2. Weight analyst perspectives by their confidence scores
3. Accept the strategist's concentration risk rating and recommended_allocation as a hard cap
4. Set recommended_amount ≤ strategist's recommended_allocation
5. Anchor price targets to the REAL current price in the market data
6. Provide concrete entry_strategy (e.g. "DCA $X/month for 3 months") and
   risk_management (e.g. "stop-loss at $Y, -Z% from current price")
7. 5-dimensional confidence breakdown (0-100 each):
   - growth_potential: strength of bull case given real financials
   - risk_level: severity of bear risks vs current valuation
   - portfolio_fit: match to user's risk profile and portfolio size
   - timing: is NOW a good entry given price vs analyst consensus targets?
   - execution_clarity: how well-defined is the entry/exit plan?

Be decisive. Every number you cite must come from the data or analyst reports above.
Output only valid JSON matching the JudgeRecommendation schema."""


def run_judge_agent(
    ticker: str,
    bull: BullAnalysis,
    bear: BearAnalysis,
    strategist: StrategistAnalysis,
    market_data: dict,
    rag_context: str = "",
) -> JudgeRecommendation:
    llm = get_judge_llm().with_structured_output(JudgeRecommendation)
    return llm.invoke(JUDGE_SYSTEM.format(
        ticker=ticker,
        market_context=format_market_context(market_data),
        rag_context=rag_context or _NO_RAG,
        bull_analysis=bull.model_dump_json(indent=2),
        bear_analysis=bear.model_dump_json(indent=2),
        strategist_analysis=strategist.model_dump_json(indent=2),
    ))
