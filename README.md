# InvestiGate — The Anti-FOMO Advisor

> Three AI analysts debate every investment — **Bull vs Bear vs Strategist** — so you don't have to FOMO into bad trades.

InvestiGate is a multi-agent AI investment analysis platform. Given a stock ticker and investment amount it runs a structured debate between a Bull analyst, a Bear analyst, and a Portfolio Strategist, then delivers a Judge verdict with confidence scores, a traffic-light consensus signal, and hidden ETF-exposure warnings.

---

## Features

| Feature | Description |
|---|---|
| **Multi-agent debate** | Bull, Bear, and Strategist agents independently analyse the stock using live market data + SEC filings + news |
| **Judge verdict** | Final Buy / Hold / Sell recommendation with confidence breakdown |
| **Traffic Light** | Green / Yellow / Red consensus signal from conviction scores |
| **Portfolio Exposure** | Detects hidden concentration risk through ETF holdings (SPY, QQQ, VOO, VTI…) |
| **Dashboard Homepage** | Search bar across top + 3-column portfolio dashboard (value card, portfolio analysis, risk controls) |
| **Agent Role Explainers** | Dedicated Agent Roles view in Results + quick access on startup page (`?` icon) |
| **Sortable Holdings Table** | Portfolio holdings can be sorted by any attribute in ascending/descending order |
| **Realistic Portfolio Trend** | Portfolio value-over-time includes natural variability (ups and downs) |
| **Voice Input** | Speak your idea ("Invest $5,000 in NVIDIA") — auto-fills the form via Whisper + regex fallback |
| **PDF / JSON export** | Download the full analysis report |
| **History & Compare** | Browse past analyses and compare two stocks side-by-side |
| **Fully local** | Runs 100% offline with Ollama — no API keys required |

---

## Quick Start

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.10 + | [python.org](https://python.org) |
| Node.js | 18 + | [nodejs.org](https://nodejs.org) |
| Ollama | latest | [ollama.com](https://ollama.com) |

### 1 — Clone the repo

```bash
git clone https://github.com/yuvasrig/investigate-ai.git
cd investigate-ai
```

### 2 — Start Ollama

```bash
ollama serve          # start the local LLM server
```

> `start.sh` will auto-pull the required models on first run.

### 3 — Run the app

```bash
./start.sh
```

That's it. The script handles everything else automatically.

---

## `start.sh` Reference

```
./start.sh [OPTIONS]
```

| Option | Description |
|---|---|
| *(none)* | Normal start — skip steps that are already done |
| `--fresh` | Wipe `backend/.venv` and `node_modules`, reinstall from scratch |
| `--help` | Print usage and exit |

### What the script does

```
1/5  Environment      copies .env.example → backend/.env (Ollama defaults)
2/5  Ollama           pings localhost:11434, auto-pulls llama3.1 + nomic-embed-text
3/5  Python           creates backend/.venv, pip install -r requirements.txt
4/5  Node             npm install (skipped if node_modules exists)
5/5  Servers          uvicorn :8000 + Vite :8080 — colour-coded logs in one terminal
```

Press **Ctrl+C** to cleanly shut down both servers.

### URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:8080 |
| Backend API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |

---

## Manual Setup

If you prefer to run the servers separately:

```bash
# 1. Copy env
cp .env.example backend/.env

# 2. Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --reload --app-dir .

# 3. Frontend (new terminal, from project root)
npm install
npm run dev
```

---

## LLM Provider Configuration

Edit `backend/.env` to switch providers:

```bash
# ── Use local Ollama (default, no API key needed) ──
LLM_PROVIDER=ollama
ANALYST_MODEL=llama3.1
JUDGE_MODEL=llama3.1
EMBEDDING_MODEL=nomic-embed-text

# ── Use Anthropic Claude ──
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...

# ── Use OpenAI GPT-4o ──
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# ── Mixed: Claude for analysts, GPT-4o for judge ──
# LLM_PROVIDER=mixed
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
```

> **Voice input** uses Whisper + GPT-4o-mini when `OPENAI_API_KEY` is set.
> Without it, voice input falls back to local regex parsing — still works for common phrases.

See [`.env.example`](.env.example) for the full list of options.

---

## Project Structure

```
investigate-ai/
├── start.sh                  # one-command startup script
├── .env.example              # all config options with Ollama defaults
│
├── backend/
│   ├── server.py             # FastAPI app — all HTTP endpoints
│   ├── agents/               # Bull / Bear / Strategist / Judge agents (package)
│   ├── workflow.py           # LangGraph orchestration
│   ├── schemas.py            # Pydantic request/response models
│   ├── config.py             # env-var configuration
│   ├── llm_factory.py        # provider-agnostic LLM client factory
│   ├── portfolio_analyzer.py # ETF hidden-exposure calculator
│   ├── voice_parser.py       # Whisper + regex intent parser
│   ├── demo_data.py          # demo portfolio (SPY / QQQ / VOO)
│   ├── database.py           # SQLite persistence (analysis history)
│   ├── services/
│   │   ├── export_service.py # PDF + JSON report generation
│   │   ├── storage_service.py
│   │   └── cache_service.py
│   └── rag/                  # SEC EDGAR + news retrieval
│
└── src/
    ├── pages/
    │   ├── Landing.tsx        # dashboard homepage + top search + holdings actions
    │   ├── Loading.tsx        # analysis progress screen
    │   ├── Results.tsx        # full results + Agent Roles tab
    │   ├── PortfolioDashboard.tsx # sortable full holdings + portfolio analytics
    │   ├── HistoryPage.tsx    # past analyses
    │   └── ComparePage.tsx    # side-by-side comparison
    ├── components/
    │   ├── TrafficLight.tsx   # Green/Yellow/Red consensus card
    │   ├── PortfolioExposure.tsx  # hidden ETF exposure card
    │   └── VoiceInput.tsx     # mic + waveform + text fallback
    └── services/
        └── api.ts             # typed API client
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/analyze` | Run a full multi-agent analysis |
| `GET` | `/analysis/{id}` | Fetch a saved analysis by ID |
| `GET` | `/history` | List past analyses |
| `POST` | `/compare` | Compare two analyses side-by-side |
| `GET` | `/export/pdf/{id}` | Download PDF report |
| `GET` | `/export/json/{id}` | Download JSON report |
| `POST` | `/api/voice/transcribe` | Transcribe audio → intent |
| `POST` | `/api/voice/parse-text` | Parse text → investment intent |
| `GET` | `/api/portfolio/demo` | Get demo portfolio |
| `POST` | `/api/portfolio/exposure` | Calculate hidden ETF exposure |
| `GET` | `/providers` | Show active LLM provider config |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Tech Stack

**Backend** — Python, FastAPI, LangGraph, LangChain, Ollama / OpenAI / Anthropic, ChromaDB, SQLite, fpdf2

**Frontend** — React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router

---

## License

MIT
