import time
from datetime import datetime, timezone

import config
config.validate()           # fail fast if required API keys are missing

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import AnalysisRequest, AnalysisResponse
from workflow import run_analysis
from llm_factory import health_check as llm_health_check

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="InvestiGate API",
    description="Multi-agent AI investment advisor with flexible LLM providers",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
def analyze(request: AnalysisRequest):
    ticker = request.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    portfolio_value = request.portfolio.get("total_value", 0.0)
    if portfolio_value <= 0:
        raise HTTPException(status_code=400, detail="Portfolio total_value must be positive")

    start = time.time()

    try:
        result = run_analysis(
            ticker=ticker,
            amount=request.amount,
            portfolio_value=portfolio_value,
            risk_tolerance=request.risk_tolerance,
            time_horizon=request.time_horizon,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    elapsed = round(time.time() - start, 2)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return AnalysisResponse(
        ticker=ticker,
        bull_analysis=result["bull_analysis"],
        bear_analysis=result["bear_analysis"],
        strategist_analysis=result["strategist_analysis"],
        final_recommendation=result["final_recommendation"],
        market_data=result.get("market_data"),
        rag_summary=result.get("rag_summary"),
        execution_time=elapsed,
        timestamp=timestamp,
    )


# ── Dev entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
