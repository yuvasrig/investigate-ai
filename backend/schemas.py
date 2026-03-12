import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, Literal


def _coerce_money_like_number(value):
    """Best-effort parse for LLM outputs like '0.95 * $40,000 = $38,000'."""
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return value
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


# ══════════════════════════════════════════════════════════════════════════════
# Verified Claim & Agent output schemas
# ══════════════════════════════════════════════════════════════════════════════

class VerifiedClaim(BaseModel):
    claim: str = Field(description="The analytical claim or data point")
    is_speculative: bool = Field(description="True if the claim lacks concrete verification from 10-K or grounding data")

class BullAnalysis(BaseModel):
    competitive_advantages: list[VerifiedClaim] = Field(description="Key competitive moats and advantages")
    growth_catalysts: list[VerifiedClaim] = Field(description="Key drivers of future growth")
    valuation_justification: str = Field(description="Why the current valuation is justified")
    best_case_target: float = Field(description="Best case price target in USD")
    best_case_timeline: str = Field(description="Timeline for best case (e.g. '3 years')")
    confidence: int = Field(ge=0, le=10, description="Confidence score 0-10")
    pe_ratio: Optional[float] = Field(default=None, description="Estimated P/E ratio")


class BearAnalysis(BaseModel):
    competition_threats: list[VerifiedClaim] = Field(description="Key competitive threats and risks")
    valuation_concerns: str = Field(description="Summary of valuation concerns")
    cyclical_risks: list[VerifiedClaim] = Field(description="Cyclical, macro, and regulatory risks")
    worst_case_target: float = Field(description="Worst case price target in USD")
    worst_case_timeline: str = Field(description="Timeline for worst case scenario")
    confidence: int = Field(ge=0, le=10, description="Confidence score 0-10")
    pe_ratio: Optional[float] = Field(default=None, description="Estimated P/E ratio")


class StrategistAnalysis(BaseModel):
    current_exposure: str = Field(description="Description of current indirect exposure")
    concentration_risk: Literal["LOW", "MODERATE", "HIGH", "VERY HIGH"] = Field(
        description="Risk level: LOW, MODERATE, HIGH, or VERY HIGH"
    )
    concentration_explanation: str = Field(description="Explanation of concentration risk")
    recommended_allocation: float = Field(ge=0, description="Recommended dollar allocation")
    reasoning: str = Field(description="Reasoning behind the recommendation")
    alternative_options: list[str] = Field(description="Alternative investment options as plain strings")

    @field_validator("recommended_allocation", mode="before")
    @classmethod
    def parse_recommended_allocation(cls, value):
        return _coerce_money_like_number(value)

    @field_validator("alternative_options", mode="before")
    @classmethod
    def coerce_alternative_options(cls, value):
        """Coerce each element to a string.

        Ollama sometimes returns list[dict] like {"ticker": "VWO", "amount": "$20"}
        instead of list[str]. Convert any non-string element to a readable string.
        """
        if not isinstance(value, list):
            return [str(value)] if value is not None else []
        result = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # e.g. {"ticker": "VWO", "name": "...", "amount": "$20"}
                ticker = item.get("ticker") or item.get("symbol") or ""
                name = item.get("name") or item.get("description") or ""
                amount = item.get("amount") or item.get("allocation") or ""
                reasoning = item.get("reasoning") or item.get("reason") or ""
                parts = [p for p in [ticker, name, amount, reasoning] if p]
                result.append(" — ".join(parts) if parts else str(item))
            else:
                result.append(str(item))
        return result


class ConfidenceBreakdown(BaseModel):
    growth_potential: int = Field(ge=0, le=100)
    risk_level: int = Field(ge=0, le=100)
    portfolio_fit: int = Field(ge=0, le=100)
    timing: int = Field(ge=0, le=100)
    execution_clarity: int = Field(ge=0, le=100)


# ── Evidence-Based Scoring ─────────────────────────────────────────────────────

class AgentEvidenceScore(BaseModel):
    """Evidence quality scores for a single analyst (0-10 each, max 40 total)."""
    data_citations: int = Field(ge=0, le=10, description="Data Citations quality (0-10): specificity and sourcing of data points")
    calculation_rigor: int = Field(ge=0, le=10, description="Calculation Rigor (0-10): shows valuation methodology and work")
    historical_precedent: int = Field(ge=0, le=10, description="Historical Precedent (0-10): specific comparables with dates and numbers")
    counterargument: int = Field(ge=0, le=10, description="Counterargument Strength (0-10): acknowledges and addresses opposing views")
    total: int = Field(ge=0, le=40, description="Sum of all four dimension scores (max 40)")


