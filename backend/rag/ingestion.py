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

import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

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
