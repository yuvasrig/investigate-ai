import time
import uuid
from datetime import datetime, timezone

import config
config.validate()           # fail fast if required API keys are missing

from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from schemas import (
    AnalysisRequest, AnalysisResponse, TrafficLightResult, KellySizingResult,
    RegisterRequest, LoginRequest, TokenResponse, UserResponse,
    WatchlistCreate, WatchlistResponse, AlertCreate, AlertResponse,
    TaxHarvestRequest,
)
from workflow import get_workflow, InvestmentState
from agents.intent_router import route_intent
import json
import asyncio
from llm_factory import health_check as llm_health_check
from database import create_tables, get_db, User, Watchlist, Alert
from services.storage_service import save_analysis, get_analysis, list_analyses
from services.cache_service import get_cached, set_cached
from services.export_service import generate_pdf
from portfolio_analyzer import calculate_hidden_exposure, analyze_complete_portfolio
from sec_fetcher import get_latest_10k, get_section_text, SECTION_LABELS
from rag import store as rag_store
from demo_data import DEMO_PORTFOLIO
import voice_parser as vp
import plaid_service
import auth as auth_module
import tax_harvesting

# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=[])

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="InvestiGate API",
    description="Multi-agent AI investment advisor with flexible LLM providers",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round(time.time() - start, 3)
    print(
        f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC] "
        f"{request.method} {request.url.path} → {response.status_code} ({elapsed}s)"
    )
    return response


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    create_tables()


# ── Traffic-light helper ──────────────────────────────────────────────────────

def _compute_traffic_light(bull, bear, judge) -> TrafficLightResult:
    """
    Derive a traffic-light color from bull/bear conviction + judge action.

    bull.confidence and bear.confidence are on 0-10; we scale to 0-100.
    """
    bull_conviction = bull.confidence * 10.0   # 0-100
    bear_conviction = bear.confidence * 10.0   # 0-100
    conviction_diff = round(abs(bull_conviction - bear_conviction), 1)
    net_bullishness = bull_conviction - bear_conviction  # positive = bull winning

    # Determine key conflict
    if (
        bull.pe_ratio and bear.pe_ratio
        and abs(bull.pe_ratio - bear.pe_ratio) > 5
    ):
        key_conflict = {
            "topic": "Valuation",
            "bull_view": f"Fair P/E at {bull.pe_ratio:.1f}x",
            "bear_view": f"Overvalued, target P/E {bear.pe_ratio:.1f}x",
            "gap": round(abs(bull.pe_ratio - bear.pe_ratio), 1),
        }
    else:
        key_conflict = {
            "topic": "Price Target Range",
            "bull_view": f"${bull.best_case_target:,.0f} ({bull.best_case_timeline})",
            "bear_view": f"${bear.worst_case_target:,.0f} ({bear.worst_case_timeline})",
            "gap": round(abs(bull.best_case_target - bear.worst_case_target), 0),
        }

    # Color logic
    action = (judge.action or "hold").lower()
    if action == "sell" or net_bullishness < -20:
        color = "red"
        message = "Strong bearish signal — High risk"
    elif (
        net_bullishness > 20
        and conviction_diff > 20
        and action == "buy"
        and judge.confidence_overall >= 65
    ):
        color = "green"
        message = "Strong bullish consensus — Lower risk"
    else:
        color = "yellow"
        message = "Mixed signals — Proceed with caution"

    return TrafficLightResult(
        color=color,
        message=message,
        conviction_diff=conviction_diff,
        key_conflict=key_conflict,
        bull_recommendation="BUY",
        bear_recommendation="SELL",
        bull_conviction=bull_conviction,
        bear_conviction=bear_conviction,
    )


