"""
High-level RAG retrieval interface for InvestiGate agents.

Usage:
    from rag.retriever import ingest_ticker, retrieve_all_agents

    # Ingest once (cached — skips if already fresh)
    ingest_ticker(ticker, market_data)

    # Retrieve per-agent context (parallel, fast after ingestion)
    rag_context = retrieve_all_agents(ticker)
    # → {"bull": "...", "bear": "...", "strategist": "...", "judge": "..."}
"""

import concurrent.futures
import os

from rag.ingestion import SECIngester, NewsIngester
from rag import store

RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "true").lower() == "true"

# ── Per-agent retrieval queries ───────────────────────────────────────────────
# Each query is tuned to surface the most relevant document chunks
# for that agent's specific analytical perspective.

AGENT_QUERIES: dict[str, str] = {
    "bull": (
        "competitive advantages revenue growth market share leadership "
        "product innovation expanding margins free cash flow growth "
        "TAM total addressable market earnings growth catalysts "
        "new products partnerships demand acceleration"
    ),
    "bear": (
        "risk factors competition threats market share loss regulatory risks "
        "antitrust litigation supply chain customer concentration "
        "valuation concerns high PE ratio earnings miss guidance cut "
        "macro headwinds cyclical downturn financial leverage debt"
    ),
    "strategist": (
        "institutional ownership buybacks dividends capital allocation "
        "portfolio concentration volatility beta correlation sector exposure "
        "management commentary forward guidance liquidity position sizing"
    ),
    "judge": (
        "investment thesis key factors summary recommendation "
        "price target upside downside risk reward analyst consensus "
        "management guidance forward outlook strategic priorities "
        "overall assessment balanced view"
    ),
}


# ── Ingestion ─────────────────────────────────────────────────────────────────

def ingest_ticker(ticker: str, market_data: dict) -> dict:
    """
    Fetch and index documents for a ticker if not already cached.

    Sources:
      - SEC 10-K and 10-Q filings (via EDGAR REST API)
      - Full news article text (from URLs in market_data['recent_news'])

    Returns a summary dict: {"sec": N, "news": M, "cache_hit": bool}
    """
    if not RAG_ENABLED:
        return {"sec": 0, "news": 0, "cache_hit": False, "disabled": True}

    if store.is_fresh(ticker):
        return {"sec": 0, "news": 0, "cache_hit": True}

    sec_count = 0
    news_count = 0

    # SEC EDGAR — 10-K risk factors, business overview, MD&A
    try:
        sec_ingester = SECIngester()
        sec_docs = sec_ingester.fetch_documents(ticker)
        if sec_docs:
            sec_count = store.upsert_documents(ticker, sec_docs)
    except Exception:
        pass  # non-fatal — agents still run with grounding

    # Full news article text
    try:
        news_items = market_data.get("recent_news", [])
        if news_items:
            news_ingester = NewsIngester()
            news_docs = news_ingester.fetch_documents(ticker, news_items)
            if news_docs:
                news_count = store.upsert_documents(ticker, news_docs)
    except Exception:
        pass

    return {"sec": sec_count, "news": news_count, "cache_hit": False}


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve_for_agent(ticker: str, role: str, n_results: int = 6) -> str:
    """
    Retrieve and format the most relevant document chunks for an agent role.
    Returns an empty string if RAG is disabled or no documents are indexed.
    """
    if not RAG_ENABLED:
        return ""

    query = AGENT_QUERIES.get(role, AGENT_QUERIES["judge"])
    results = store.similarity_search(ticker, query, n_results=n_results)

    if not results:
        return ""

    sec_results = [r for r in results if r["metadata"].get("source") == "sec_edgar"]
    news_results = [r for r in results if r["metadata"].get("source") == "news"]

    lines = [
        "=" * 60,
        f"  RETRIEVED DOCUMENTS — {ticker} ({role.upper()} agent)",
        "=" * 60,
    ]

    if sec_results:
        lines.append("\nSEC FILING EXCERPTS")
        for r in sec_results:
            form = r["metadata"].get("form", "Filing")
            section = r["metadata"].get("section", "").replace("_", " ").upper()
            lines.append(f"\n[{form} — {section}  relevance: {r['score']:.2f}]")
            lines.append(r["text"])

    if news_results:
        lines.append("\nNEWS ARTICLE EXCERPTS")
        for r in news_results:
            title = r["metadata"].get("title", "")
            pub = r["metadata"].get("publisher", "")
            header = f"[{pub}: {title}]" if pub else f"[{title}]"
            lines.append(f"\n{header}  relevance: {r['score']:.2f}")
            lines.append(r["text"])

    lines.append("=" * 60)
    return "\n".join(lines)


def retrieve_all_agents(ticker: str) -> dict[str, str]:
    """
    Retrieve RAG context for all four agent roles in parallel.
    Returns {"bull": str, "bear": str, "strategist": str, "judge": str}.
    Empty strings mean no relevant documents were found for that role.
    """
    if not RAG_ENABLED:
        return {role: "" for role in AGENT_QUERIES}

    roles = list(AGENT_QUERIES.keys())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {role: ex.submit(retrieve_for_agent, ticker, role) for role in roles}
        return {role: fut.result() for role, fut in futures.items()}


def rag_status(ticker: str) -> dict:
    """Return RAG status for a ticker — useful for /health endpoint."""
    return {
        "enabled": RAG_ENABLED,
        "fresh": store.is_fresh(ticker) if RAG_ENABLED else False,
        "collection": store.collection_stats(ticker) if RAG_ENABLED else {},
    }
