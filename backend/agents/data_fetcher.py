"""
Shared data-fetching utilities for professional agents.

Provides:
  - fetch_peer_data()          → peer company valuation + growth metrics
  - fetch_historical_patterns() → 5-year price history, volatility, drawdowns
  - fetch_competitive_threats() → news-based competitive intel
  - fetch_portfolio_metrics()  → concentration, sector allocation, correlation
"""

import re
from typing import Optional
import yfinance as yf

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ── Peer group map ─────────────────────────────────────────────────────────────

PEER_MAP: dict[str, list[str]] = {
    "NVDA": ["AMD", "INTC", "QCOM", "AVGO"],
    "TSLA": ["GM",  "F",   "RIVN", "TM"],
    "AAPL": ["MSFT","GOOGL","AMZN","META"],
    "MSFT": ["AAPL","GOOGL","AMZN","ORCL"],
    "GOOGL":["MSFT","META","AMZN","SNAP"],
    "META": ["GOOGL","SNAP","PINS","TTD"],
    "AMZN": ["MSFT","GOOGL","WMT","SHOP"],
    "AMD":  ["NVDA","INTC","QCOM","MRVL"],
    "INTC": ["NVDA","AMD", "QCOM","TSM"],
    "NFLX": ["DIS", "PARA","WBD", "SPOT"],
    "CRM":  ["NOW", "SAP", "ORCL","WDAY"],
    "NOW":  ["CRM", "SAP", "WDAY","ORCL"],
    "UBER": ["LYFT","ABNB","DASH","BKNG"],
    "COIN": ["MSTR","HOOD","MARA","RIOT"],
}

# Sector lookup for portfolio metrics
SECTOR_MAP: dict[str, str] = {
    "NVDA": "Technology", "AMD": "Technology", "INTC": "Technology",
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "META": "Technology", "AMZN": "Technology", "CRM": "Technology",
    "NOW": "Technology",  "ORCL": "Technology", "QCOM": "Technology",
    "AVGO": "Technology", "MRVL": "Technology",
    "TSLA": "Consumer Cyclical", "GM": "Consumer Cyclical", "F": "Consumer Cyclical",
    "RIVN": "Consumer Cyclical", "TM": "Consumer Cyclical",
    "NFLX": "Communication", "DIS": "Communication", "SNAP": "Communication",
    "META": "Communication", "GOOGL": "Communication",
    "UBER": "Consumer Cyclical", "LYFT": "Consumer Cyclical", "ABNB": "Consumer Cyclical",
    "COIN": "Financial", "MSTR": "Financial", "HOOD": "Financial",
    "SPY": "Diversified", "VOO": "Diversified", "VTI": "Diversified", "IVV": "Diversified",
    "QQQ": "Technology-Heavy",
    "VWO": "International", "VEA": "International", "VXUS": "International",
    "BND": "Bonds", "AGG": "Bonds", "TLT": "Bonds",
}


# ── Peer data ──────────────────────────────────────────────────────────────────

def fetch_peer_data(ticker: str) -> dict:
    """
    Fetch valuation + growth metrics for the peer group of ticker.
    Returns {"peers": [...], "median_metrics": {...}}.
    Falls back gracefully if yfinance is rate-limited.
    """
    peers = PEER_MAP.get(ticker.upper(), [])
    if not peers:
        return {"peers": [], "median_metrics": {}}

    peer_rows = []
    for p in peers:
        try:
            info = yf.Ticker(p).info
            rg = info.get("revenueGrowth") or 0
            gm = info.get("grossMargins") or 0
            om = info.get("operatingMargins") or 0
            roe = info.get("returnOnEquity") or 0
            peer_rows.append({
                "ticker": p,
                "name": info.get("longName", p),
                "forward_pe": round(info.get("forwardPE") or 0, 1),
                "trailing_pe": round(info.get("trailingPE") or 0, 1),
                "peg_ratio": round(info.get("pegRatio") or 0, 2),
                "revenue_growth_pct": round(rg * 100, 1),
                "gross_margin_pct": round(gm * 100, 1),
                "operating_margin_pct": round(om * 100, 1),
                "roe_pct": round(roe * 100, 1),
                "market_cap_b": round((info.get("marketCap") or 0) / 1e9, 1),
            })
        except Exception:
            continue

    if not peer_rows:
        return {"peers": [], "median_metrics": {}}

    def _med(key: str) -> float:
        vals = [r[key] for r in peer_rows if r[key] > 0]
        if not vals:
            return 0.0
        if _HAS_NUMPY:
            return round(float(np.median(vals)), 1)
        vals.sort()
        mid = len(vals) // 2
        return round(vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2, 1)

    return {
        "peers": peer_rows,
        "median_metrics": {
            "median_forward_pe": _med("forward_pe"),
            "median_peg": _med("peg_ratio"),
            "median_revenue_growth_pct": _med("revenue_growth_pct"),
            "median_gross_margin_pct": _med("gross_margin_pct"),
            "median_roe_pct": _med("roe_pct"),
        },
    }