class EvidenceAssessment(BaseModel):
    """Evidence quality evaluation of all three analysts with weighted decision scoring."""
    bull: AgentEvidenceScore = Field(description="Bull analyst evidence quality breakdown")
    bear: AgentEvidenceScore = Field(description="Bear analyst evidence quality breakdown")
    strategist: AgentEvidenceScore = Field(description="Portfolio Strategist evidence quality breakdown")
    bull_weighted: float = Field(description="Bull conviction × (bull_evidence / 40)")
    bear_weighted: float = Field(description="Bear conviction × (bear_evidence / 40)")
    strategist_weighted: float = Field(description="Strategist conviction × (strategist_evidence / 40)")
    winner: str = Field(description="Agent with highest weighted score: 'bull', 'bear', or 'strategist'")
    winner_reasoning: str = Field(description="Brief explanation of why the winner's evidence-weighted case is strongest")


class EvaluatedScenario(BaseModel):
    scenario_name: str = Field(description="Name of the scenario evaluated (from Intent Router)")
    verified_analog_used: str = Field(description="Historical event or comparable used from RAG to justify the scenario outcome")

class JudgeRecommendation(BaseModel):
    action: str = Field(description="Investment action: buy, hold, or sell")
    recommended_amount: float = Field(ge=0, description="Recommended dollar amount")
    reasoning: str = Field(description="Comprehensive reasoning")
    confidence_overall: int = Field(ge=0, le=100, description="Overall confidence 0-100")
    confidence_breakdown: ConfidenceBreakdown = Field(description="5-dimensional confidence breakdown")
    entry_strategy: str = Field(description="How to enter the position")
    risk_management: str = Field(description="Risk management guidance")
    traffic_light_color: Literal["red", "yellow", "green"] = Field(description="Red if any stress scenario correlates with >2sigma drawdown, else based on overall consensus")
    evaluated_scenarios: list[EvaluatedScenario] = Field(default_factory=list, description="List of scenarios that the Judge evaluated")
    key_factors: list[str] = Field(description="Key decision factors")
    evidence_assessment: Optional[EvidenceAssessment] = Field(
        default=None,
        description="Evidence quality scoring for all three analysts with evidence-weighted decision"
    )

    @field_validator("recommended_amount", mode="before")
    @classmethod
    def parse_recommended_amount(cls, value):
        return _coerce_money_like_number(value)


# ══════════════════════════════════════════════════════════════════════════════
# Intent Router & Multi-Tier Schemas
# ══════════════════════════════════════════════════════════════════════════════

class IntentRouterResult(BaseModel):
    target_asset: Optional[str] = Field(description="The primary ticker or asset in question, if any")
    scenarios: list[str] = Field(description="Array of RAG macro fear scenarios mapped from the intent (e.g. ['Geopolitical Escalation: Pacific Rim'])")
    requires_deep_dive: bool = Field(description="True if the user intent requires the 4-agent deep dive, false if it's just general info")



# ══════════════════════════════════════════════════════════════════════════════
# Portfolio / request schemas & Tier 1 Scan
# ══════════════════════════════════════════════════════════════════════════════

class PositionType(BaseModel):
    ticker: str = Field(description="The asset ticker")
    category: Literal["Long-Term Core", "Growth Position", "Speculative", "Income", "Cash"] = Field(description="Classification of the holding")
    weight_pct: float = Field(description="Percentage weight in portfolio")
    is_flagged: bool = Field(default=False, description="True if position poses concentration risk")

class Tier1ScanResult(BaseModel):
    overall_risk_score: int = Field(ge=0, le=10, description="0-10 risk score (10 = highest risk)")
    missing_protections: list[str] = Field(description="Missing diversifiers (e.g. '0% bonds', 'No international exposure')")
    positions: list[PositionType] = Field(description="Categorized portfolio holdings")
    concentration_warning: Optional[str] = Field(default=None, description="Warning if any single asset or sector is too concentrated")


class PortfolioHolding(BaseModel):
    ticker: str = Field(description="ETF or stock ticker (e.g. SPY, QQQ)")
    value: float = Field(description="Current market value in USD")
    name: Optional[str] = None
    shares: Optional[float] = None
    cost_basis: Optional[float] = Field(default=None, description="Total purchase cost (for tax harvesting)")
    holding_period_days: Optional[int] = Field(default=None, description="Days held (determines ST vs LT tax rate)")