def _normalize_rag_summary(rag_summary):
    """Keep response shape stable across retriever/cache versions."""
    if not isinstance(rag_summary, dict):
        return rag_summary

    sec_count = rag_summary.get("sec")
    if sec_count is None:
        sec_count = rag_summary.get("sec_docs", 0)

    news_count = rag_summary.get("news")
    if news_count is None:
        news_count = rag_summary.get("news_docs", 0)

    return {
        "sec": sec_count,
        "news": news_count,
        "sec_docs": sec_count,
        "news_docs": news_count,
        "fmp_docs": rag_summary.get("fmp_docs", 0),
        "cache_hit": bool(rag_summary.get("cache_hit", False)),
        "disabled": bool(rag_summary.get("disabled", False)),
    }


def _sec_anchor_for_section(section: str) -> str:
    return {
        "business": "#item1",
        "risk_factors": "#item1a",
        "mda": "#item7",
        "financials": "#item8",
    }.get(section, "")


def _get_sec_filing_for_run(ticker: str):
    filing = get_latest_10k(ticker.upper())
    if filing is not None:
        return filing

    sec_docs = rag_store.source_metadatas(ticker.upper(), "sec_edgar", limit=50)
    if not sec_docs:
        return None

    preferred = next((doc for doc in sec_docs if doc.get("form") == "10-K"), sec_docs[0])
    filing_url = preferred.get("url", "")
    if not filing_url:
        return None

    section_urls = {
        "business": filing_url + _sec_anchor_for_section("business"),
        "risk_factors": filing_url + _sec_anchor_for_section("risk_factors"),
        "mda": filing_url + _sec_anchor_for_section("mda"),
        "financials": filing_url + _sec_anchor_for_section("financials"),
    }
    for doc in sec_docs:
        section = doc.get("section")
        url = doc.get("url")
        if section in section_urls and url:
            section_urls[section] = url + _sec_anchor_for_section(section)

    return {
        "cik": "",
        "ticker": ticker.upper(),
        "accession_number": "",
        "filing_date": "Cached SEC filing",
        "filing_url": filing_url,
        "viewer_url": filing_url,
        "section_urls": section_urls,
    }


def _get_news_links_for_run(ticker: str) -> list[dict]:
    news_docs = rag_store.source_metadatas(ticker.upper(), "news", limit=10)
    if not news_docs:
        return []

    seen: set[str] = set()
    links: list[dict] = []
    for doc in news_docs:
        url = (doc.get("url") or "").strip()
        title = (doc.get("title") or "").strip()
        if not url or not title or url in seen:
            continue
        seen.add(url)
        links.append({
            "title": title,
            "publisher": (doc.get("publisher") or "").strip(),
            "link": url,
        })
    return links


def _enrich_analysis_payload(result: dict, ticker: str) -> dict:
    updated = dict(result)

    if updated.get("sec_filing") is None:
        sec_filing = _get_sec_filing_for_run(ticker)
        if sec_filing is not None:
            updated["sec_filing"] = sec_filing

    market_data = dict(updated.get("market_data") or {})
    recent_news = market_data.get("recent_news")
    if not isinstance(recent_news, list) or len(recent_news) == 0:
        news_links = _get_news_links_for_run(ticker)
        if news_links:
            market_data["recent_news"] = news_links
            updated["market_data"] = market_data

    return updated


def _enrich_cached_analysis(result: dict, ticker: str) -> dict:
    return _enrich_analysis_payload(result, ticker)


def _with_user_query(result: dict, user_query: str | None) -> dict:
    """Preserve the original user question on fresh and cached responses."""
    if result.get("user_query"):
        return result
    if user_query and user_query.strip():
        return {**result, "user_query": user_query.strip()}
    return result


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "InvestiGate API",
        "version": "1.0.0",
        "provider": config.PROVIDER.value,
    }


@app.get("/health")
def health():
    llm_status = llm_health_check()
    ok = all(v == "ok" for v in llm_status.values())
    return {
        "status": "healthy" if ok else "degraded",
        "llm": llm_status,
    }


@app.get("/providers")
def providers():
    """Return the active LLM provider configuration (no secrets)."""
    return config.summary()


