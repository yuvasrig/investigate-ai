"""
Real market data fetching via yfinance.

fetch_full_market_data(ticker) → dict   — comprehensive snapshot
format_market_context(data)    → str   — LLM-ready formatted block
"""

import math
import os
import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests
import requests_cache
import yfinance as yf

# Cache yfinance HTTP calls for 1 hour — eliminates most Yahoo 429 errors
requests_cache.install_cache(
    "yfinance_cache",
    backend="sqlite",
    expire_after=3600,
    allowable_codes=[200],
)

_FMP_KEY = os.getenv("FMP_API_KEY", "")


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


# ── FMP primary data source ───────────────────────────────────────────────────
_FMP_BASE = "https://financialmodelingprep.com/stable"


def _fmp_get(path: str) -> list | dict:
    """GET a FMP stable endpoint. Returns [] on any error."""
    if not _FMP_KEY:
        return []
    try:
        sep = "&" if "?" in path else "?"
        r = requests.get(f"{_FMP_BASE}/{path}{sep}apikey={_FMP_KEY}", timeout=8)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return []


def _fmp_first(path: str) -> dict:
    result = _fmp_get(path)
    return result[0] if isinstance(result, list) and result else {}


def _slugify_company_name(company_name: str) -> str:
    cleaned = (company_name or "").lower()
    cleaned = cleaned.replace("&", " and ")
    cleaned = re.sub(
        r"\b(class [ab]|ordinary shares?|common stock|holdings?|group|company|co|corp|corporation|inc|plc|ltd|limited)\b",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned


def _fetch_companiesmarketcap_trailing_pe(company_name: str | None) -> float | None:
    """
    Best-effort trailing P/E fallback from CompaniesMarketCap.
    This avoids Yahoo's crumb flow and works without an API key.
    """
    slug = _slugify_company_name(company_name or "")
    if not slug:
        return None

    try:
        url = f"https://companiesmarketcap.com/{slug}/pe-ratio/"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if not resp.ok:
            return None
        match = re.search(r"P/E ratio of <strong>([^<]+)</strong>", resp.text, re.I)
        if not match:
            return None
        return float(match.group(1).replace(",", "").strip())
    except Exception:
        return None


def _fetch_google_news(ticker: str, company_name: str | None = None, limit: int = 5) -> list[dict]:
    """
    Fetch a small headline set from Google News RSS without requiring an API key.
    This is a resilient fallback when Yahoo/FMP news is empty or unavailable.
    """
    queries = [f"{ticker} stock"]
    if company_name:
        queries.append(f"\"{company_name}\" stock")

    seen_titles: set[str] = set()
    items: list[dict] = []

    for query in queries:
        if len(items) >= limit:
            break
        try:
            url = (
                "https://news.google.com/rss/search"
                f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            for item in root.findall("./channel/item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                publisher = ""
                source_el = item.find("source")
                if source_el is not None and source_el.text:
                    publisher = source_el.text.strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                items.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                })
                if len(items) >= limit:
                    break
        except Exception:
            continue

    return items


def _fetch_yfinance_news(ticker: str, limit: int = 5) -> list[dict]:
    """
    Fetch a small recent-news set from yfinance even when FMP is the primary
    market-data source. This keeps RAG news ingestion active for FMP-backed runs.
    """
    try:
        session = requests_cache.CachedSession("yfinance_cache", expire_after=3600)
        stock = yf.Ticker(ticker, session=session)
        raw_news = stock.news or []
        return [
            {
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
            }
            for item in raw_news[:limit]
            if item.get("title")
        ]
    except Exception:
        return []


def _fetch_recent_news(ticker: str, company_name: str | None = None, limit: int = 5) -> list[dict]:
    news = _fetch_yfinance_news(ticker, limit=limit)
    if news:
        return news
    return _fetch_google_news(ticker, company_name=company_name, limit=limit)


# ── Main data fetcher ─────────────────────────────────────────────────────────

def fetch_full_market_data(ticker: str) -> dict:
    """
    Fetch a comprehensive real-time snapshot via Financial Modeling Prep (primary)
    with yfinance as a last-resort fallback.

    FMP free tier: ~250-750 calls/day depending on plan.
    Set FMP_API_KEY in .env to enable. Without it, falls back to yfinance.
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    ticker = ticker.upper()

    # ── Try FMP first if key is available ─────────────────────────────────────
    if _FMP_KEY:
        try:
            profile   = _fmp_first(f"profile?symbol={ticker}")
            quote     = _fmp_first(f"quote?symbol={ticker}")
            ratios    = _fmp_first(f"ratios-ttm?symbol={ticker}")
            km        = _fmp_first(f"key-metrics-ttm?symbol={ticker}")
            est_list  = _fmp_get(f"analyst-estimates?symbol={ticker}&period=annual&limit=1")
            est       = est_list[0] if isinstance(est_list, list) and est_list else {}
            inc_list  = _fmp_get(f"income-statement?symbol={ticker}&period=quarter&limit=4")
            pt_cons   = _fmp_first(f"price-target-consensus?symbol={ticker}")
            pt_summ   = _fmp_first(f"price-target-summary?symbol={ticker}")

            if not profile and not quote:
                pass  # fall through to yfinance
            else:
                # Parse 52W range from profile "169.21-288.62" string
                range_str = profile.get("range", "")
                try:
                    low_52, high_52 = (float(x) for x in range_str.split("-"))
                except Exception:
                    low_52 = high_52 = None

                # Revenue growth from quarterly income statements
                rev_growth = None
                quarterly_revenue = []
                quarterly_earnings = []
                if isinstance(inc_list, list) and len(inc_list) >= 2:
                    for q in inc_list:
                        if q.get("revenue"):
                            quarterly_revenue.append({"period": str(q.get("date", ""))[:10], "revenue": int(q["revenue"])})
                        if q.get("netIncome"):
                            quarterly_earnings.append({"period": str(q.get("date", ""))[:10], "net_income": int(q["netIncome"])})
                    r0 = inc_list[0].get("revenue") or 0
                    r4 = inc_list[-1].get("revenue") or 0
                    if r4 > 0:
                        rev_growth = (r0 - r4) / r4

                # EV / Revenue from key metrics
                ev = km.get("enterpriseValueTTM")
                rev_ttm = sum(q.get("revenue", 0) for q in (inc_list[:4] if isinstance(inc_list, list) else []))
                ev_to_rev = _safe(ev / rev_ttm) if ev and rev_ttm else None

                data: dict = {
                    "ticker": ticker,
                    "fetched_at": now,
                    "_source": "fmp",

                    # ── Price & valuation ──────────────────────────────────────
                    "longName": profile.get("companyName") or quote.get("name"),
                    "shortName": profile.get("companyName"),
                    "current_price": _safe(quote.get("price") or profile.get("price")),
                    "previous_close": _safe(quote.get("previousClose")),
                    "day_change_pct": _safe(quote.get("changePercentage") / 100) if quote.get("changePercentage") is not None else None,
                    "52_week_high": _safe(quote.get("yearHigh") or high_52),
                    "52_week_low": _safe(quote.get("yearLow") or low_52),
                    "market_cap": _safe(quote.get("marketCap") or profile.get("marketCap")),
                    "pe_trailing": _safe(ratios.get("priceToEarningsRatioTTM")),
                    "pe_forward": None,  # not in FMP free tier
                    "peg_ratio": _safe(ratios.get("priceToEarningsGrowthRatioTTM")),
                    "price_to_book": _safe(ratios.get("priceToBookRatioTTM")),
                    "price_to_sales": _safe(ratios.get("priceToSalesRatioTTM")),
                    "ev_to_ebitda": _safe(ratios.get("enterpriseValueMultipleTTM")),
                    "ev_to_revenue": _safe(ev_to_rev),
                    "eps_trailing": _safe(ratios.get("revenuePerShareTTM")),
                    "eps_forward": _safe(est.get("epsAvg")),
                    "beta": _safe(profile.get("beta")),
                    "dividend_yield": _safe(ratios.get("dividendYieldTTM")),

                    # ── Growth & profitability ─────────────────────────────────
                    "revenue_ttm": _safe(rev_ttm or None),
                    "revenue_growth_yoy": _safe(rev_growth),
                    "earnings_growth_yoy": None,
                    "earnings_quarterly_growth": None,
                    "gross_margin": _safe(ratios.get("grossProfitMarginTTM")),
                    "operating_margin": _safe(ratios.get("operatingProfitMarginTTM")),
                    "net_profit_margin": _safe(ratios.get("netProfitMarginTTM")),
                    "ebitda_margin": _safe(ratios.get("ebitdaMarginTTM")),
                    "roe": _safe(km.get("returnOnEquityTTM")),
                    "roa": _safe(km.get("returnOnAssetsTTM")),

                    # ── Financial health ──────────────────────────────────────
                    "total_cash": None,
                    "total_debt": None,
                    "debt_to_equity": _safe(ratios.get("debtToEquityRatioTTM")),
                    "current_ratio": _safe(ratios.get("currentRatioTTM")),
                    "quick_ratio": _safe(ratios.get("quickRatioTTM")),
                    "free_cash_flow": None,
                    "operating_cash_flow": None,
                    "short_percent_float": None,
                    "shares_outstanding": None,

                    # ── Analyst consensus ─────────────────────────────────────
                    # Map to yfinance key names so agent prompts work unchanged
                    "targetMeanPrice":   _safe(pt_cons.get("targetConsensus") or pt_summ.get("lastQuarterAvgPriceTarget")),
                    "targetHighPrice":   _safe(pt_cons.get("targetHigh")),
                    "targetLowPrice":    _safe(pt_cons.get("targetLow")),
                    "targetMedianPrice": _safe(pt_cons.get("targetMedian")),
                    "numberOfAnalystOpinions": _safe(pt_summ.get("lastQuarterCount") or est.get("numAnalystsEps")),
                    "recommendationKey": profile.get("rating") or None,
                    "analyst_count": _safe(pt_summ.get("lastQuarterCount") or est.get("numAnalystsEps")),

                    # ── Company profile ───────────────────────────────────────
                    "sector": profile.get("sector", "Unknown"),
                    "industry": profile.get("industry", "Unknown"),
                    "business_summary": (profile.get("description") or "")[:400],
                    "employees": profile.get("fullTimeEmployees"),
                    "country": profile.get("country"),
                    "website": profile.get("website"),

                    "quarterly_revenue": quarterly_revenue,
                    "quarterly_earnings": quarterly_earnings,
                    "recent_news": _fetch_recent_news(
                        ticker,
                        company_name=profile.get("companyName") or quote.get("name"),
                    ),
                }
                if data["pe_trailing"] is None:
                    data["pe_trailing"] = _fetch_companiesmarketcap_trailing_pe(
                        profile.get("companyName") or quote.get("name")
                    )
                return data

        except Exception:
            pass  # fall through to yfinance

    # ── yfinance fallback ──────────────────────────────────────────────────────
    try:
        session = requests_cache.CachedSession("yfinance_cache", expire_after=3600)
        stock = yf.Ticker(ticker, session=session)
        info = stock.info

        if not info or (not info.get("regularMarketPrice") and not info.get("currentPrice")):
            return {
                "ticker": ticker,
                "error": f"No market data found for '{ticker}'. Check the ticker symbol.",
                "fetched_at": now,
            }

        data: dict = {
            "ticker": ticker,
            "fetched_at": now,
            "_source": "yfinance",
            "longName": info.get("longName") or info.get("shortName"),
            "shortName": info.get("shortName"),
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
            "total_cash": _safe(info.get("totalCash")),
            "total_debt": _safe(info.get("totalDebt")),
            "debt_to_equity": _safe(info.get("debtToEquity")),
            "current_ratio": _safe(info.get("currentRatio")),
            "quick_ratio": _safe(info.get("quickRatio")),
            "free_cash_flow": _safe(info.get("freeCashflow")),
            "operating_cash_flow": _safe(info.get("operatingCashflow")),
            "short_percent_float": _safe(info.get("shortPercentOfFloat")),
            "shares_outstanding": _safe(info.get("sharesOutstanding")),
            "analyst_mean_target": _safe(info.get("targetMeanPrice")),
            "analyst_median_target": _safe(info.get("targetMedianPrice")),
            "analyst_high_target": _safe(info.get("targetHighPrice")),
            "analyst_low_target": _safe(info.get("targetLowPrice")),
            "analyst_recommendation": info.get("recommendationKey"),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "business_summary": (info.get("longBusinessSummary") or "")[:400],
            "employees": info.get("fullTimeEmployees"),
            "country": info.get("country"),
            "website": info.get("website"),
            "quarterly_revenue": [],
            "quarterly_earnings": [],
            "recent_news": [],
        }

        try:
            q_income = stock.quarterly_income_stmt
            if q_income is not None and not q_income.empty:
                cols = q_income.columns[:4]
                if "Total Revenue" in q_income.index:
                    rev_row = q_income.loc["Total Revenue"]
                    data["quarterly_revenue"] = [
                        {"period": str(col)[:10], "revenue": int(rev_row[col])}
                        for col in cols if _safe(rev_row.get(col)) is not None
                    ]
                if "Net Income" in q_income.index:
                    ni_row = q_income.loc["Net Income"]
                    data["quarterly_earnings"] = [
                        {"period": str(col)[:10], "net_income": int(ni_row[col])}
                        for col in cols if _safe(ni_row.get(col)) is not None
                    ]
        except Exception:
            pass

        data["recent_news"] = _fetch_recent_news(
            ticker,
            company_name=info.get("longName") or info.get("shortName"),
        )
        if data["pe_trailing"] is None:
            data["pe_trailing"] = _fetch_companiesmarketcap_trailing_pe(
                info.get("longName") or info.get("shortName")
            )

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
            emp = data['employees']
            try:
                lines.append(f"  Employees {int(emp):,}")
            except (TypeError, ValueError):
                lines.append(f"  Employees {emp}")
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
