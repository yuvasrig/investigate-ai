"""
Document ingestion for InvestiGate RAG.

Two sources:
  1. SEC EDGAR — 10-K and 10-Q filings fetched directly via the EDGAR REST API.
     We extract three sections per filing: Business (Item 1), Risk Factors (Item 1A),
     and MD&A (Item 7).  These give agents real disclosed risks and management outlook.

  2. News articles — full article text fetched from the URLs yfinance provides.
     Falls back to the headline if the page is paywalled or JS-rendered.

Neither source requires an API key.  EDGAR is a free government service.
"""

import os
import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

_FMP_KEY = os.getenv("FMP_API_KEY", "")
_FMP_BASE = "https://financialmodelingprep.com/stable"

# EDGAR requires a descriptive User-Agent per their policy
HEADERS = {"User-Agent": "InvestiGate research@investigateai.com Accept-Encoding: gzip, deflate"}
REQUEST_TIMEOUT = 15

# How many characters to extract per filing section before chunking
MAX_SECTION_CHARS = 10_000


# ── Text chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 350, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping word-count chunks.
    chunk_size=350 words ≈ ~450 tokens — fits comfortably with other context.
    """
    words = text.split()
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


# ── SEC EDGAR ingester ────────────────────────────────────────────────────────

# Regex patterns for the three sections we care about in a 10-K / 10-Q
_SECTION_PATTERNS = {
    "business":     r"item\s+1[.\s]+business",
    "risk_factors": r"item\s+1a[.\s]+risk\s+factors",
    "mda":          r"item\s+7[.\s]+management.{0,40}discussion",
}


class SECIngester:
    """
    Fetches 10-K and 10-Q filings directly from the EDGAR REST API.
    No library dependency — uses requests only.
    """

    # Cache ticker→CIK across instances within a process
    _cik_cache: dict[str, str] = {}

    def _get_cik(self, ticker: str) -> Optional[str]:
        """Resolve a ticker to its SEC CIK number."""
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]
        try:
            resp = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            for entry in resp.json().values():
                if entry.get("ticker", "").upper() == ticker.upper():
                    cik = str(entry["cik_str"])
                    self._cik_cache[ticker] = cik
                    return cik
        except Exception:
            pass
        return None

    def _get_latest_filing_url(self, cik: str, form_type: str) -> Optional[str]:
        """Return the URL to the primary document of the most recent filing."""
        try:
            cik_padded = cik.zfill(10)
            resp = requests.get(
                f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            subs = resp.json()
            recent = subs.get("filings", {}).get("recent", {})

            for form, accession, doc in zip(
                recent.get("form", []),
                recent.get("accessionNumber", []),
                recent.get("primaryDocument", []),
            ):
                if form == form_type:
                    acc_clean = accession.replace("-", "")
                    return (
                        f"https://www.sec.gov/Archives/edgar/data"
                        f"/{cik}/{acc_clean}/{doc}"
                    )
        except Exception:
            pass
        return None

    def _fetch_text(self, url: str) -> str:
        """Fetch an EDGAR filing URL and return clean plain text."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "lxml")
            for tag in soup(["script", "style", "table", "ix:nonfraction", "ix:nonnumeric"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return re.sub(r"\s+", " ", text)
        except Exception:
            return ""

    def _extract_section(self, text: str, section_key: str) -> str:
        """Extract a named section by locating its Item header in the text."""
        pattern = _SECTION_PATTERNS.get(section_key)
        if not pattern:
            return ""
        text_lower = text.lower()
        match = re.search(pattern, text_lower)
        if not match:
            return ""
        start = match.start()
        # Find the next "Item N" header to bound the section
        next_item = re.search(r"item\s+\d+[a-z]?[.\s]", text_lower[start + 100 :])
        if next_item:
            end = start + 100 + next_item.start()
        else:
            end = start + MAX_SECTION_CHARS
        return text[start : min(end, start + MAX_SECTION_CHARS)]

    def fetch_documents(self, ticker: str) -> list[dict]:
        """
        Download and parse the latest 10-K and 10-Q for a ticker.
        Returns a list of {text, metadata} dicts ready for embedding.
        """
        documents: list[dict] = []
        cik = self._get_cik(ticker)
        if not cik:
            return documents

        filing_plan = [
            ("10-K", ["business", "risk_factors", "mda"]),
            ("10-Q", ["risk_factors", "mda"]),
        ]

        for form_type, sections in filing_plan:
            url = self._get_latest_filing_url(cik, form_type)
            if not url:
                continue

            text = self._fetch_text(url)
            if not text:
                continue

            for section_key in sections:
                section_text = self._extract_section(text, section_key)
                if len(section_text) < 200:
                    continue
                for i, chunk in enumerate(chunk_text(section_text)):
                    documents.append({
                        "text": chunk,
                        "metadata": {
                            "source": "sec_edgar",
                            "form": form_type,
                            "section": section_key,
                            "ticker": ticker.upper(),
                            "url": url,
                            "chunk_index": i,
                        },
                    })

        return documents


# ── News ingester ─────────────────────────────────────────────────────────────

# Selectors to find the main article body (ordered by specificity)
_ARTICLE_SELECTORS = [
    "article",
    "[itemprop='articleBody']",
    "[class*='article-body']",
    "[class*='article-content']",
    "[class*='story-body']",
    "[class*='story-content']",
    "main",
]


class NewsIngester:
    """
    Fetches full article text from news URLs provided by yfinance.
    Gracefully falls back to the headline if the page is paywalled
    or requires JavaScript.
    """

    def _fetch_article_text(self, url: str) -> str:
        """Try to get readable article text from a URL."""
        try:
            resp = requests.get(
                url,
                headers={
                    **HEADERS,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=8,
                allow_redirects=True,
            )
            if not resp.ok:
                return ""
            if "text/html" not in resp.headers.get("Content-Type", ""):
                return ""

            soup = BeautifulSoup(resp.content, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "figure"]):
                tag.decompose()

            # Try content-specific selectors first
            for selector in _ARTICLE_SELECTORS:
                el = soup.select_one(selector)
                if el:
                    text = re.sub(r"\s+", " ", el.get_text(separator=" ", strip=True))
                    if len(text) > 200:
                        return text[:6_000]

            # Fallback: whole body
            text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))
            return text[:6_000] if len(text) > 200 else ""
        except Exception:
            return ""

    def fetch_documents(self, ticker: str, news_items: list[dict]) -> list[dict]:
        """
        Fetch full article text for each news item dict.
        Each dict must have at least {"title": ..., "link": ...}.
        Returns list of {text, metadata} dicts.
        """
        documents: list[dict] = []
        for item in news_items:
            title = item.get("title", "").strip()
            url = item.get("link", "")
            publisher = item.get("publisher", "")
            if not title:
                continue

            full_text = self._fetch_article_text(url) if url else ""
            # If we couldn't get article body, use the headline as a minimal doc
            if not full_text or len(full_text) < len(title):
                full_text = title

            for i, chunk in enumerate(chunk_text(full_text)):
                documents.append({
                    "text": chunk,
                    "metadata": {
                        "source": "news",
                        "publisher": publisher,
                        "title": title,
                        "ticker": ticker.upper(),
                        "url": url,
                        "chunk_index": i,
                    },
                })

        return documents


