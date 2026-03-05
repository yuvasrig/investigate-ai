from pydantic import BaseModel, Field
from typing import Optional


class BullAnalysis(BaseModel):
    competitive_advantages: list[str] = Field(
        description="Key competitive moats and advantages"
    )
    growth_catalysts: list[str] = Field(
        description="Key drivers of future growth"
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
    concentration_risk: str = Field(
        description="Risk level: LOW, MODERATE, or HIGH"
    )
    concentration_explanation: str = Field(
        description="Explanation of the concentration risk assessment"
    )
    recommended_allocation: float = Field(
        description="Recommended dollar allocation"
    )
    reasoning: str = Field(
        description="Reasoning behind the recommended allocation"
    )
    alternative_options: list[str] = Field(
        description="Alternative investment options to consider"
    )


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
        description="Recommended dollar amount to invest"
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


class AnalysisResponse(BaseModel):
    ticker: str
    bull_analysis: BullAnalysis
    bear_analysis: BearAnalysis
    strategist_analysis: StrategistAnalysis
    final_recommendation: JudgeRecommendation
    market_data: Optional[dict] = None
    rag_summary: Optional[dict] = None   # {"sec": N, "news": M, "cache_hit": bool}
    execution_time: float
    timestamp: str
