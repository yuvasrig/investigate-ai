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

from schemas import AnalysisRequest, AnalysisResponse, TrafficLightResult
from workflow import run_analysis
from llm_factory import health_check as llm_health_check
from database import create_tables, get_db
from services.storage_service import save_analysis, get_analysis, list_analyses
from services.cache_service import get_cached, set_cached
from services.export_service import generate_pdf
from portfolio_analyzer import calculate_hidden_exposure
from demo_data import DEMO_PORTFOLIO
import voice_parser as vp

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


@app.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("10/minute")
def analyze(request: Request, body: AnalysisRequest, db: Session = Depends(get_db)):
    ticker = body.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    portfolio_value = body.portfolio.get("total_value", 0.0)
    if portfolio_value <= 0:
        raise HTTPException(status_code=400, detail="Portfolio total_value must be positive")

    # ── Cache check ───────────────────────────────────────────────────────────
    cached = get_cached(
        ticker,
        body.amount,
        portfolio_value,
        body.risk_tolerance,
        body.time_horizon,
    )
    if cached:
        return AnalysisResponse(**cached)

    start = time.time()

    try:
        result = run_analysis(
            ticker=ticker,
            amount=body.amount,
            portfolio_value=portfolio_value,
            risk_tolerance=body.risk_tolerance,
            time_horizon=body.time_horizon,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    elapsed = round(time.time() - start, 2)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    analysis_id = str(uuid.uuid4())

    # ── Traffic light ─────────────────────────────────────────────────────────
    traffic_light = _compute_traffic_light(
        result["bull_analysis"],
        result["bear_analysis"],
        result["final_recommendation"],
    )

    # ── Portfolio hidden exposure ──────────────────────────────────────────────
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

    try:
        response = AnalysisResponse(
            analysis_id=analysis_id,
            llm_provider=config.PROVIDER.value,
            ticker=ticker,
            bull_analysis=result["bull_analysis"],
            bear_analysis=result["bear_analysis"],
            strategist_analysis=result["strategist_analysis"],
            final_recommendation=result["final_recommendation"],
            market_data=result.get("market_data"),
            rag_summary=result.get("rag_summary"),
            traffic_light=traffic_light,
            portfolio_exposure=portfolio_exposure,
            execution_time=elapsed,
            timestamp=timestamp,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis produced invalid model output: {e.errors()}",
        )

    response_dict = response.model_dump()

    # ── Persist to DB ─────────────────────────────────────────────────────────
    try:
        save_analysis(
            db,
            analysis_id,
            response_dict,
            amount=body.amount,
            portfolio_value=portfolio_value,
            risk_tolerance=body.risk_tolerance,
            time_horizon=body.time_horizon,
        )
    except Exception:
        pass  # non-fatal — analysis still returned to client

    # ── Cache result ──────────────────────────────────────────────────────────
    set_cached(
        ticker,
        body.amount,
        portfolio_value,
        body.risk_tolerance,
        body.time_horizon,
        response_dict,
    )

    return response


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


# ── Dev entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
