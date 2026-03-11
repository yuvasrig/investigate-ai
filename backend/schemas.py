import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


def _coerce_money_like_number(value):
    """Best-effort parse for LLM outputs like '0.95 * $40,000 = $38,000'."""
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return value

        # Prefer the value after "=" when the model shows work.
        search_zone = raw.split("=")[-1] if "=" in raw else raw
        matches = re.findall(r"[-+]?\$?\s*\d[\d,]*(?:\.\d+)?", search_zone)
        if not matches:
            matches = re.findall(r"[-+]?\$?\s*\d[\d,]*(?:\.\d+)?", raw)

        if matches:
            token = matches[-1].replace("$", "").replace(",", "").strip()
            try:
                return float(token)
            except ValueError:
                return value

    return value


class BullAnalysis(BaseModel):
    competitive_advantages: list[str] = Field(
        description="Key competitive moats and advantages"
    )
    growth_catalysts: list[str] = Field(
        description="Key drivers of future growth"
    )
    valuation_justification: str = Field(
        description="Why the current valuation is justified by growth (PEG, margins, FCF)"
    )
    best_case_target: float = Field(
        description="Best case price target in USD"
    )
    best_case_timeline: str = Field(
        description="Timeline for best case scenario (e.g. '3 years')"
    )
    confidence: int = Field(
        ge=0, le=10, description="Confidence score 0-10"
    )
    pe_ratio: Optional[float] = Field(
        default=None, description="Estimated or known P/E ratio"
    )


class BearAnalysis(BaseModel):
    competition_threats: list[str] = Field(
        description="Key competitive threats and risks"
    )
    valuation_concerns: str = Field(
        description="Summary of valuation concerns"
    )
    cyclical_risks: list[str] = Field(
        description="Cyclical, macro, and regulatory risks"
    )
    worst_case_target: float = Field(
        description="Worst case price target in USD"
    )
    worst_case_timeline: str = Field(
        description="Timeline for worst case scenario"
    )
    confidence: int = Field(
        ge=0, le=10, description="Confidence score 0-10"
    )
    pe_ratio: Optional[float] = Field(
        default=None, description="Estimated or known P/E ratio"
    )


class StrategistAnalysis(BaseModel):
    current_exposure: str = Field(
        description="Description of current indirect exposure (e.g. '7% via S&P 500')"
    )
    concentration_risk: Literal["LOW", "MODERATE", "HIGH", "VERY HIGH"] = Field(
        description="Risk level: LOW, MODERATE, HIGH, or VERY HIGH"
    )
    concentration_explanation: str = Field(
        description="Explanation of the concentration risk assessment"
    )
    recommended_allocation: float = Field(
        ge=0, description="Recommended dollar allocation"
    )
    reasoning: str = Field(
        description="Reasoning behind the recommended allocation"
    )
    alternative_options: list[str] = Field(
        description="Alternative investment options to consider"
    )

    @field_validator("recommended_allocation", mode="before")
    @classmethod
    def parse_recommended_allocation(cls, value):
        return _coerce_money_like_number(value)


class ConfidenceBreakdown(BaseModel):
    growth_potential: int = Field(ge=0, le=100)
    risk_level: int = Field(ge=0, le=100)
    portfolio_fit: int = Field(ge=0, le=100)
    timing: int = Field(ge=0, le=100)
    execution_clarity: int = Field(ge=0, le=100)


class JudgeRecommendation(BaseModel):
    action: str = Field(
        description="Investment action: buy, hold, or sell"
    )
    recommended_amount: float = Field(
        ge=0, description="Recommended dollar amount to invest"
    )
    reasoning: str = Field(
        description="Comprehensive reasoning for the recommendation"
    )
    confidence_overall: int = Field(
        ge=0, le=100, description="Overall confidence score 0-100"
    )
    confidence_breakdown: ConfidenceBreakdown = Field(
        description="5-dimensional confidence breakdown"
    )
    entry_strategy: str = Field(
        description="How to enter the position (e.g. 'DCA over 3 months')"
    )
    risk_management: str = Field(
        description="Risk management guidance (e.g. 'stop-loss at $350')"
    )
    key_factors: list[str] = Field(
        description="Key decision factors that drove the recommendation"
    )

    @field_validator("recommended_amount", mode="before")
    @classmethod
    def parse_recommended_amount(cls, value):
        return _coerce_money_like_number(value)


class PortfolioHolding(BaseModel):
    ticker: str = Field(description="ETF or stock ticker (e.g. SPY, QQQ)")
    value: float = Field(description="Current market value in USD")
    name: Optional[str] = None
    shares: Optional[float] = None


class AnalysisRequest(BaseModel):
    ticker: str = Field(description="Stock ticker symbol (e.g. NVDA)")
    amount: float = Field(description="Investment amount in USD")
    portfolio: dict = Field(description="Portfolio info with total_value key")
    risk_tolerance: str = Field(
        description="Risk tolerance: conservative, moderate, aggressive"
    )
    time_horizon: str = Field(
        description="Investment time horizon (e.g. '1Y', '3Y', '5Y', '10Y')"
    )
    # Optional: detailed holdings for hidden-exposure calculation
    portfolio_holdings: Optional[list[PortfolioHolding]] = Field(
        default=None,
        description="Individual ETF/stock holdings for hidden-exposure analysis"
    )


class TrafficLightResult(BaseModel):
    """Consensus signal derived from Bull vs Bear conviction."""
    color: Literal["green", "yellow", "red"]
    message: str
    conviction_diff: float = Field(description="Absolute diff between bull/bear conviction (0-100)")
    key_conflict: dict = Field(description="Main point of disagreement between agents")
    bull_recommendation: str   # Always "BUY"
    bear_recommendation: str   # Always "SELL"
    bull_conviction: float     # 0-100
    bear_conviction: float     # 0-100


class AnalysisResponse(BaseModel):
    analysis_id: str
    llm_provider: str
    ticker: str
    bull_analysis: BullAnalysis
    bear_analysis: BearAnalysis
    strategist_analysis: StrategistAnalysis
    final_recommendation: JudgeRecommendation
    market_data: Optional[dict] = None
    rag_summary: Optional[dict] = None   # {"sec": N, "news": M, "cache_hit": bool}
    traffic_light: Optional[TrafficLightResult] = None
    portfolio_exposure: Optional[dict] = None
    execution_time: float
    timestamp: str
