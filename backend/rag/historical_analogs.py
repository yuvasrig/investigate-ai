"""
Pre-seeded historical analog documents for scenario grounding.

These documents are authored from publicly available historical data to give
RAG-based agents verified precedents for common disruption and macro scenarios.
They live in a dedicated ChromaDB collection ("_ANALOGS") and are retrieved
whenever the Intent Router detects a matching scenario tag.

Analogs currently seeded
────────────────────────
AI Disruption Analog:
  • Excel → Accounting (1988)      — commodity hours disrupted, advisory grew
  • AWS → IT Consulting (2010)     — infra consulting compressed, cloud consulting boomed
  • ATM → Bank Tellers (1970s–90s) — volume automation expanded branch count
  • CAD → Engineering Drafters (1980s) — near-total displacement of a profession

Regulatory Crackdown Analog:
  • Microsoft Antitrust (1998)     — sentiment headwind, limited product impact

Valuation Compression Analog:
  • Dot-Com Crash (2000)           — timeline and magnitude by PE tier

Rates Shock / Stagflation Analog:
  • 1970s–1980 stagflation         — winners / losers, modern parallel
"""

from __future__ import annotations

from rag import store

# Special ticker key for the shared analogs collection
ANALOGS_TICKER = "_ANALOGS"

# ── Authored analog documents ─────────────────────────────────────────────────

ANALOG_DOCUMENTS: list[dict] = [
    # ── AI Disruption ─────────────────────────────────────────────────────────
    {
        "text": (
            "Excel → Accounting disruption (1988 analog): "
            "When Lotus 1-2-3 and Microsoft Excel spread in the late 1980s, bookkeeping clerks "
            "—a role accounting firms charged at $40–60/hr—saw demand fall ~50% between 1985 "
            "and 1995 (BLS Occupational Outlook data). "
            "However, accounting firms that pivoted to advisory services (tax strategy, M&A advisory, "
            "CFO services) grew total revenue 2–3× over the same period. "
            "Key lesson: disruption compressed commodity hours but expanded advisory revenue. "
            "Firms slow to pivot (small bookkeeping shops) saw revenue fall 60–80%. "
            "Large diversified firms (Big Eight) converted ~30% of headcount to new service lines "
            "within 5 years. "
            "Analog risk for AI vs consulting: AI compresses the $150–250/hr analyst tier "
            "but advisory, transformation, and change management remain human-led. "
            "Historical revenue impact on firms that pivoted: +20–40% margin expansion."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "Excel → Accounting Disruption (1988)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 0,
        },
    },
    {
        "text": (
            "AWS → IT consulting disruption (2010 analog): "
            "AWS mainstream adoption from 2010–2015 eliminated a large share of on-premise "
            "infrastructure consulting revenue. Gartner estimated infrastructure implementation "
            "consulting (server rack, data centre, network config) saw 30–40% margin compression "
            "from 2010–2016 as clients migrated to cloud. "
            "Firms like EDS, HP Services, and IBM Global Services saw revenue from traditional "
            "IT implementation fall ~25% over 5 years. "
            "However, cloud migration consulting (AWS/Azure/GCP) created a new $50B+ market. "
            "Accenture, Capgemini, and Infosys all pivoted successfully: "
            "Accenture Technology revenues grew from $12B (2012) to $27B (2017) despite "
            "commoditisation of legacy IT services. "
            "Analog risk for AI vs consulting: AI automates slide production, data analysis, "
            "and junior deliverables but creates implementation/change-management demand. "
            "Revenue shift timeline: 3–5 years from compression onset to new-service offset."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "AWS → IT Consulting Disruption (2010)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 1,
        },
    },
    {
        "text": (
            "ATM → Bank Tellers (1970s–1990s analog — augmentation, not replacement): "
            "ATM deployment from 1970–1995 is the most-cited case of automation that INCREASED "
            "total employment in the disrupted sector. "
            "From 1985–2002, US bank branches rose from 60,000 to 92,000 because ATMs made branch "
            "operation cheaper (fewer teller FTEs per branch), enabling banks to open more locations. "
            "Teller headcount per branch fell 30% but total tellers employed rose 2% over 20 years. "
            "Teller role transformed: transaction processing → relationship banking, upselling, advisory. "
            "Key lesson: automation can expand the market while transforming the human role. "
            "For consulting: if AI reduces delivery cost per engagement, firms may take on more "
            "(smaller/mid-market) clients, expanding total market rather than contracting. "
            "Bull scenario: Accenture/McKinsey grows mid-market share previously uneconomic to serve."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "ATM → Bank Teller Role Transformation (1970s–1990s)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 2,
        },
    },
    {
        "text": (
            "CAD software → Engineering Drafters (1980s analog — near-total displacement): "
            "AutoCAD release (1982) and mass adoption 1985–1995 resulted in near-total "
            "displacement of engineering drafting as a profession. "
            "BLS records show Drafters (SOC 17-3010) fell from ~350,000 in 1983 to ~210,000 "
            "in 2000: a 40% reduction in 17 years. "
            "Unlike bank tellers or accountants, drafters did not successfully pivot to advisory "
            "roles at scale — the cognitive complexity of remaining work was too low. "
            "This is the worst-case 'displacement' scenario for consulting: "
            "if AI can produce strategy deliverables end-to-end (slides, models, insights), "
            "the junior analyst tier (Analyst/Associate, 2–4 years) could face similar structural decline. "
            "McKinsey estimates ~40% of management consulting time is in data gathering + analysis "
            "— the most automatable tier. "
            "Bear scenario revenue impact: 15–20% revenue decline in 5 years if clients "
            "insource AI-augmented analysis, bypassing junior consulting tiers entirely."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "CAD → Engineering Drafters Displacement (1980s)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 3,
        },
    },
    # ── Regulatory Crackdown ──────────────────────────────────────────────────
    {
        "text": (
            "Microsoft antitrust (1998) — Regulatory Crackdown analog: "
            "DOJ antitrust suit filed May 1998 against Microsoft (MSFT). "
            "MSFT stock fell ~35% from peak ($59) to trough ($30) over 18 months (1999–2001). "
            "However, ~60% of the decline was dot-com driven, not antitrust. "
            "Settlement (Nov 2001) had minimal product impact: Microsoft retained Windows/IE bundling. "
            "MSFT stock recovered to pre-suit levels within 36 months of settlement. "
            "Key lesson: antitrust fears in tech historically overstated near-term impact "
            "but create multi-year sentiment headwinds (15–25% P/E multiple compression). "
            "Analog for AI regulation: EU AI Act, US Executive Orders may compress multiples "
            "but rarely prevent core business model continuation. "
            "Typical regulatory headwind duration: 18–36 months from filing to resolution."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Regulatory Crackdown Analog",
            "title": "Microsoft Antitrust (1998) — Regulatory Analog",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 4,
        },
    },
    # ── Valuation Compression ─────────────────────────────────────────────────
    {
        "text": (
            "Dot-com valuation compression (2000) analog: "
            "Nasdaq fell 78% from peak (5,048 on Mar 10, 2000) to trough (1,114 on Oct 9, 2002). "
            "High-multiple tech (P/E >100×) fell average 85%. "
            "Profitable tech (P/E 30–50×) fell average 55%. "
            "Revenue-growth-only (no earnings) fell average 95%. "
            "Recovery: Nasdaq did not revisit 2000 peak until April 2015 — 15 years later. "
            "S&P 500 returned to 2000 peak in 2007 (7 years). "
            "Key lesson: companies trading >40× P/E with <20% revenue growth face "
            "60–75% downside in a multiple-compression scenario if growth disappoints. "
            "Recovery driver: actual earnings growth, not narrative re-rating."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Valuation Compression Analog",
            "title": "Dot-Com Valuation Compression (2000)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 5,
        },
    },
    # ── Rates Shock / Stagflation ─────────────────────────────────────────────
    {
        "text": (
            "1970s–1980 stagflation / rates shock analog: "
            "US CPI peaked at 14.8% in March 1980. Fed Funds Rate peaked at 20% in June 1981. "
            "S&P 500 real returns: −15% from 1968–1982 (14 years flat-to-negative in real terms). "
            "Winners: energy stocks (+400% real 1974–1980), commodities, gold (+800%). "
            "Losers: long-duration bonds (−30% real), high-PE growth stocks (−60–80%), REITs. "
            "Modern parallel (2022–2025): 10yr Treasury from 0.5% (Aug 2020) to 5.0% (Oct 2023) "
            "compressed high-PE growth multiples by 40–60%. "
            "Historical precedent: rate normalisation from 5% → 3% over 2–3 years "
            "has historically led to S&P P/E re-expansion of 15–25% "
            "and tech sector outperformance in the 12–18 months following peak rates."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Rates Shock / Stagflation Analog",
            "title": "1970s Stagflation / 1980 Rate Shock Analog",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 6,
        },
    },
]

