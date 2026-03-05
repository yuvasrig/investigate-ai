"""
LangGraph workflow for InvestiGate.

Graph order (always):
  fetch_market_data → parallel_analysis → judge → END

Real market data is fetched FIRST so every agent — Bull, Bear, Strategist,
and Judge — reasons from the same verified live snapshot, not training-data
guesses.  The old conditional P/E grounding gate has been removed; grounding
is now unconditional and happens before any LLM call.
"""

import concurrent.futures
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, END

from schemas import BullAnalysis, BearAnalysis, StrategistAnalysis, JudgeRecommendation
from agents import run_bull_agent, run_bear_agent, run_strategist_agent, run_judge_agent
from tools import fetch_full_market_data


# ── State ─────────────────────────────────────────────────────────────────────

class InvestmentState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────────
    ticker: str
    amount: float
    portfolio_value: float
    risk_tolerance: str
    time_horizon: str

    # ── Live market data (populated first) ────────────────────────────────────
    market_data: Optional[dict]

    # ── Agent outputs ─────────────────────────────────────────────────────────
    bull_analysis: Optional[BullAnalysis]
    bear_analysis: Optional[BearAnalysis]
    strategist_analysis: Optional[StrategistAnalysis]
    final_recommendation: Optional[JudgeRecommendation]


# ── Node 1 — Fetch real market data ──────────────────────────────────────────

def fetch_data_node(state: InvestmentState) -> dict[str, Any]:
    """
    Pull a live snapshot from yfinance.
    This runs BEFORE any agent so every LLM call has real numbers to work from.
    """
    market_data = fetch_full_market_data(state["ticker"])
    return {"market_data": market_data}


# ── Node 2 — Parallel agent analysis ─────────────────────────────────────────

def parallel_analysis_node(state: InvestmentState) -> dict[str, Any]:
    """
    Run Bull, Bear, and Strategist agents concurrently.
    All three receive the real market data fetched in node 1.
    """
    ticker = state["ticker"]
    amount = state["amount"]
    portfolio_value = state["portfolio_value"]
    risk_tolerance = state["risk_tolerance"]
    market_data = state["market_data"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        bull_future = executor.submit(run_bull_agent, ticker, market_data)
        bear_future = executor.submit(run_bear_agent, ticker, market_data)
        strategist_future = executor.submit(
            run_strategist_agent,
            ticker, amount, portfolio_value, risk_tolerance, market_data,
        )

        bull = bull_future.result()
        bear = bear_future.result()
        strategist = strategist_future.result()

    return {
        "bull_analysis": bull,
        "bear_analysis": bear,
        "strategist_analysis": strategist,
    }


# ── Node 3 — Judge synthesises all outputs ────────────────────────────────────

def judge_node(state: InvestmentState) -> dict[str, Any]:
    """
    Judge agent gets all three analyst reports AND the same live market data,
    so it can settle factual disputes and anchor its recommendation to the
    real current price.
    """
    recommendation = run_judge_agent(
        ticker=state["ticker"],
        bull=state["bull_analysis"],
        bear=state["bear_analysis"],
        strategist=state["strategist_analysis"],
        market_data=state["market_data"],
    )
    return {"final_recommendation": recommendation}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_workflow() -> Any:
    graph = StateGraph(InvestmentState)

    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("parallel_analysis", parallel_analysis_node)
    graph.add_node("judge", judge_node)

    graph.set_entry_point("fetch_data")
    graph.add_edge("fetch_data", "parallel_analysis")
    graph.add_edge("parallel_analysis", "judge")
    graph.add_edge("judge", END)

    return graph.compile()


# ── Singleton ─────────────────────────────────────────────────────────────────

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
    """Execute the full grounded investment analysis workflow."""
    initial_state: InvestmentState = {
        "ticker": ticker.upper(),
        "amount": amount,
        "portfolio_value": portfolio_value,
        "risk_tolerance": risk_tolerance,
        "time_horizon": time_horizon,
        "market_data": None,
        "bull_analysis": None,
        "bear_analysis": None,
        "strategist_analysis": None,
        "final_recommendation": None,
    }
    return get_workflow().invoke(initial_state)
