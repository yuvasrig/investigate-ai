"""
LangGraph workflow for InvestiGate.

Graph (in order):

  fetch_data           ← yfinance: live price, financials, analyst consensus, news URLs
       ↓
  rag_ingest           ← fetch SEC 10-K/10-Q + full news articles, embed into ChromaDB
       ↓                  (cache-aware: skips if fresh data already indexed)
  parallel_analysis    ← Bull, Bear, Strategist run concurrently
       ↓                  each receives BOTH grounding data AND per-role RAG context
  verify_facts         ← CONDITIONAL: re-fetches Yahoo Finance P/E if bull/bear disagree >10
       ↓
  judge                ← synthesises all three reports + same data sources
       ↓
  END

Both grounding (structured live data) and RAG (document retrieval) run before
any LLM call, so every agent reasons from the same verified foundation.
"""

import concurrent.futures
import time
from typing import TypedDict, Optional, Any, Callable, TypeVar

from langgraph.graph import StateGraph, END

from schemas import BullAnalysis, BearAnalysis, StrategistAnalysis, JudgeRecommendation, IntentRouterResult
from agents import run_bull_agent, run_bear_agent, run_strategist_agent, run_judge_agent
from agents.intent_router import route_intent
from tools import fetch_full_market_data
from rag.retriever import ingest_ticker, retrieve_all_agents
from sec_fetcher import get_latest_10k, get_sec_grounding_context

T = TypeVar("T")


# ── State ─────────────────────────────────────────────────────────────────────

class InvestmentState(TypedDict):
    # Inputs
    ticker: str
    amount: float
    portfolio_value: float
    risk_tolerance: str
    time_horizon: str
    analysis_action: str  # "buy" | "sell" | "hold"
    user_query: Optional[str] # Triggering narrative

    # Intent routing
    intent: Optional[IntentRouterResult]

    # Live market snapshot (populated by fetch_data node)
    market_data: Optional[dict]

    # Per-agent RAG context strings (populated by rag_ingest node)
    rag_context: Optional[dict[str, str]]   # {"bull": str, "bear": str, ...}
    rag_summary: Optional[dict]              # {"sec": N, "news": M, "cache_hit": bool}

    # SEC 10-K filing metadata (populated by rag_ingest node)
    sec_filing: Optional[dict]              # {filing_url, viewer_url, filing_date, section_urls}

    # Agent outputs
    bull_analysis: Optional[BullAnalysis]
    bear_analysis: Optional[BearAnalysis]
    strategist_analysis: Optional[StrategistAnalysis]
    final_recommendation: Optional[JudgeRecommendation]

    # Gated grounding flag
    grounding_triggered: Optional[bool]


# ── Node 1 — Live market data ─────────────────────────────────────────────────

def fetch_data_node(state: InvestmentState) -> dict[str, Any]:
    """Pull ~35 real-time fields from yfinance before any agent runs."""
    market_data = fetch_full_market_data(state["ticker"])
    return {"market_data": market_data}


# ── Node 1.5 — Intent Routing (Tier 2) ────────────────────────────────────────

def intent_router_node(state: InvestmentState) -> dict[str, Any]:
    """Parse free-text query into structured scenarios if provided."""
    query = state.get("user_query")
    if not query:
        return {"intent": IntentRouterResult(target_asset=state["ticker"], scenarios=[], requires_deep_dive=True)}
    intent = route_intent(query)
    return {"intent": intent}


# ── Node 2 — RAG ingestion & retrieval ───────────────────────────────────────

def rag_node(state: InvestmentState) -> dict[str, Any]:
    """
    Two steps:
      a) Ingest — fetch SEC 10-K/10-Q + news articles, embed into ChromaDB.
                  Skips automatically if fresh documents are already indexed.
      b) Retrieve — run four parallel semantic searches (one per agent role)
                    and return formatted context strings.
    """
    ticker = state["ticker"]
    market_data = state["market_data"] or {}

    rag_summary = ingest_ticker(ticker, market_data)
    rag_context = retrieve_all_agents(ticker)

    # SEC 10-K grounding — fetch in parallel with RAG (non-blocking; None if unavailable)
    sec_filing = get_latest_10k(ticker)
    sec_context = get_sec_grounding_context(ticker)

    # Prepend SEC grounding to every agent's RAG context block
    if sec_context:
        rag_context = {
            role: sec_context + "\n\n" + ctx
            for role, ctx in rag_context.items()
        }

    return {"rag_context": rag_context, "rag_summary": rag_summary, "sec_filing": sec_filing}


