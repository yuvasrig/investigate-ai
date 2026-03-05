"""
Four investment agents — all grounded with live market data.

Every agent receives a formatted market-data block BEFORE being asked to reason,
so price targets, PE ratios, and financials are anchored to real numbers rather
than the model's (potentially stale) training data.
"""

from schemas import BullAnalysis, BearAnalysis, StrategistAnalysis, JudgeRecommendation
from llm_factory import get_analyst_llm, get_judge_llm
from tools import format_market_context


# ── Bull Analyst ─────────────────────────────────────────────────────────────

BULL_SYSTEM = """You are a BULL ANALYST for {ticker}.

You have been given VERIFIED LIVE market data below. You MUST:
- Use the exact current price shown as your baseline
- Base your best-case price target on the real current price (e.g. "+80% in 3 years")
- Reference actual revenue figures, margins, and growth rates from the data
- Do NOT invent or hallucinate numbers — every metric you cite must come from the data below or be clearly labeled as your reasoned estimate

{market_context}

Given this real data, construct the STRONGEST possible bull case for investing in {ticker} now.

Focus on:
1. Competitive advantages that the data supports (high margins, revenue growth, market position)
2. Growth catalysts visible in the financials (revenue acceleration, margin expansion, FCF growth)
3. Valuation justification — is the current P/E warranted by growth rate? Use the PEG ratio
4. A specific best-case price target derived from the current price above and a realistic timeline

Be precise. Reference actual numbers from the data. Output only valid JSON matching the BullAnalysis schema."""


def run_bull_agent(ticker: str, market_data: dict) -> BullAnalysis:
    llm = get_analyst_llm().with_structured_output(BullAnalysis)
    market_context = format_market_context(market_data)
    return llm.invoke(BULL_SYSTEM.format(ticker=ticker, market_context=market_context))


# ── Bear Analyst ─────────────────────────────────────────────────────────────

BEAR_SYSTEM = """You are a BEAR ANALYST for {ticker}.

You have been given VERIFIED LIVE market data below. You MUST:
- Use the exact current price shown as your baseline
- Base your worst-case price target on the real current price (e.g. "-60% over 2 years")
- Reference actual valuation multiples, debt levels, and margin trends from the data
- Do NOT invent or hallucinate numbers — every metric you cite must come from the data below or be clearly labeled as your reasoned estimate

{market_context}

Given this real data, construct the STRONGEST possible bear case AGAINST investing in {ticker} now.

Focus on:
1. Valuation risks — how does the current P/E compare to growth rate? Is the PEG ratio justified?
2. Competition threats — what do the margins or slowing growth reveal about competitive pressure?
3. Financial risks — debt levels, FCF sustainability, short interest signals
4. A specific worst-case price target derived from the current price above and a realistic timeline

Be skeptical. Stress-test every bullish assumption. Reference actual numbers from the data.
Output only valid JSON matching the BearAnalysis schema."""


def run_bear_agent(ticker: str, market_data: dict) -> BearAnalysis:
    llm = get_analyst_llm().with_structured_output(BearAnalysis)
    market_context = format_market_context(market_data)
    return llm.invoke(BEAR_SYSTEM.format(ticker=ticker, market_context=market_context))


# ── Portfolio Strategist ──────────────────────────────────────────────────────

STRATEGIST_SYSTEM = """You are a PORTFOLIO STRATEGIST evaluating a position in {ticker}.

You have been given VERIFIED LIVE market data below. You MUST:
- Use the real current price to calculate exact share counts
- Use the real market cap and beta to assess volatility-adjusted position sizing
- Reference analyst consensus targets when setting realistic allocation bounds
- Do NOT invent or hallucinate numbers

{market_context}

User portfolio context:
- Proposed investment amount: ${amount:,.0f}
- Total portfolio value:      ${portfolio_value:,.0f}
- Proposed allocation pct:   {proposed_pct:.1f}% of portfolio
- Risk tolerance:             {risk_tolerance}

Position sizing guidelines:
- Single stock should not exceed 5-10% of portfolio for moderate risk
- High-beta stocks (beta > 1.5) warrant tighter sizing
- High short interest (> 10%) signals elevated volatility risk
- Factor in analyst consensus — if mean target < current price, flag this

Calculate:
1. Current indirect exposure via broad index funds (S&P 500 / Nasdaq ETFs)
2. Concentration risk rating (LOW / MODERATE / HIGH) with explanation
3. Recommended allocation — may differ from the user's proposed amount if risk warrants it
4. Entry strategy advice given current valuation vs analyst targets

Output only valid JSON matching the StrategistAnalysis schema."""


def run_strategist_agent(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    market_data: dict,
) -> StrategistAnalysis:
    llm = get_analyst_llm().with_structured_output(StrategistAnalysis)
    proposed_pct = (amount / portfolio_value * 100) if portfolio_value > 0 else 0
    market_context = format_market_context(market_data)
    prompt = STRATEGIST_SYSTEM.format(
        ticker=ticker,
        amount=amount,
        portfolio_value=portfolio_value,
        proposed_pct=proposed_pct,
        risk_tolerance=risk_tolerance,
        market_context=market_context,
    )
    return llm.invoke(prompt)


# ── Judge Agent ───────────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are the INVESTMENT JUDGE for {ticker}.

All three analysts worked from the same verified live market data shown below.
Use it as the authoritative source of truth when settling factual disputes.

{market_context}

BULL ANALYST REPORT:
{bull_analysis}

BEAR ANALYST REPORT:
{bear_analysis}

PORTFOLIO STRATEGIST REPORT:
{strategist_analysis}

Your task:
1. Identify where the bull and bear cases agree vs conflict — weight by confidence scores
2. Anchor your recommendation to the REAL current price in the market data above
3. Accept the strategist's concentration risk assessment and recommended allocation
4. Set a final recommended_amount that respects portfolio sizing constraints
5. Give concrete entry_strategy and risk_management figures (e.g. "DCA at $X/month", "stop-loss at $Y")
6. Provide a 5-dimensional confidence breakdown (0-100 each):
   - growth_potential: strength of the bull case given real financials
   - risk_level: severity of bear risks relative to current valuation
   - portfolio_fit: how well this fits the user's risk profile and portfolio size
   - timing: is NOW a good entry point given price vs analyst targets?
   - execution_clarity: how clearly defined is the entry/exit plan?

Be decisive. Cite specific numbers. The user needs an actionable decision.
Output only valid JSON matching the JudgeRecommendation schema."""


def run_judge_agent(
    ticker: str,
    bull: BullAnalysis,
    bear: BearAnalysis,
    strategist: StrategistAnalysis,
    market_data: dict,
) -> JudgeRecommendation:
    llm = get_judge_llm().with_structured_output(JudgeRecommendation)
    market_context = format_market_context(market_data)
    prompt = JUDGE_SYSTEM.format(
        ticker=ticker,
        market_context=market_context,
        bull_analysis=bull.model_dump_json(indent=2),
        bear_analysis=bear.model_dump_json(indent=2),
        strategist_analysis=strategist.model_dump_json(indent=2),
    )
    return llm.invoke(prompt)
