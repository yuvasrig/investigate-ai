# InvestiGate — Architecture

> A deep-dive into the design decisions, data flows, and component boundaries that power the multi-agent investment debate engine.

---

## Table of Contents

- [System Overview](#system-overview)
- [LangGraph Workflow](#langgraph-workflow)
- [Agent Design](#agent-design)
- [RAG Pipeline](#rag-pipeline)
- [LLM Provider Layer](#llm-provider-layer)
- [Frontend Architecture](#frontend-architecture)
- [Storage Layer](#storage-layer)
- [Data Models](#data-models)
- [Configuration Reference](#configuration-reference)

---

## System Overview

InvestiGate is split into a Python backend and a React frontend. All LLM inference stays on the backend; the frontend is a pure consumer of the REST API.

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                            │
│  React 18 + TypeScript + Vite + Tailwind + shadcn/ui    │
│  :8080                                                  │
└────────────────────┬────────────────────────────────────┘
                     │  HTTP / REST
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI  :8000                          │
│                                                         │
│  ┌──────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │  Intent  │  │  LangGraph  │  │   Portfolio /   │    │
│  │  Router  │  │  Workflow   │  │   Voice / Auth  │    │
│  └──────────┘  └──────┬──────┘  └─────────────────┘    │
│                        │                                │
│          ┌─────────────┼──────────────────┐             │
│          │             │                  │             │
│  ┌───────▼──┐  ┌───────▼──┐  ┌───────────▼──┐          │
│  │  Bull    │  │  Bear    │  │  Strategist  │          │
│  │  Agent   │  │  Agent   │  │  Agent       │          │
│  └──────────┘  └──────────┘  └──────────────┘          │
│          └─────────────┬──────────────────┘             │
│                 ┌──────▼──────┐                         │
│                 │   Judge     │                         │
│                 │   Agent     │                         │
│                 └─────────────┘                         │
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐     │
│  │  yfinance  │  │ ChromaDB   │  │ SQLite history │     │
│  │  SEC EDGAR │  │ (RAG store)│  │ + auth         │     │
│  └────────────┘  └────────────┘  └────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## LangGraph Workflow

The analysis pipeline is a directed acyclic graph compiled by LangGraph. Each node is a pure function that reads from the shared `InvestmentState` TypedDict and returns a partial update.

```
fetch_data
    │
    ▼
rag_ingest
    │
    ├──────────────────────┐
    │                      │
    ▼                      ▼
bull_node            bear_node
    │                      │
    │             strategist_node
    │                      │
    └──────────┬───────────┘
               ▼
             sync ──── conditional edge ───┐
               │                          │
               ▼ (no P/E divergence)       ▼ (P/E divergence > 10)
             judge                   verify_facts
                                          │
                                          ▼
                                        judge
                                          │
                                          ▼
                                         END
```

### Node descriptions

| Node | File | Responsibility |
|---|---|---|
| `fetch_data` | `workflow.py` | Pulls ~35 live fields from yfinance (price, P/E, analyst consensus, news URLs) |
| `rag_ingest` | `workflow.py` → `rag/retriever.py` | Ingests SEC filings + news articles into ChromaDB; retrieves per-agent context chunks |
| `bull_node` | `workflow.py` | Runs Bull agent with grounding data + bull-optimized RAG context |
| `bear_node` | `workflow.py` | Runs Bear agent with grounding data + bear-optimized RAG context |
| `strategist_node` | `workflow.py` | Runs Portfolio Strategist with risk/allocation focus |
| `sync` | `workflow.py` | Barrier node — waits for all three parallel agents before routing |
| `verify_facts` | `workflow.py` | **Conditional.** Re-fetches live P/E from Yahoo Finance when bull and bear estimates diverge by more than 10 points |
| `judge` | `workflow.py` | Synthesises all three reports into a final verdict with confidence breakdown and traffic-light signal |

### Retry strategy

All agent calls are wrapped in `_run_with_retry`. Analysts get 3 attempts with 1-second exponential backoff; the Judge gets 2. Every output is validated against its Pydantic schema before being accepted.

---

## Agent Design

Each analyst is a role-scoped LLM call. Agents receive the same grounding data but different RAG retrieval queries, ensuring genuine independence before the Judge synthesises.

### Bull Analyst

- **Goal** — Build the strongest possible case for buying.
- **RAG query focus** — competitive advantages, revenue growth, TAM, free cash flow catalysts, new products.
- **Output** — `BullAnalysis`: competitive advantages, growth catalysts, valuation justification, best-case price target, confidence score (0–10), P/E estimate.

### Bear Analyst

- **Goal** — Surface every meaningful risk and headwind.
- **RAG query focus** — risk factors, competition threats, regulatory exposure, debt, earnings miss history.
- **Output** — `BearAnalysis`: competition threats, valuation concerns, cyclical risks, worst-case price target, confidence score, P/E estimate.

### Portfolio Strategist

- **Goal** — Give portfolio-level position sizing advice independent of conviction.
- **RAG query focus** — institutional ownership, buybacks, volatility, beta, correlation, capital allocation.
- **Output** — `StrategistAnalysis`: concentration risk (LOW / MODERATE / HIGH / VERY HIGH), recommended dollar allocation, alternatives.

### Judge

- **Goal** — Arbitrate the debate and produce an actionable verdict.
- **Inputs** — all three analyst reports + same live data + judge-tuned RAG context.
- **Output** — `JudgeRecommendation`: action (buy/hold/sell), recommended amount, 5-dimensional confidence breakdown, traffic-light color, evaluated scenarios, evidence assessment with evidence-weighted scoring.

### Intent Router

A deterministic regex classifier (`agents/intent_router.py`) that runs before the LangGraph workflow. It:

1. Extracts the target ticker from natural-language queries.
2. Maps keywords to macro-scenario labels (e.g. "inflation" → `Rates Shock / Stagflation Analog`).
3. Auto-injects AI disruption scenarios for tickers with known exposure (ACN, IBM, INFY, etc.).
4. Sets `requires_deep_dive` to skip the 4-agent pipeline for simple informational queries.

---

## RAG Pipeline

The Retrieval-Augmented Generation layer gives every agent access to primary-source documents before any LLM call, grounding outputs in verified facts rather than parametric memory.

### Ingestion sources

| Source | Module | Documents |
|---|---|---|
| SEC EDGAR | `rag/ingestion.py` → `SECIngester` | 10-K / 10-Q filings — Business (Item 1), Risk Factors (Item 1A), MD&A (Item 7) |
| News articles | `rag/ingestion.py` → `NewsIngester` | Full article text from yfinance news URLs; headline fallback for paywalled pages |
| FMP financials | `rag/ingestion.py` → `FMPFinancialsIngester` | 4 years of audited income statement, balance sheet, cash flow (requires `FMP_API_KEY`) |
| Historical analogs | `rag/historical_analogs.py` | Curated collection of historical market events seeded once per process |

### Retrieval flow

```
User request
    │
    ▼
ingest_ticker()  ─── cache hit? ──▶ skip ingestion
    │
    ├── SECIngester.fetch_documents()
    ├── NewsIngester.fetch_documents()
    └── FMPFinancialsIngester.fetch_documents()
              │
              ▼ (chunk → embed → upsert)
         ChromaDB collection (per ticker)
              │
              ▼ (4 parallel similarity searches)
    retrieve_all_agents()
    ├── bull   query → top-6 chunks
    ├── bear   query → top-6 chunks
    ├── strategist query → top-6 chunks
    └── judge  query → top-6 chunks
              │
              ▼ (scenario analogs appended if intent router detected scenarios)
    rag_context dict {"bull": str, "bear": str, ...}
```

Text is chunked at 350 words with 50-word overlap before embedding. Each chunk stores `source`, `form`, `section`, `title`, and `publisher` metadata for citation display in the UI.

---

## LLM Provider Layer

`llm_factory.py` provides a provider-agnostic `BaseChatModel` interface. Agents call `get_analyst_llm()` or `get_judge_llm()` — they never reference provider details directly.

### Provider modes

| Mode | Analyst model | Judge model | Requires |
|---|---|---|---|
| `ollama` | `llama3.1` (default) | `llama3.1` | Ollama running locally |
| `anthropic` | `claude-sonnet-4-6` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| `openai` | `gpt-4o` | `gpt-4o` | `OPENAI_API_KEY` |
| `mixed` *(default)* | `claude-sonnet-4-6` | `gpt-4o` | Both API keys |

All models are accessed through LangChain's `BaseChatModel` interface with `.with_structured_output()` for guaranteed Pydantic-validated responses. Ollama uses the OpenAI-compatible `/v1` endpoint for consistent JSON mode support.

### Caching

LLM instances are memoised with `@lru_cache(maxsize=4)` keyed on `(role, model, provider)`. The cache is bypassed automatically if environment variables change between requests.

---

## Frontend Architecture

The frontend is a single-page React application that communicates exclusively with the FastAPI backend.

### Page routing

| Route | Component | Purpose |
|---|---|---|
| `/` | `Landing.tsx` | Dashboard — search bar, portfolio summary, holdings table, risk controls |
| `/loading` | `Loading.tsx` | Animated progress screen while analysis runs |
| `/results/:id` | `Results.tsx` | Full analysis: agent verdicts, traffic light, Agent Roles explainer |
| `/portfolio` | `PortfolioDashboard.tsx` | Sortable holdings table, portfolio analytics, sector allocation |
| `/history` | `HistoryPage.tsx` | Paginated list of past analyses |
| `/compare` | `ComparePage.tsx` | Side-by-side comparison of two analyses |
| `/login` | `LoginPage.tsx` | JWT authentication |
| `/register` | `RegisterPage.tsx` | Account creation |

### Key components

| Component | File | Role |
|---|---|---|
| `TrafficLight` | `components/TrafficLight.tsx` | Green / Yellow / Red consensus card |
| `PortfolioExposure` | `components/PortfolioExposure.tsx` | Hidden ETF concentration risk display |
| `VoiceInput` | `components/VoiceInput.tsx` | Microphone + waveform animation + text fallback |
| `CitationModal` | `components/CitationModal.tsx` | Source citation overlay for RAG-backed claims |
| `DynamicIntentBadge` | `components/DynamicIntentBadge.tsx` | Scenario label chip |
| `EvaluatedScenariosMatrix` | `components/EvaluatedScenariosMatrix.tsx` | Historical analog scoring grid |

### State management

- **`AnalysisContext`** — holds the active analysis result and controls the Loading → Results transition.
- **`AuthContext`** — manages JWT token, user session, and login/logout flow.
- **React Query** — all API calls; handles loading/error states and background refetching.

---

## Storage Layer

### SQLite — `database.py`

Persistent relational store for analysis history, user accounts, watchlists, and alerts. The schema is created with `CREATE TABLE IF NOT EXISTS` on startup — no migration tool required.

| Table | Purpose |
|---|---|
| `analyses` | Full serialised `AnalysisResponse` JSON keyed by UUID |
| `users` | Hashed credentials, display name, timestamps |
| `watchlists` | Named lists of tickers per user |
| `alerts` | Price and risk-change triggers per user |

### ChromaDB — `rag/store.py`

Ephemeral vector store (persisted to `backend/chroma_db/` by default). One collection per ticker, e.g. `NVDA_documents`.

- **Freshness check** — a collection is considered stale after 24 hours; `ingest_ticker()` re-fetches automatically.
- **Upsert** — documents are keyed by a deterministic ID (`{ticker}_{source}_{hash}`) to prevent duplicates across repeated runs.

---

## Data Models

All request/response contracts are Pydantic v2 models defined in `backend/schemas.py`.

### Analysis flow

```
AnalysisRequest
    │
    ▼
InvestmentState  (LangGraph shared state TypedDict)
    │
    ├── market_data: dict          (yfinance snapshot)
    ├── rag_context: dict[str,str] (per-agent RAG chunks)
    ├── bull_analysis: BullAnalysis
    ├── bear_analysis: BearAnalysis
    ├── strategist_analysis: StrategistAnalysis
    └── final_recommendation: JudgeRecommendation
              │
              ▼
        AnalysisResponse         (persisted to SQLite, returned to client)
```

### Confidence scoring

The Judge produces a 5-dimensional breakdown:

| Dimension | Meaning |
|---|---|
| `growth_potential` | Probability-weighted upside from bull case |
| `risk_level` | Severity of the bear case headwinds |
| `portfolio_fit` | Strategist's concentration and correlation assessment |
| `timing` | Entry point quality relative to current valuation |
| `execution_clarity` | Clarity and actionability of the entry strategy |

The `traffic_light_color` is derived from `confidence_overall`: ≥ 70 → green, < 45 → red, otherwise yellow.

### Evidence-weighted scoring

The `EvidenceAssessment` model scores each analyst on four dimensions (0–10 each, 40 max): data citations, calculation rigor, historical precedent, and counterargument strength. The Judge multiplies each analyst's conviction by their evidence score to produce an evidence-weighted recommendation.

---

## Configuration Reference

All settings are loaded from `backend/.env` via `python-dotenv`. See `.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `mixed` | `ollama` / `anthropic` / `openai` / `mixed` |
| `ANALYST_MODEL` | *(provider default)* | Model name for Bull, Bear, and Strategist agents |
| `JUDGE_MODEL` | *(provider default)* | Model name for the Judge agent |
| `LLM_TEMPERATURE` | `0.3` | Sampling temperature for all LLM calls |
| `ANTHROPIC_API_KEY` | — | Required when provider is `anthropic` or `mixed` |
| `OPENAI_API_KEY` | — | Required when provider is `openai` or `mixed` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `FMP_API_KEY` | — | Optional — enables FMP financials ingestion |
| `RAG_ENABLED` | `true` | Set to `false` to skip RAG entirely (faster, less grounded) |
| `JWT_SECRET_KEY` | — | Secret for signing user auth tokens |
| `PLAID_CLIENT_ID` | — | Optional — enables Plaid portfolio import |
| `PLAID_SECRET` | — | Optional — Plaid API secret |