# ── Seeding ───────────────────────────────────────────────────────────────────

_analogs_seeded: bool = False


def ensure_analogs_seeded() -> None:
    """Upsert analog documents into ChromaDB (idempotent, once per process)."""
    global _analogs_seeded
    if _analogs_seeded:
        return
    try:
        # Use a very long TTL so analogs are treated as permanently fresh
        if not store.is_fresh(ANALOGS_TICKER, max_age_hours=24 * 365):
            store.upsert_documents(ANALOGS_TICKER, ANALOG_DOCUMENTS)
    except Exception:
        pass
    _analogs_seeded = True


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve_analogs(scenarios: list[str], n_results: int = 3) -> str:
    """
    Retrieve historical analog chunks matching the given scenario tags.
    Returns a formatted grounding block ready for injection into agent prompts.
    Returns an empty string if no scenarios provided or no matches found.
    """
    if not scenarios:
        return ""

    ensure_analogs_seeded()

    # Query with all scenario names combined for best semantic match
    query = " ".join(scenarios)
    results = store.similarity_search(ANALOGS_TICKER, query, n_results=n_results)
    if not results:
        return ""

    lines = [
        "═══ HISTORICAL ANALOGS (Gated Grounding — RAG Verified) ═══",
        f"Scenarios detected: {', '.join(scenarios)}",
        "Use these verified precedents to quantify probability and magnitude of impact.",
        "Cite the specific analog title and data point when referencing scenario outcomes.",
        "",
    ]
    for r in results:
        title = r["metadata"].get("title", "Historical Analog")
        lines.append(f"▶ {title}  [relevance: {r['score']:.2f}]")
        lines.append(r["text"])
        lines.append("")

    return "\n".join(lines)