# ── Historical patterns ────────────────────────────────────────────────────────

def fetch_historical_patterns(ticker: str) -> dict:
    """
    5-year price history: high/low, current drawdown, annualised volatility.
    """
    try:
        hist = yf.Ticker(ticker).history(period="5y")
        if hist.empty:
            return {}

        close = hist["Close"]
        current = float(close.iloc[-1])
        high_5y = float(close.max())
        low_5y = float(close.min())

        pct_from_high = round((current / high_5y - 1) * 100, 1)
        pct_from_low  = round((current / low_5y  - 1) * 100, 1)

        # Annualised volatility (std of daily returns × √252)
        daily_ret = close.pct_change().dropna()
        if _HAS_NUMPY:
            vol = round(float(np.std(daily_ret) * np.sqrt(252) * 100), 1)
        else:
            import statistics, math
            vol = round(statistics.stdev(daily_ret) * math.sqrt(252) * 100, 1)

        # 1-year return
        one_yr_ago = close.iloc[-252] if len(close) >= 252 else close.iloc[0]
        ret_1y = round((current / float(one_yr_ago) - 1) * 100, 1)

        return {
            "current_price": round(current, 2),
            "high_5y": round(high_5y, 2),
            "low_5y": round(low_5y, 2),
            "pct_from_5y_high": pct_from_high,
            "pct_from_5y_low": pct_from_low,
            "volatility_annualised_pct": vol,
            "return_1y_pct": ret_1y,
        }
    except Exception:
        return {}


# ── Competitive threats (news headlines) ──────────────────────────────────────

def fetch_competitive_threats(ticker: str, market_data: dict) -> str:
    """
    Pull competitive / negative headlines from the market_data news list.
    Returns a plain-text summary (max ~500 chars).
    """
    news = market_data.get("recent_news") or []
    keywords = ["competi", "threat", "rival", "market share", "losing",
                "downgrade", "risk", "concern", "headwind", "pressure", "decline"]
    hits = []
    for item in news:
        title = (item.get("title") or "").strip()
        if any(k in title.lower() for k in keywords):
            hits.append(title)
    if hits:
        return " | ".join(hits[:4])
    # Fallback: return first 3 headlines
    return " | ".join([(n.get("title") or "") for n in news[:3]]) or "No recent headlines."


# ── Earnings highlights (for Bull agent) ──────────────────────────────────────

def fetch_earnings_highlights(ticker: str, market_data: dict) -> str:
    """
    Pull recent earnings-related headlines for the Bull agent to cite.

    Strategy (in order of availability):
      1. Filter market_data news for earnings / revenue / guidance keywords.
      2. Supplement with yfinance news if market_data has fewer than 2 hits.
      3. Fall back to analyst consensus from market_data fields.

    Returns a plain-text string ready to be embedded in the Bull prompt.
    """
    earnings_keywords = [
        "earnings", "revenue", "beat", "guidance", "forecast", "outlook",
        "quarter", "eps", "profit", "sales", "margin", "raised", "raised guidance",
        "record", "growth", "results", "reported", "exceeds", "surpasses",
    ]

    hits: list[str] = []

    # 1. Scan market_data news
    news = market_data.get("recent_news") or []
    for item in news:
        title = (item.get("title") or "").strip()
        if any(k in title.lower() for k in earnings_keywords):
            hits.append(title)

    # 2. Supplement with raw yfinance news if thin coverage
    if len(hits) < 2:
        try:
            extra_news = yf.Ticker(ticker).news or []
            for item in extra_news[:10]:
                title = (item.get("title") or "").strip()
                if title and title not in hits and any(k in title.lower() for k in earnings_keywords):
                    hits.append(title)
                if len(hits) >= 5:
                    break
        except Exception:
            pass

    if hits:
        return " | ".join(hits[:5])

    # 3. Graceful fallback: synthesise from analyst consensus fields
    n_analysts = int(market_data.get("numberOfAnalystOpinions") or 0)
    mean_target = market_data.get("targetMeanPrice") or 0
    rec_key = (market_data.get("recommendationKey") or "N/A").upper()
    rev_growth = (market_data.get("revenueGrowth") or 0) * 100
    earn_growth = (market_data.get("earningsGrowth") or 0) * 100

    return (
        f"Analyst consensus ({n_analysts} analysts): {rec_key}, "
        f"mean target ${mean_target:.2f}. "
        f"Revenue growth {rev_growth:+.1f}% YoY, earnings growth {earn_growth:+.1f}% YoY. "
        "No specific earnings headlines available."
    )


# ── Portfolio metrics ──────────────────────────────────────────────────────────