@app.post("/analyze/stream")
@limiter.limit("30/minute")
async def analyze_stream(request: Request, body: AnalysisRequest, db: Session = Depends(get_db)):
    """Streaming endpoint for real-time progress updates via SSE."""
    ticker = body.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
        
    portfolio_value = body.portfolio.get("total_value", 0.0)
    if portfolio_value <= 0:
        raise HTTPException(status_code=400, detail="Portfolio total_value must be positive")

    intent = route_intent(body.user_query or "", ticker)

    initial_state: InvestmentState = {
        "ticker": ticker,
        "amount": body.amount,
        "portfolio_value": portfolio_value,
        "risk_tolerance": body.risk_tolerance,
        "time_horizon": body.time_horizon,
        "analysis_action": body.analysis_action,
        "user_query": body.user_query,
        "scenarios": intent.scenarios,
        "market_data": None,
        "rag_context": None,
        "rag_summary": None,
        "bull_analysis": None,
        "bear_analysis": None,
        "strategist_analysis": None,
        "final_recommendation": None,
        "grounding_triggered": False,
    }

    async def event_generator():
        graph = get_workflow()
        start = time.time()
        final_state = None
        
        try:
            # Requires langchain-core >= 0.1.52 for astream_events v2
            async for event in graph.astream_events(initial_state, version="v2"):
                # Handle connection drop
                if await request.is_disconnected():
                    break
                    
                kind = event["event"]
                # We specifically look for when nodes FINISH to update progress bars
                if kind == "on_chain_end":
                    node_name = event["name"]
                    
                    if node_name == "fetch_data":
                        yield f"data: {json.dumps({'status': 'Data Fetched'})}\n\n"
                    elif node_name == "rag_ingest":
                        yield f"data: {json.dumps({'status': 'RAG Complete'})}\n\n"
                    elif node_name == "bull_node":
                        yield f"data: {json.dumps({'agent': 'bull', 'status': 'complete'})}\n\n"
                    elif node_name == "bear_node":
                        yield f"data: {json.dumps({'agent': 'bear', 'status': 'complete'})}\n\n"
                    elif node_name == "strategist_node":
                        yield f"data: {json.dumps({'agent': 'strategist', 'status': 'complete'})}\n\n"
                    elif node_name == "judge":
                        yield f"data: {json.dumps({'agent': 'judge', 'status': 'complete'})}\n\n"
                    elif node_name == "LangGraph":
                        # This happens when the entire graph finishes
                        final_state = event["data"]["output"]
                        
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        if not final_state:
            yield f"data: {json.dumps({'error': 'Graph did not return a final state'})}\n\n"
            return
            
        # Compile final response identical to old sync endpoint
        elapsed = round(time.time() - start, 2)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        analysis_id = str(uuid.uuid4())
        
        traffic_light = _compute_traffic_light(
            final_state["bull_analysis"],
            final_state["bear_analysis"],
            final_state["final_recommendation"],
        )
        
        portfolio_exposure = None
        holdings_input = body.portfolio_holdings
        if holdings_input:
            try:
                portfolio_exposure = calculate_hidden_exposure(
                    portfolio=[h.model_dump() for h in holdings_input],
                    target_ticker=ticker,
                    proposed_amount=body.amount,
                )
            except Exception:
                portfolio_exposure = None
                
        # Send FINAL result payload so frontend can navigate to /results
        try:
            response = AnalysisResponse(
                analysis_id=analysis_id,
                llm_provider=config.PROVIDER.value,
                ticker=ticker,
                user_query=body.user_query,
                bull_analysis=final_state["bull_analysis"],
                bear_analysis=final_state["bear_analysis"],
                strategist_analysis=final_state["strategist_analysis"],
                final_recommendation=final_state["final_recommendation"],
                intent=None,
                market_data=final_state.get("market_data"),
                rag_summary=_normalize_rag_summary(final_state.get("rag_summary")),
                traffic_light=traffic_light,
                portfolio_exposure=portfolio_exposure,
                sec_filing=_get_sec_filing_for_run(ticker),
                execution_time=elapsed,
                timestamp=timestamp,
            )
        except ValidationError as e:
            yield f"data: {json.dumps({'error': f'Validation error: {e.errors()}'})}\n\n"
            return
            
        response_dict = _enrich_analysis_payload(response.model_dump(), ticker)
        
        try:
            from database import SessionLocal
            with SessionLocal() as session:
                save_analysis(
                    session, analysis_id, response_dict,
                    amount=body.amount, portfolio_value=portfolio_value,
                    risk_tolerance=body.risk_tolerance, time_horizon=body.time_horizon
                )
        except Exception as e:
            print(f"Error saving stream analysis to memory: {e}")
            
        # Cache outcome
        portfolio_holdings_key = "none"
        if body.portfolio_holdings:
            portfolio_holdings_key = "-".join(sorted(f"{h.ticker}:{h.value}" for h in body.portfolio_holdings))
        
        set_cached(
            ticker, 
            body.amount, 
            portfolio_value, 
            body.risk_tolerance, 
            body.time_horizon, 
            body.user_query or "",
            body.analysis_action or "buy",
            portfolio_holdings_key,
            response_dict
        )
        
        # We must serialize to a dict, because SSE expects strings
        # "type": "result" tells the frontend this is the payload to render.
        yield f"data: {json.dumps({'type': 'result', 'payload': response_dict})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/analyze")
