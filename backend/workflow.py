"""
LangGraph workflow for InvestiGate.

Graph (in order):

  fetch_data           ← yfinance: live price, financials, analyst consensus, news URLs
       ↓
  rag_ingest           ← fetch SEC 10-K/10-Q + full news articles, embed into ChromaDB
       ↓                  (cache-aware: skips if fresh data already indexed)
  parallel_analysis    ← Bull, Bear, Strategist run concurrently
       ↓                  each receives BOTH grounding data AND per-role RAG context
  judge                ← synthesises all three reports + same data sources
       ↓
  END

Both grounding (structured live data) and RAG (document retrieval) run before
any LLM call, so every agent reasons from the same verified foundation.
"""

import concurrent.futures
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, END

from schemas import BullAnalysis, BearAnalysis, StrategistAnalysis, JudgeRecommendation
from agents import run_bull_agent, run_bear_agent, run_strategist_agent, run_judge_agent
from tools import fetch_full_market_data
from rag.retriever import ingest_ticker, retrieve_all_agents


# ── State ─────────────────────────────────────────────────────────────────────

class InvestmentState(TypedDict):
    # Inputs
    ticker: str
    amount: float
    portfolio_value: float
    risk_tolerance: str
    time_horizon: str

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

    # Ingest (cache-aware — typically fast on repeat requests)
    rag_summary = ingest_ticker(ticker, market_data)

    # Retrieve per-agent context (parallel, < 0.5s after ingestion)
    rag_context = retrieve_all_agents(ticker)

    return {"rag_context": rag_context, "rag_summary": rag_summary}


# ── Node 3 — Parallel agent analysis ─────────────────────────────────────────

def parallel_analysis_node(state: InvestmentState) -> dict[str, Any]:
    """
    Run Bull, Bear, and Strategist concurrently.
    Each receives live market data AND its own RAG context block.
    """
    ticker = state["ticker"]
    amount = state["amount"]
    portfolio_value = state["portfolio_value"]
    risk_tolerance = state["risk_tolerance"]
    market_data = state["market_data"] or {}
    rag = state.get("rag_context") or {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        bull_fut = ex.submit(
            run_bull_agent, ticker, market_data, rag.get("bull", "")
        )
        bear_fut = ex.submit(
            run_bear_agent, ticker, market_data, rag.get("bear", "")
        )
        strategist_fut = ex.submit(
            run_strategist_agent,
            ticker, amount, portfolio_value, risk_tolerance,
            market_data, rag.get("strategist", ""),
        )
        bull = bull_fut.result()
        bear = bear_fut.result()
        strategist = strategist_fut.result()

    return {
        "bull_analysis": bull,
        "bear_analysis": bear,
        "strategist_analysis": strategist,
    }


# ── Node 4 — Judge synthesis ──────────────────────────────────────────────────

def judge_node(state: InvestmentState) -> dict[str, Any]:
    """
    Judge receives all three analyst reports plus the same live data and RAG
    context, so it can arbitrate factual disputes and anchor recommendations
    to verified numbers.
    """
    rag = state.get("rag_context") or {}
    recommendation = run_judge_agent(
        ticker=state["ticker"],
        bull=state["bull_analysis"],
        bear=state["bear_analysis"],
        strategist=state["strategist_analysis"],
        market_data=state["market_data"] or {},
        rag_context=rag.get("judge", ""),
    )
    return {"final_recommendation": recommendation}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_workflow() -> Any:
    graph = StateGraph(InvestmentState)

    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("rag_ingest", rag_node)
    graph.add_node("parallel_analysis", parallel_analysis_node)
    graph.add_node("judge", judge_node)

    graph.set_entry_point("fetch_data")
    graph.add_edge("fetch_data", "rag_ingest")
    graph.add_edge("rag_ingest", "parallel_analysis")
    graph.add_edge("parallel_analysis", "judge")
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
) -> InvestmentState:
    """Execute the full grounded + RAG investment analysis workflow."""
    initial_state: InvestmentState = {
        "ticker": ticker.upper(),
        "amount": amount,
        "portfolio_value": portfolio_value,
        "risk_tolerance": risk_tolerance,
        "time_horizon": time_horizon,
        "market_data": None,
        "rag_context": None,
        "rag_summary": None,
        "bull_analysis": None,
        "bear_analysis": None,
        "strategist_analysis": None,
        "final_recommendation": None,
    }
    return get_workflow().invoke(initial_state)