ETF_WEIGHTS: dict[str, dict[str, float]] = {
    "SPY": {"NVDA": 0.068, "AAPL": 0.070, "MSFT": 0.065, "AMZN": 0.038, "TSLA": 0.024,
            "GOOGL": 0.035, "META": 0.026, "AVGO": 0.020},
    "QQQ": {"NVDA": 0.099, "AAPL": 0.083, "MSFT": 0.082, "AMZN": 0.054, "TSLA": 0.039,
            "GOOGL": 0.051, "META": 0.045, "AVGO": 0.032},
    "VOO": {"NVDA": 0.068, "AAPL": 0.070, "MSFT": 0.065, "AMZN": 0.038, "TSLA": 0.024,
            "GOOGL": 0.035, "META": 0.026, "AVGO": 0.020},
    "VTI": {"NVDA": 0.054, "AAPL": 0.056, "MSFT": 0.052, "AMZN": 0.030, "TSLA": 0.019,
            "GOOGL": 0.028, "META": 0.020, "AVGO": 0.016},
    "IVV": {"NVDA": 0.068, "AAPL": 0.070, "MSFT": 0.065, "AMZN": 0.038, "TSLA": 0.024},
}


def fetch_portfolio_metrics(holdings: list[dict], ticker: str, proposed_amount: float) -> dict:
    """
    Full portfolio metrics:
      - concentration (top 1/3/5)
      - sector allocation
      - hidden exposure to ticker via ETFs
      - correlation estimate (same-sector = 0.80, diversified = 0.65, other = 0.55)
      - rebalancing suggestions

    holdings: [{"ticker": str, "value": float, "name": str?}]
    """
    if not holdings:
        return {}

    total_value = sum(h.get("value", 0) for h in holdings)
    if total_value <= 0:
        return {}

    # Sector allocation
    sector_alloc: dict[str, float] = {}
    for h in holdings:
        sector = SECTOR_MAP.get(h["ticker"].upper(), "Other")
        sector_alloc[sector] = sector_alloc.get(sector, 0) + h.get("value", 0)
    sector_pct = {s: round(v / total_value * 100, 1) for s, v in sector_alloc.items()}

    # Concentration
    vals = sorted([h.get("value", 0) for h in holdings], reverse=True)
    top1 = round(vals[0] / total_value * 100, 1) if vals else 0
    top3 = round(sum(vals[:3]) / total_value * 100, 1) if len(vals) >= 3 else 0
    top5 = round(sum(vals[:5]) / total_value * 100, 1) if len(vals) >= 5 else 0

    # Hidden exposure to ticker via ETFs
    ticker_up = ticker.upper()
    direct = sum(h.get("value", 0) for h in holdings if h["ticker"].upper() == ticker_up)
    indirect_rows = []
    total_indirect = 0.0
    for h in holdings:
        etf = h["ticker"].upper()
        if etf in ETF_WEIGHTS and ticker_up in ETF_WEIGHTS[etf]:
            w = ETF_WEIGHTS[etf][ticker_up]
            amt = h.get("value", 0) * w
            indirect_rows.append({"etf": etf, "amount": round(amt, 0), "weight_pct": round(w * 100, 1)})
            total_indirect += amt

    total_current = direct + total_indirect
    new_total = total_value + proposed_amount
    new_exposure = total_current + proposed_amount
    current_pct = round(total_current / total_value * 100, 1) if total_value else 0
    proposed_pct = round(new_exposure / new_total * 100, 1) if new_total else 0
    exceeds_limit = proposed_pct > 15

    # Correlation estimate
    new_sector = SECTOR_MAP.get(ticker_up, "Other")
    weighted_corr = 0.0
    for h in holdings:
        s = SECTOR_MAP.get(h["ticker"].upper(), "Other")
        corr = 0.80 if s == new_sector else 0.65 if "Diversified" in s else 0.55
        weighted_corr += corr * h.get("value", 0)
    avg_corr = round(weighted_corr / total_value, 2) if total_value else 0.65
    diversification_benefit = "LOW" if avg_corr > 0.75 else "MEDIUM" if avg_corr > 0.60 else "HIGH"

    # International / bond checks
    intl_pct = sum(sector_pct.get(s, 0) for s in ["International"])
    bond_pct = sum(sector_pct.get(s, 0) for s in ["Bonds"])

    return {
        "total_value": total_value,
        "num_holdings": len(holdings),
        "sector_allocation": sector_pct,
        "top_1_pct": top1,
        "top_3_pct": top3,
        "top_5_pct": top5,
        "international_pct": round(intl_pct, 1),
        "bond_pct": round(bond_pct, 1),
        "concentration_label": "HIGH" if top1 > 20 or top3 > 50 else "MODERATE" if top1 > 15 else "LOW",
        "exposure": {
            "ticker": ticker_up,
            "direct": round(direct, 0),
            "indirect_rows": indirect_rows,
            "total_indirect": round(total_indirect, 0),
            "total_current": round(total_current, 0),
            "current_pct": current_pct,
            "proposed_amount": proposed_amount,
            "new_exposure": round(new_exposure, 0),
            "proposed_pct": proposed_pct,
            "exceeds_15pct": exceeds_limit,
        },
        "correlation": {
            "avg_with_portfolio": avg_corr,
            "diversification_benefit": diversification_benefit,
            "new_position_sector": new_sector,
        },
    }