@limiter.limit("30/minute")
async def analyze_sync(request: Request, body: AnalysisRequest, db: Session = Depends(get_db)):
    """Synchronous (non-streaming) analysis endpoint. Returns full AnalysisResponse JSON."""
    ticker = body.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    portfolio_value = body.portfolio.get("total_value", 0.0)
    if portfolio_value <= 0:
        raise HTTPException(status_code=400, detail="Portfolio total_value must be positive")

    # Check cache first
    portfolio_holdings_key = "none"
    if body.portfolio_holdings:
        portfolio_holdings_key = "-".join(sorted(f"{h.ticker}:{h.value}" for h in body.portfolio_holdings))

    cached = get_cached(
        ticker, body.amount, portfolio_value,
        body.risk_tolerance, body.time_horizon,
        body.user_query or "", body.analysis_action or "buy",
        portfolio_holdings_key,
    )
    if cached:
        return _with_user_query(_enrich_cached_analysis(cached, ticker), body.user_query)

    intent = route_intent(body.user_query or "", ticker)

    initial_state: InvestmentState = {
        "ticker": ticker,
        "amount": body.amount,
        "portfolio_value": portfolio_value,
        "risk_tolerance": body.risk_tolerance,
        "time_horizon": body.time_horizon,
        "analysis_action": body.analysis_action,
        "user_query": body.user_query,
        "scenarios": intent.scenarios,
        "market_data": None,
        "rag_context": None,
        "rag_summary": None,
        "bull_analysis": None,
        "bear_analysis": None,
        "strategist_analysis": None,
        "final_recommendation": None,
        "grounding_triggered": False,
    }

    graph = get_workflow()
    start = time.time()

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not final_state:
        raise HTTPException(status_code=500, detail="Graph did not return a final state")

    elapsed = round(time.time() - start, 2)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    analysis_id = str(uuid.uuid4())

    traffic_light = _compute_traffic_light(
        final_state["bull_analysis"],
        final_state["bear_analysis"],
        final_state["final_recommendation"],
    )

    portfolio_exposure = None
    if body.portfolio_holdings:
        try:
            portfolio_exposure = calculate_hidden_exposure(
                portfolio=[h.model_dump() for h in body.portfolio_holdings],
                target_ticker=ticker,
                proposed_amount=body.amount,
            )
        except Exception:
            portfolio_exposure = None

    try:
        response = AnalysisResponse(
            analysis_id=analysis_id,
            llm_provider=config.PROVIDER.value,
            ticker=ticker,
            user_query=body.user_query,
            bull_analysis=final_state["bull_analysis"],
            bear_analysis=final_state["bear_analysis"],
            strategist_analysis=final_state["strategist_analysis"],
            final_recommendation=final_state["final_recommendation"],
            intent=None,
            market_data=final_state.get("market_data"),
            rag_summary=_normalize_rag_summary(final_state.get("rag_summary")),
            traffic_light=traffic_light,
            portfolio_exposure=portfolio_exposure,
            sec_filing=_get_sec_filing_for_run(ticker),
            execution_time=elapsed,
            timestamp=timestamp,
        )
    except ValidationError as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {e.errors()}")

    response_dict = _enrich_analysis_payload(response.model_dump(), ticker)

    try:
        save_analysis(
            db, analysis_id, response_dict,
            amount=body.amount, portfolio_value=portfolio_value,
            risk_tolerance=body.risk_tolerance, time_horizon=body.time_horizon,
        )
    except Exception as e:
        print(f"Error saving analysis to memory: {e}")

    set_cached(
        ticker, body.amount, portfolio_value,
        body.risk_tolerance, body.time_horizon,
        body.user_query or "", body.analysis_action or "buy",
        portfolio_holdings_key,
        response_dict,
    )

    return response_dict


