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

from schemas import BullAnalysis, BearAnalysis, StrategistAnalysis, JudgeRecommendation
from agents import run_bull_agent, run_bear_agent, run_strategist_agent, run_judge_agent
from tools import fetch_full_market_data
from rag.retriever import ingest_ticker, retrieve_all_agents

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

    # Live market snapshot (populated by fetch_data node)
    market_data: Optional[dict]

    # Per-agent RAG context strings (populated by rag_ingest node)
    rag_context: Optional[dict[str, str]]   # {"bull": str, "bear": str, ...}
    rag_summary: Optional[dict]              # {"sec": N, "news": M, "cache_hit": bool}

    # Agent outputs
    bull_analysis: Optional[BullAnalysis]
    bear_analysis: Optional[BearAnalysis]
    strategist_analysis: Optional[StrategistAnalysis]
    final_recommendation: Optional[JudgeRecommendation]

    # Gated grounding flag
    grounding_triggered: Optional[bool]
    
    # Synchronization flag for parallel execution
    sync_complete: Optional[bool]


# ── Node 1 — Live market data ─────────────────────────────────────────────────

def fetch_data_node(state: InvestmentState) -> dict[str, Any]:
    """Pull ~35 real-time fields from yfinance before any agent runs."""
    market_data = fetch_full_market_data(state["ticker"])
    return {"market_data": market_data}


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

    return {"rag_context": rag_context, "rag_summary": rag_summary}


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

def bull_node(state: InvestmentState) -> dict[str, Any]:
    ticker = state["ticker"]
    amount = state["amount"]
    portfolio_value = state["portfolio_value"]
    analysis_action = state.get("analysis_action", "buy")
    market_data = state["market_data"] or {}
    rag = state.get("rag_context") or {}

    bull = _run_with_retry(
        "Bull Analyst",
        BullAnalysis,
        run_bull_agent,
        ticker,
        market_data,
        rag.get("bull", ""),
        amount,
        portfolio_value,
        analysis_action,
    )
    return {"bull_analysis": bull}

def bear_node(state: InvestmentState) -> dict[str, Any]:
    ticker = state["ticker"]
    amount = state["amount"]
    portfolio_value = state["portfolio_value"]
    analysis_action = state.get("analysis_action", "buy")
    market_data = state["market_data"] or {}
    rag = state.get("rag_context") or {}

    bear = _run_with_retry(
        "Bear Analyst",
        BearAnalysis,
        run_bear_agent,
        ticker,
        market_data,
        rag.get("bear", ""),
        amount,
        portfolio_value,
        analysis_action,
    )
    return {"bear_analysis": bear}

def strategist_node(state: InvestmentState) -> dict[str, Any]:
    ticker = state["ticker"]
    amount = state["amount"]
    portfolio_value = state["portfolio_value"]
    risk_tolerance = state["risk_tolerance"]
    analysis_action = state.get("analysis_action", "buy")
    market_data = state["market_data"] or {}
    rag = state.get("rag_context") or {}

    strategist = _run_with_retry(
        "Portfolio Strategist",
        StrategistAnalysis,
        run_strategist_agent,
        ticker, amount, portfolio_value, risk_tolerance,
        market_data, rag.get("strategist", ""), None, analysis_action,
    )
    return {"strategist_analysis": strategist}

# (Threadpool executor removed in favor of separate nodes)


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
        max_retries=_JUDGE_MAX_RETRIES,
    )
    return {"final_recommendation": recommendation}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_workflow() -> Any:
    graph = StateGraph(InvestmentState)

    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("rag_ingest", rag_node)
    graph.add_node("bull_node", bull_node)
    graph.add_node("bear_node", bear_node)
    graph.add_node("strategist_node", strategist_node)
    graph.add_node("verify_facts", verify_facts_node)
    graph.add_node("judge", judge_node)

    graph.set_entry_point("fetch_data")
    graph.add_edge("fetch_data", "rag_ingest")
    
    # Fan out to parallel agent nodes
    graph.add_edge("rag_ingest", "bull_node")
    graph.add_edge("rag_ingest", "bear_node")
    graph.add_edge("rag_ingest", "strategist_node")
    
    # Conditional logic requires waiting for all 3 agents to finish.
    # We create a dummy synchronization node to easily collect the parallel states.
    def sync_node(state: InvestmentState) -> dict[str, Any]:
        return {"sync_complete": True}
    
    graph.add_node("sync", sync_node)
    graph.add_edge("bull_node", "sync")
    graph.add_edge("bear_node", "sync")
    graph.add_edge("strategist_node", "sync")
    
    graph.add_conditional_edges(
        "sync",
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
) -> InvestmentState:
    """Execute the full grounded + RAG investment analysis workflow."""
    initial_state: InvestmentState = {
        "ticker": ticker.upper(),
        "amount": amount,
        "portfolio_value": portfolio_value,
        "risk_tolerance": risk_tolerance,
        "time_horizon": time_horizon,
        "analysis_action": analysis_action,
        "market_data": None,
        "rag_context": None,
        "rag_summary": None,
        "bull_analysis": None,
        "bear_analysis": None,
        "strategist_analysis": None,
        "final_recommendation": None,
        "grounding_triggered": False,
    }
    return get_workflow().invoke(initial_state)