# ── Node 3 — Parallel agent analysis ─────────────────────────────────────────

_ANALYST_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 1.0
_JUDGE_MAX_RETRIES = 2


def _ensure_model_output(name: str, result: Any, expected_type: type[T]) -> T:
    """Normalize and validate structured outputs from model/tool calls."""
    if result is None:
        raise ValueError(f"{name} returned empty output")
    if isinstance(result, expected_type):
        return result
    try:
        return expected_type.model_validate(result)
    except Exception as exc:
        raise ValueError(
            f"{name} returned invalid output type={type(result).__name__}"
        ) from exc


def _run_with_retry(
    name: str,
    expected_type: type[T],
    fn: Callable[..., Any],
    *args: Any,
    max_retries: int = _ANALYST_MAX_RETRIES,
    retry_delay_seconds: float = _RETRY_DELAY_SECONDS,
) -> T:
    """Retry transient agent failures and only return a validated model."""
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            raw = fn(*args)
            return _ensure_model_output(name, raw, expected_type)
        except Exception as exc:  # LLM/provider/parse/runtime failures
            last_exc = exc
            if attempt < max_retries:
                time.sleep(retry_delay_seconds * attempt)

    raise RuntimeError(
        f"{name} failed after {max_retries} attempts: {last_exc}"
    ) from last_exc

def parallel_analysis_node(state: InvestmentState) -> dict[str, Any]:
    """
    Run Bull, Bear, and Strategist concurrently.
    Each receives live market data AND its own RAG context block.
    """
    ticker = state["ticker"]
    amount = state["amount"]
    portfolio_value = state["portfolio_value"]
    risk_tolerance = state["risk_tolerance"]
    analysis_action = state.get("analysis_action", "buy")
    market_data = state["market_data"] or {}
    rag = state.get("rag_context") or {}
    intent = state.get("intent")
    scenarios = intent.scenarios if intent else []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        bull_fut = ex.submit(
            _run_with_retry,
            "Bull Analyst",
            BullAnalysis,
            run_bull_agent,
            ticker,
            market_data,
            rag.get("bull", ""),
            amount,
            portfolio_value,
            analysis_action,
            scenarios,
        )
        bear_fut = ex.submit(
            _run_with_retry,
            "Bear Analyst",
            BearAnalysis,
            run_bear_agent,
            ticker,
            market_data,
            rag.get("bear", ""),
            amount,
            portfolio_value,
            analysis_action,
            scenarios,
        )
        strategist_fut = ex.submit(
            _run_with_retry,
            "Portfolio Strategist",
            StrategistAnalysis,
            run_strategist_agent,
            ticker, amount, portfolio_value, risk_tolerance,
            market_data, rag.get("strategist", ""), None, analysis_action, scenarios,
        )
        bull = bull_fut.result()
        bear = bear_fut.result()
        strategist = strategist_fut.result()

    return {
        "bull_analysis": bull,
        "bear_analysis": bear,
        "strategist_analysis": strategist,
    }


# ── Node 4 — Gated grounding (conditional) ───────────────────────────────────

_PE_DIVERGENCE_THRESHOLD = 10.0


def _should_verify_facts(state: InvestmentState) -> bool:
    """Return True when bull and bear P/E estimates diverge by more than 10 points."""
    bull: Optional[BullAnalysis] = state.get("bull_analysis")
    bear: Optional[BearAnalysis] = state.get("bear_analysis")
    if bull is None or bear is None:
        return False
    b_pe = bull.pe_ratio
    r_pe = bear.pe_ratio
    if b_pe is None or r_pe is None:
        return False
    return abs(b_pe - r_pe) > _PE_DIVERGENCE_THRESHOLD