@app.get("/analysis/{analysis_id}")
def get_analysis_by_id(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieve a previously-run analysis by UUID."""
    result = get_analysis(db, analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result


@app.get("/history")
def history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Return a paginated list of past analyses (most recent first)."""
    return list_analyses(db, limit=min(limit, 100), offset=offset)


@app.post("/compare")
def compare(analysis_ids: list[str], db: Session = Depends(get_db)):
    """Return full results for multiple analysis IDs side-by-side."""
    if len(analysis_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 analysis IDs")
    if len(analysis_ids) > 5:
        raise HTTPException(status_code=400, detail="Cannot compare more than 5 analyses at once")

    results = {}
    missing = []
    for aid in analysis_ids:
        data = get_analysis(db, aid)
        if data is None:
            missing.append(aid)
        else:
            results[aid] = data

    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis IDs not found: {missing}",
        )

    return results


@app.get("/export/pdf/{analysis_id}")
def export_pdf(analysis_id: str, db: Session = Depends(get_db)):
    """Generate and return a PDF report for a stored analysis."""
    analysis = get_analysis(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        pdf_bytes = generate_pdf(analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    ticker = str(analysis.get("ticker", "analysis")).upper()
    filename = f"InvestiGate_{ticker}_{analysis_id[:8]}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── v2 endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/voice/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)):
    """
    Transcribe a voice recording and extract investment intent.
    Requires OPENAI_API_KEY.
    """
    audio_bytes = await audio.read()
    try:
        transcript = vp.transcribe_audio(audio_bytes, filename=audio.filename or "recording.wav")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    intent = vp.parse_investment_intent(transcript)
    return {"transcript": transcript, "intent": intent}


@app.post("/api/voice/parse-text")
def parse_text_intent(body: dict):
    """
    Parse investment intent from a plain-text query (no audio).
    Works without OPENAI_API_KEY via regex fallback.
    """
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text field required")
    intent = vp.parse_investment_intent(text)
    return {"intent": intent}


@app.get("/api/portfolio/demo")
def get_demo_portfolio():
    """Return the canned demo portfolio for testing / demo video."""
    return DEMO_PORTFOLIO


@app.post("/api/portfolio/analyze-complete")
def portfolio_analyze_complete(body: dict):
    """
    Tier-1 portfolio analysis: categorise every holding into long-term core,
    growth positions, concentration risks, and missing protections.

    Body: { "holdings": [...], "total_value": 80000 }
    Returns the full PortfolioReport structure consumed by PortfolioReportCard.
    """
    try:
        report = analyze_complete_portfolio(body)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portfolio/demo/analyze")
def get_demo_portfolio_analysis():
    """Convenience endpoint — runs Tier-1 analysis on the built-in demo portfolio."""
    try:
        return analyze_complete_portfolio(DEMO_PORTFOLIO)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portfolio/exposure")
def portfolio_exposure_endpoint(body: dict):
    """
    Calculate hidden exposure for a ticker given a list of holdings.

    Body: {
      "ticker": "NVDA",
      "amount": 5000,
      "holdings": [{"ticker": "SPY", "value": 15000}, ...]
    }
    """
    ticker = body.get("ticker", "").upper()
    amount = float(body.get("amount", 0))
    holdings = body.get("holdings", [])
    if not ticker or not holdings:
        raise HTTPException(status_code=400, detail="ticker and holdings are required")
    exposure = calculate_hidden_exposure(holdings, ticker, amount)
    return exposure


# ── Plaid endpoints ───────────────────────────────────────────────────────────

@app.post("/api/plaid/link-token")
def plaid_link_token(body: dict):
    """
    Request a Plaid Link token for the frontend to open the Plaid modal.
    Body: { "user_id": "<your-user-id>" }   (optional — defaults to "anonymous")
    """
    if not plaid_service.is_available():
        raise HTTPException(
            status_code=501,
            detail="Plaid is not configured. Set PLAID_CLIENT_ID and PLAID_SECRET in .env."
        )
    user_id = body.get("user_id", "anonymous")
    try:
        link_token = plaid_service.create_link_token(user_id)
        return {"link_token": link_token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plaid/exchange-token")
def plaid_exchange_token(body: dict):
    """
    Exchange the short-lived public_token (from Plaid Link onSuccess) for an
    access_token and immediately return the investment holdings.
    Body: { "public_token": "<token-from-frontend>" }
    """
    if not plaid_service.is_available():
        raise HTTPException(
            status_code=501,
            detail="Plaid is not configured. Set PLAID_CLIENT_ID and PLAID_SECRET in .env."
        )
    public_token = body.get("public_token", "")
    if not public_token:
        raise HTTPException(status_code=400, detail="public_token is required")
    try:
        access_token = plaid_service.exchange_public_token(public_token)
        portfolio = plaid_service.get_portfolio_summary(access_token)
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=UserResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Returns the created user profile."""
    try:
        user = auth_module.register_user(db, body.email, body.password, body.name or "")
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return a JWT bearer token."""
    user = auth_module.authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth_module.create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
        ),
    )


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(auth_module.require_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.created_at,
    )


# ── Watchlist endpoints ────────────────────────────────────────────────────────

@app.post("/api/watchlist", response_model=WatchlistResponse)
def create_watchlist(
    body: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.require_user),
):
    """Create a new watchlist for the authenticated user."""
    import uuid as _uuid
    from datetime import datetime, timezone as _tz
    wl = Watchlist(
        id=str(_uuid.uuid4()),
        user_id=current_user.id,
        name=body.name,
        tickers=body.tickers,
        notes=body.notes,
        created_at=datetime.now(_tz.utc),
    )
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return wl


@app.get("/api/watchlist", response_model=list[WatchlistResponse])
def list_watchlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.require_user),
):
    """Return all watchlists for the authenticated user."""
    return db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()


