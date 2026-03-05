"""
Real market data fetching via yfinance.

fetch_full_market_data(ticker) → dict   — comprehensive snapshot
format_market_context(data)    → str   — LLM-ready formatted block
"""

import math
from datetime import datetime
from typing import Optional

import yfinance as yf


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_price(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_big(v) -> str:
    """Format large dollar values as $XXXb / $XXXm / $XXXk."""
    if v is None:
        return "N/A"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "N/A"
    if abs(v) >= 1e12:
        return f"${v / 1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.2f}M"
    return f"${v:,.0f}"


def _fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_ratio(v, suffix: str = "x") -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v):.2f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def _safe(val):
    """Return None for NaN / inf, otherwise the value."""
    if val is None:
        return None
    try:
        if math.isnan(float(val)) or math.isinf(float(val)):
            return None
    except (TypeError, ValueError):
        pass
    return val


# ── Main data fetcher ─────────────────────────────────────────────────────────

def fetch_full_market_data(ticker: str) -> dict:
    """
    Fetch a comprehensive real-time snapshot for a ticker using yfinance.

    Covers:
    - Price & valuation (PE, PB, PS, EPS, beta)
    - Growth & profitability (revenue, margins, ROE, ROA)
    - Financial health (cash, debt, FCF, short interest)
    - Analyst consensus (rating, price targets, # analysts)
    - Quarterly revenue trend (last 4 quarters)
    - Recent news headlines (last 5)
    - Company profile (sector, industry, business summary)
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    ticker = ticker.upper()

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Guard: if yfinance returns an empty info dict, the ticker is invalid
        if not info or not info.get("regularMarketPrice") and not info.get("currentPrice"):
            return {
                "ticker": ticker,
                "error": f"No market data found for '{ticker}'. Check the ticker symbol.",
                "fetched_at": now,
            }

        data: dict = {
            "ticker": ticker,
            "fetched_at": now,

            # ── Price & valuation ──────────────────────────────────────────────
            "current_price": _safe(info.get("currentPrice") or info.get("regularMarketPrice")),
            "previous_close": _safe(info.get("previousClose")),
            "day_change_pct": _safe(info.get("regularMarketChangePercent")),
            "52_week_high": _safe(info.get("fiftyTwoWeekHigh")),
            "52_week_low": _safe(info.get("fiftyTwoWeekLow")),
            "market_cap": _safe(info.get("marketCap")),
            "pe_trailing": _safe(info.get("trailingPE")),
            "pe_forward": _safe(info.get("forwardPE")),
            "peg_ratio": _safe(info.get("pegRatio")),
            "price_to_book": _safe(info.get("priceToBook")),
            "price_to_sales": _safe(info.get("priceToSalesTrailing12Months")),
            "ev_to_ebitda": _safe(info.get("enterpriseToEbitda")),
            "ev_to_revenue": _safe(info.get("enterpriseToRevenue")),
            "eps_trailing": _safe(info.get("trailingEps")),
            "eps_forward": _safe(info.get("forwardEps")),
            "beta": _safe(info.get("beta")),
            "dividend_yield": _safe(info.get("dividendYield")),

            # ── Growth & profitability ─────────────────────────────────────────
            "revenue_ttm": _safe(info.get("totalRevenue")),
            "revenue_growth_yoy": _safe(info.get("revenueGrowth")),
            "earnings_growth_yoy": _safe(info.get("earningsGrowth")),
            "earnings_quarterly_growth": _safe(info.get("earningsQuarterlyGrowth")),
            "gross_margin": _safe(info.get("grossMargins")),
            "operating_margin": _safe(info.get("operatingMargins")),
            "net_profit_margin": _safe(info.get("profitMargins")),
            "ebitda_margin": _safe(info.get("ebitdaMargins")),
            "roe": _safe(info.get("returnOnEquity")),
            "roa": _safe(info.get("returnOnAssets")),

            # ── Financial health ──────────────────────────────────────────────
            "total_cash": _safe(info.get("totalCash")),
            "total_debt": _safe(info.get("totalDebt")),
            "debt_to_equity": _safe(info.get("debtToEquity")),
            "current_ratio": _safe(info.get("currentRatio")),
            "quick_ratio": _safe(info.get("quickRatio")),
            "free_cash_flow": _safe(info.get("freeCashflow")),
            "operating_cash_flow": _safe(info.get("operatingCashflow")),
            "short_percent_float": _safe(info.get("shortPercentOfFloat")),
            "shares_outstanding": _safe(info.get("sharesOutstanding")),

            # ── Analyst consensus ─────────────────────────────────────────────
            "analyst_mean_target": _safe(info.get("targetMeanPrice")),
            "analyst_median_target": _safe(info.get("targetMedianPrice")),
            "analyst_high_target": _safe(info.get("targetHighPrice")),
            "analyst_low_target": _safe(info.get("targetLowPrice")),
            "analyst_recommendation": info.get("recommendationKey"),
            "analyst_count": info.get("numberOfAnalystOpinions"),

            # ── Company profile ───────────────────────────────────────────────
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "business_summary": (info.get("longBusinessSummary") or "")[:400],
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country"),
            "website": info.get("website"),

            # Populated below
            "quarterly_revenue": [],
            "quarterly_earnings": [],
            "recent_news": [],
        }

        # ── Quarterly revenue & earnings trend ───────────────────────────────
        try:
            q_income = stock.quarterly_income_stmt
            if q_income is not None and not q_income.empty:
                cols = q_income.columns[:4]          # most recent 4 quarters

                if "Total Revenue" in q_income.index:
                    rev_row = q_income.loc["Total Revenue"]
                    data["quarterly_revenue"] = [
                        {"period": str(col)[:10], "revenue": int(rev_row[col])}
                        for col in cols
                        if _safe(rev_row.get(col)) is not None
                    ]

                if "Net Income" in q_income.index:
                    ni_row = q_income.loc["Net Income"]
                    data["quarterly_earnings"] = [
                        {"period": str(col)[:10], "net_income": int(ni_row[col])}
                        for col in cols
                        if _safe(ni_row.get(col)) is not None
                    ]
        except Exception:
            pass  # quarterly data is a nice-to-have

        # ── Recent news headlines ─────────────────────────────────────────────
        try:
            raw_news = stock.news or []
            data["recent_news"] = [
                {
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                }
                for item in raw_news[:5]
                if item.get("title")
            ]
        except Exception:
            pass

        return data

    except Exception as exc:
        return {
            "ticker": ticker,
            "error": str(exc),
            "fetched_at": now,
        }


# ── LLM-ready formatter ───────────────────────────────────────────────────────

def format_market_context(data: dict) -> str:
    """
    Convert the raw market data dict into a clean, structured text block
    ready to be injected into any agent prompt.
    """
    if data.get("error"):
        return (
            f"[Market data unavailable for {data['ticker']}: {data['error']}]\n"
            "Use your best knowledge but explicitly note that real data was unavailable."
        )

    ticker = data["ticker"]
    ts = data.get("fetched_at", "today")
    price = data.get("current_price")
    day_chg = data.get("day_change_pct")
    day_str = f"  ({_fmt_pct(day_chg)} today)" if day_chg is not None else ""

    lines = [
        f"{'='*60}",
        f"  VERIFIED LIVE MARKET DATA — {ticker}  (fetched {ts})",
        f"{'='*60}",
        "",
        "PRICE & VALUATION",
        f"  Current Price       {_fmt_price(price)}{day_str}",
        f"  Previous Close      {_fmt_price(data.get('previous_close'))}",
        f"  52-Week Range       {_fmt_price(data.get('52_week_low'))} – {_fmt_price(data.get('52_week_high'))}",
        f"  Market Cap          {_fmt_big(data.get('market_cap'))}",
        f"  P/E  Trailing       {_fmt_ratio(data.get('pe_trailing'))}",
        f"  P/E  Forward        {_fmt_ratio(data.get('pe_forward'))}",
        f"  PEG Ratio           {_fmt_ratio(data.get('peg_ratio'))}",
        f"  Price / Book        {_fmt_ratio(data.get('price_to_book'))}",
        f"  Price / Sales       {_fmt_ratio(data.get('price_to_sales'))}",
        f"  EV / EBITDA         {_fmt_ratio(data.get('ev_to_ebitda'))}",
        f"  EPS  Trailing       {_fmt_price(data.get('eps_trailing'))}",
        f"  EPS  Forward        {_fmt_price(data.get('eps_forward'))}",
        f"  Beta                {_fmt_ratio(data.get('beta'), '')}",
        f"  Dividend Yield      {_fmt_pct(data.get('dividend_yield'))}",
        "",
        "GROWTH & PROFITABILITY",
        f"  Revenue (TTM)       {_fmt_big(data.get('revenue_ttm'))}",
        f"  Revenue Growth YoY  {_fmt_pct(data.get('revenue_growth_yoy'))}",
        f"  Earnings Growth YoY {_fmt_pct(data.get('earnings_growth_yoy'))}",
        f"  Qtrly EPS Growth    {_fmt_pct(data.get('earnings_quarterly_growth'))}",
        f"  Gross Margin        {_fmt_pct(data.get('gross_margin'))}",
        f"  Operating Margin    {_fmt_pct(data.get('operating_margin'))}",
        f"  Net Profit Margin   {_fmt_pct(data.get('net_profit_margin'))}",
        f"  EBITDA Margin       {_fmt_pct(data.get('ebitda_margin'))}",
        f"  Return on Equity    {_fmt_pct(data.get('roe'))}",
        f"  Return on Assets    {_fmt_pct(data.get('roa'))}",
        "",
        "FINANCIAL HEALTH",
        f"  Cash & Equivalents  {_fmt_big(data.get('total_cash'))}",
        f"  Total Debt          {_fmt_big(data.get('total_debt'))}",
        f"  Debt / Equity       {_fmt_ratio(data.get('debt_to_equity'))}",
        f"  Current Ratio       {_fmt_ratio(data.get('current_ratio'))}",
        f"  Free Cash Flow      {_fmt_big(data.get('free_cash_flow'))}",
        f"  Operating Cash Flow {_fmt_big(data.get('operating_cash_flow'))}",
        f"  Short Interest      {_fmt_pct(data.get('short_percent_float'))}",
    ]

    # Analyst consensus
    n = data.get("analyst_count")
    n_str = f"  ({n} analysts)" if n else ""
    rec = (data.get("analyst_recommendation") or "N/A").upper()
    lines += [
        "",
        f"WALL STREET ANALYST CONSENSUS{n_str}",
        f"  Consensus Rating    {rec}",
        f"  Mean Price Target   {_fmt_price(data.get('analyst_mean_target'))}",
        f"  Median Target       {_fmt_price(data.get('analyst_median_target'))}",
        f"  High Target         {_fmt_price(data.get('analyst_high_target'))}",
        f"  Low Target          {_fmt_price(data.get('analyst_low_target'))}",
    ]

    # Quarterly revenue trend
    q_rev = data.get("quarterly_revenue", [])
    if q_rev:
        lines += ["", "QUARTERLY REVENUE (most recent first)"]
        for q in q_rev:
            lines.append(f"  {q['period']}    {_fmt_big(q['revenue'])}")

    q_earn = data.get("quarterly_earnings", [])
    if q_earn:
        lines += ["", "QUARTERLY NET INCOME (most recent first)"]
        for q in q_earn:
            lines.append(f"  {q['period']}    {_fmt_big(q['net_income'])}")

    # News
    news = data.get("recent_news", [])
    if news:
        lines += ["", "RECENT NEWS HEADLINES"]
        for item in news:
            pub = f"[{item['publisher']}] " if item.get("publisher") else ""
            lines.append(f"  • {pub}{item['title']}")

    # Company profile
    sector = data.get("sector", "Unknown")
    industry = data.get("industry", "Unknown")
    if sector != "Unknown":
        lines += ["", "COMPANY PROFILE"]
        lines.append(f"  Sector    {sector}")
        lines.append(f"  Industry  {industry}")
        if data.get("employees"):
            lines.append(f"  Employees {data['employees']:,}")
        if data.get("business_summary"):
            lines.append(f"  Business  {data['business_summary']}...")

    lines.append(f"{'='*60}")
    return "\n".join(lines)


# ── Legacy helpers (kept for compatibility) ───────────────────────────────────

def pe_ratios_disagree(
    bull_pe: Optional[float], bear_pe: Optional[float], threshold: float = 10.0
) -> bool:
    """Check if Bull and Bear P/E estimates diverge significantly."""
    if bull_pe is None or bear_pe is None:
        return False
    return abs(bull_pe - bear_pe) > threshold