def verify_facts_node(state: InvestmentState) -> dict[str, Any]:
    """
    Re-fetch live Yahoo Finance data to override stale P/E estimates.
    Only runs when bull/bear P/E disagree by more than the threshold.
    Merges the fresh pe_ratio into both analyst objects.
    """
    ticker = state["ticker"]
    fresh = fetch_full_market_data(ticker)
    live_pe = fresh.get("pe_ratio")

    updates: dict[str, Any] = {
        "grounding_triggered": True,
        "market_data": {**(state["market_data"] or {}), **fresh},
    }

    if live_pe is not None:
        bull = state["bull_analysis"]
        bear = state["bear_analysis"]
        if bull is not None:
            updates["bull_analysis"] = bull.model_copy(update={"pe_ratio": live_pe})
        if bear is not None:
            updates["bear_analysis"] = bear.model_copy(update={"pe_ratio": live_pe})

    return updates


def route_after_analysis(state: InvestmentState) -> str:
    """Conditional edge: go to verify_facts or jump straight to judge."""
    return "verify_facts" if _should_verify_facts(state) else "judge"


# ── Node 5 — Judge synthesis ──────────────────────────────────────────────────

def judge_node(state: InvestmentState) -> dict[str, Any]:
    """
    Judge receives all three analyst reports plus the same live data and RAG
    context, so it can arbitrate factual disputes and anchor recommendations
    to verified numbers.
    """
    rag = state.get("rag_context") or {}
    bull = state.get("bull_analysis")
    bear = state.get("bear_analysis")
    strategist = state.get("strategist_analysis")

    missing = [
        name for name, value in (
            ("bull_analysis", bull),
            ("bear_analysis", bear),
            ("strategist_analysis", strategist),
        ) if value is None
    ]
    if missing:
        raise RuntimeError(
            "Missing required analyst output(s) after retries: "
            + ", ".join(missing)
        )

    intent = state.get("intent")
    scenarios = intent.scenarios if intent else []

    # Type narrowing for static analyzers; runtime already validated above.
    assert bull is not None and bear is not None and strategist is not None

    recommendation = _run_with_retry(
        "Judge",
        JudgeRecommendation,
        run_judge_agent,
        state["ticker"],
        bull,
        bear,
        strategist,
        state["market_data"] or {},
        rag.get("judge", ""),
        state.get("analysis_action", "buy"),
        scenarios,
        max_retries=_JUDGE_MAX_RETRIES,
    )
    return {"final_recommendation": recommendation}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_workflow() -> Any:
    graph = StateGraph(InvestmentState)

    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("rag_ingest", rag_node)
    graph.add_node("parallel_analysis", parallel_analysis_node)
    graph.add_node("verify_facts", verify_facts_node)
    graph.add_node("judge", judge_node)

    graph.set_entry_point("fetch_data")
    graph.add_edge("fetch_data", "intent_router")
    graph.add_edge("intent_router", "rag_ingest")
    graph.add_edge("rag_ingest", "parallel_analysis")
    graph.add_conditional_edges(
        "parallel_analysis",
        route_after_analysis,
        {"verify_facts": "verify_facts", "judge": "judge"},
    )
    graph.add_edge("verify_facts", "judge")
    graph.add_edge("judge", END)

    return graph.compile()


_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow


# ── Public entry point ────────────────────────────────────────────────────────

def run_analysis(
    ticker: str,
    amount: float,
    portfolio_value: float,
    risk_tolerance: str,
    time_horizon: str,
    analysis_action: str = "buy",
    user_query: Optional[str] = None,
) -> InvestmentState:
    """Execute the full grounded + RAG investment analysis workflow."""
    initial_state: InvestmentState = {
        "ticker": ticker.upper(),
        "amount": amount,
        "portfolio_value": portfolio_value,
        "risk_tolerance": risk_tolerance,
        "time_horizon": time_horizon,
        "user_query": user_query,
        "analysis_action": analysis_action,
        "intent": None,
        "market_data": None,
        "rag_context": None,
        "rag_summary": None,
        "sec_filing": None,
        "bull_analysis": None,
        "bear_analysis": None,
        "strategist_analysis": None,
        "final_recommendation": None,
        "grounding_triggered": False,
    }
    return get_workflow().invoke(initial_state)