@app.delete("/api/watchlist/{watchlist_id}")
def delete_watchlist(
    watchlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.require_user),
):
    """Delete a watchlist owned by the authenticated user."""
    wl = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id,
    ).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    db.delete(wl)
    db.commit()
    return {"deleted": watchlist_id}


# ── Alert endpoints ────────────────────────────────────────────────────────────

@app.post("/api/alerts", response_model=AlertResponse)
def create_alert(
    body: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.require_user),
):
    """Create a price / risk alert for the authenticated user."""
    import uuid as _uuid
    from datetime import datetime, timezone as _tz
    alert = Alert(
        id=str(_uuid.uuid4()),
        user_id=current_user.id,
        ticker=body.ticker.upper(),
        alert_type=body.alert_type,
        threshold=body.threshold,
        message=body.message,
        is_active=True,
        created_at=datetime.now(_tz.utc),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@app.get("/api/alerts", response_model=list[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.require_user),
):
    """Return all active alerts for the authenticated user."""
    return db.query(Alert).filter(Alert.user_id == current_user.id).all()


@app.delete("/api/alerts/{alert_id}")
def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.require_user),
):
    """Delete an alert owned by the authenticated user."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    return {"deleted": alert_id}


# ── Tax-loss harvesting endpoint ───────────────────────────────────────────────

@app.post("/api/tax-harvest")
def tax_harvest(body: TaxHarvestRequest):
    """
    Analyse a list of holdings for tax-loss harvesting opportunities.

    Body: { "holdings": [{"ticker": "NVDA", "value": 10000, "cost_basis": 12000, ...}] }
    """
    holdings_dicts = [h.model_dump() for h in body.holdings]
    result = tax_harvesting.analyse_tax_loss_opportunities(
        holdings_dicts, tax_year=body.tax_year
    )
    return result


# ── Kelly standalone endpoint ──────────────────────────────────────────────────

@app.post("/api/kelly")
def kelly_endpoint(body: dict):
    """
    Compute Kelly Criterion position sizing given bull/bear conviction + prices.

    Body: {
      "bull_conviction": 0.7,       # 0-1
      "bear_conviction": 0.3,       # 0-1
      "bull_target": 200.0,         # price target
      "bear_target": 80.0,          # price target
      "current_price": 130.0,
      "proposed_amount": 5000,
      "portfolio_value": 100000,
      "strategist_cap": 15000,      # optional
      "correlation": 0.65           # optional
    }
    """
    from kelly import kelly_position_size
    try:
        result = kelly_position_size(
            bull_conviction=float(body["bull_conviction"]),
            bear_conviction=float(body["bear_conviction"]),
            bull_target=float(body["bull_target"]),
            bear_target=float(body["bear_target"]),
            current_price=float(body["current_price"]),
            proposed_amount=float(body["proposed_amount"]),
            portfolio_value=float(body["portfolio_value"]),
            strategist_cap=float(body.get("strategist_cap", float(body["portfolio_value"]) * 0.15)),
            correlation=float(body.get("correlation", 0.65)),
        )
        return KellySizingResult(**result).model_dump()
    except (KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Missing or invalid field: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── SEC EDGAR endpoints ───────────────────────────────────────────────────────

@app.get("/api/sec/{ticker}/filing")
def sec_filing(ticker: str):
    """Return 10-K filing metadata for a ticker (CIK, accession number, section URLs)."""
    result = get_latest_10k(ticker.upper())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No 10-K filing found for {ticker.upper()}")
    return result


@app.get("/api/sec/{ticker}/excerpt")
def sec_excerpt(ticker: str, section: str = "business"):
    """Return a plain-text excerpt from the specified 10-K section."""
    valid_sections = list(SECTION_LABELS.keys())
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section '{section}'. Must be one of: {valid_sections}",
        )
    filing = get_latest_10k(ticker.upper())
    if filing is None:
        raise HTTPException(status_code=404, detail=f"No 10-K filing found for {ticker.upper()}")

    text = get_section_text(ticker.upper(), section)
    if text is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not extract section '{section}' from 10-K for {ticker.upper()}",
        )
    return {
        "ticker": ticker.upper(),
        "section": section,
        "section_label": SECTION_LABELS.get(section, section),
        "filing_date": filing["filing_date"],
        "filing_url": filing["filing_url"],
        "text": text,
    }


# ── Dev entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