# ── FMP Financials ingester ───────────────────────────────────────────────────

class FMPFinancialsIngester:
    """
    Ingests 4 years of audited annual financials from Financial Modeling Prep
    into ChromaDB so agents can cite concrete historical numbers.

    Each fiscal year becomes one narrative document, e.g.:
        "FY2025 AAPL | Revenue $416B (+6.4% YoY) | Gross Margin 46.9% | ..."

    This converts speculative [SPEC] claims to evidence-grounded ones.
    Requires FMP_API_KEY to be set in the environment.
    """

    def _get(self, path: str) -> list:
        if not _FMP_KEY:
            return []
        try:
            sep = "&" if "?" in path else "?"
            r = requests.get(
                f"{_FMP_BASE}/{path}{sep}apikey={_FMP_KEY}",
                timeout=10,
            )
            if r.ok:
                data = r.json()
                return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    @staticmethod
    def _pct(a, b) -> str:
        try:
            return f"{(float(a) - float(b)) / abs(float(b)) * 100:+.1f}%"
        except Exception:
            return "N/A"

    @staticmethod
    def _bil(v) -> str:
        try:
            v = float(v)
            if abs(v) >= 1e12:
                return f"${v/1e12:.2f}T"
            if abs(v) >= 1e9:
                return f"${v/1e9:.1f}B"
            if abs(v) >= 1e6:
                return f"${v/1e6:.1f}M"
            return f"${v:,.0f}"
        except Exception:
            return "N/A"

    @staticmethod
    def _margin(num, denom) -> str:
        try:
            return f"{float(num) / float(denom) * 100:.1f}%"
        except Exception:
            return "N/A"

    def fetch_documents(self, ticker: str) -> list[dict]:
        if not _FMP_KEY:
            return []

        inc_list = self._get(f"income-statement?symbol={ticker}&period=annual&limit=5")
        bs_list  = self._get(f"balance-sheet-statement?symbol={ticker}&period=annual&limit=5")
        cf_list  = self._get(f"cash-flow-statement?symbol={ticker}&period=annual&limit=5")

        if not inc_list:
            return []

        bs_by_year = {str(b.get("fiscalYear", b.get("date", "")[:4])): b for b in bs_list}
        cf_by_year = {str(c.get("fiscalYear", c.get("date", "")[:4])): c for c in cf_list}

        documents: list[dict] = []
        for i, inc in enumerate(inc_list[:4]):
            fy   = str(inc.get("fiscalYear") or inc.get("date", "")[:4])
            date = str(inc.get("date", ""))[:10]
            rev  = inc.get("revenue") or 0
            gp   = inc.get("grossProfit") or 0
            oi   = inc.get("operatingIncome") or 0
            ni   = inc.get("netIncome") or 0
            ebitda = inc.get("ebitda") or 0
            eps  = inc.get("epsDiluted") or 0
            rd   = inc.get("researchAndDevelopmentExpenses") or 0

            prev_rev = inc_list[i + 1].get("revenue") if i + 1 < len(inc_list) else None
            yoy = self._pct(rev, prev_rev) if prev_rev else "N/A"

            bs = bs_by_year.get(fy, {})
            cash  = bs.get("cashAndShortTermInvestments") or bs.get("cashAndCashEquivalents") or 0
            debt  = bs.get("totalDebt") or 0
            equity = bs.get("totalStockholdersEquity") or 0

            cf = cf_by_year.get(fy, {})
            op_cf = cf.get("operatingCashFlow") or 0
            capex = abs(cf.get("capitalExpenditure") or 0)
            fcf = cf.get("freeCashFlow") or (op_cf - capex)

            narrative = (
                f"FY{fy} ANNUAL FINANCIALS — {ticker.upper()} "
                f"(audited, source: Financial Modeling Prep)\n"
                f"Fiscal year end: {date}\n"
                f"Revenue: {self._bil(rev)} (YoY: {yoy})\n"
                f"Gross Profit: {self._bil(gp)} | Gross Margin: {self._margin(gp, rev)}\n"
                f"Operating Income: {self._bil(oi)} | EBIT Margin: {self._margin(oi, rev)}\n"
                f"EBITDA: {self._bil(ebitda)} | EBITDA Margin: {self._margin(ebitda, rev)}\n"
                f"Net Income: {self._bil(ni)} | Net Margin: {self._margin(ni, rev)}\n"
                f"EPS Diluted: ${float(eps):.2f}\n"
                f"R&D Spending: {self._bil(rd)}\n"
                f"Cash & Short-term Investments: {self._bil(cash)}\n"
                f"Total Debt: {self._bil(debt)}\n"
                f"Shareholders Equity: {self._bil(equity)}\n"
                f"Free Cash Flow: {self._bil(fcf)}\n"
            )

            documents.append({
                "text": narrative,
                "metadata": {
                    "source": "fmp_financials",
                    "fiscal_year": fy,
                    "ticker": ticker.upper(),
                    "chunk_index": 0,
                },
            })

        return documents