class AnalysisRequest(BaseModel):
    ticker: str = Field(description="Stock ticker symbol (e.g. NVDA)")
    amount: float = Field(description="Investment amount in USD")
    portfolio: dict = Field(description="Portfolio info with total_value key")
    risk_tolerance: str = Field(description="Risk tolerance: conservative, moderate, aggressive")
    time_horizon: str = Field(description="Investment time horizon (e.g. '1Y', '3Y', '5Y')")
    user_query: Optional[str] = Field(
        default=None,
        description="Optional natural-language query used by the Tier 2 intent router",
    )
    analysis_action: Literal["buy", "sell", "hold"] = Field(
        default="buy",
        description="Action to debate: buy (buy more), sell (exit position), hold (maintain position)"
    )
    portfolio_holdings: Optional[list[PortfolioHolding]] = Field(
        default=None,
        description="Individual ETF/stock holdings for hidden-exposure and Kelly analysis"
    )


class TrafficLightResult(BaseModel):
    """Consensus signal derived from Bull vs Bear conviction."""
    color: Literal["green", "yellow", "red"]
    message: str
    conviction_diff: float = Field(description="Absolute diff between bull/bear conviction (0-100)")
    key_conflict: dict = Field(description="Main point of disagreement")
    bull_recommendation: str
    bear_recommendation: str
    bull_conviction: float
    bear_conviction: float


class KellySizingResult(BaseModel):
    """Mathematical Kelly Criterion position sizing result."""
    kelly_fraction: float = Field(description="Raw f* (0-1)")
    raw_kelly_amount: float = Field(description="f* × portfolio_value")
    correlation_adjusted_amount: float = Field(description="Reduced by portfolio correlation")
    final_amount: float = Field(description="Final recommended amount")
    sizing_rationale: str = Field(description="Human-readable explanation")
    scale_factor: float = Field(description="0-1 multiplier vs proposed amount")


class AnalysisResponse(BaseModel):
    analysis_id: str
    llm_provider: str
    ticker: str
    bull_analysis: BullAnalysis
    bear_analysis: BearAnalysis
    strategist_analysis: StrategistAnalysis
    final_recommendation: JudgeRecommendation
    intent: Optional[IntentRouterResult] = None
    market_data: Optional[dict] = None
    rag_summary: Optional[dict] = None
    traffic_light: Optional[TrafficLightResult] = None
    portfolio_exposure: Optional[dict] = None
    kelly_sizing: Optional[KellySizingResult] = None   # NEW
    execution_time: float
    timestamp: str


# ══════════════════════════════════════════════════════════════════════════════
# Auth schemas
# ══════════════════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: str = Field(description="User email address")
    password: str = Field(min_length=8, description="Password (min 8 characters)")
    name: Optional[str] = Field(default="", description="Display name")


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ══════════════════════════════════════════════════════════════════════════════
# Watchlist & Alert schemas
# ══════════════════════════════════════════════════════════════════════════════

class WatchlistCreate(BaseModel):
    name: str = Field(default="My Watchlist", description="Watchlist name")
    tickers: list[str] = Field(default=[], description="List of tickers to watch")
    notes: Optional[str] = None


class WatchlistResponse(BaseModel):
    id: str
    user_id: str
    name: str
    tickers: list[str]
    notes: Optional[str]
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertCreate(BaseModel):
    ticker: str
    alert_type: Literal["price_above", "price_below", "risk_change"]
    threshold: Optional[float] = None
    message: Optional[str] = None


class AlertResponse(BaseModel):
    id: str
    user_id: str
    ticker: str
    alert_type: str
    threshold: Optional[float]
    message: Optional[str]
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════════
# Tax harvesting schemas
# ══════════════════════════════════════════════════════════════════════════════

class TaxHarvestRequest(BaseModel):
    holdings: list[PortfolioHolding] = Field(description="Holdings with cost_basis for analysis")
    tax_year: Optional[int] = Field(default=None, description="Tax year (defaults to current year)")


# ══════════════════════════════════════════════════════════════════════════════
# Plaid schemas
# ══════════════════════════════════════════════════════════════════════════════

class PlaidExchangeRequest(BaseModel):
    public_token: str = Field(description="Short-lived public token from Plaid Link onSuccess")


class PlaidUserIdRequest(BaseModel):
    user_id: str = Field(default="anonymous", description="Your internal user ID")
