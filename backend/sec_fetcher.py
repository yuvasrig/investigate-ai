"""
SEC EDGAR data fetcher — no API key required.

Uses the public EDGAR REST API to retrieve 10-K filing metadata and
extract plain-text section excerpts for agent grounding and interactive
citations in the frontend.

Rate limit: SEC requests ≤ 10 req/s.  We sleep 0.12 s between calls
and keep an in-process cache so repeat runs are instant.
"""

from __future__ import annotations

import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── Constants ─────────────────────────────────────────────────────────────────

_UA = {"User-Agent": "InvestiGate research@investigateai.com Accept: application/json"}
_RATE_DELAY = 0.12          # seconds between EDGAR requests
_EDGAR_BASE  = "https://data.sec.gov"
_SEC_BASE    = "https://www.sec.gov"

# Section label → (start-pattern, end-pattern)
_SECTION_PATTERNS: dict[str, tuple[str, str]] = {
    "business":     (r"Item\s+1[\.\s]+Business\b",                 r"Item\s+1A"),
    "risk_factors": (r"Item\s+1A[\.\s]*Risk\s+Factors",            r"Item\s+1B"),
    "mda":          (r"Item\s+7[\.\s]*Management.{0,30}Discussion", r"Item\s+7A"),
    "financials":   (r"Item\s+8[\.\s]*Financial\s+Statements",     r"Item\s+9"),
    # Geographic revenue breakdown — appears in financial statement notes or Item 1
    "geography":    (
        r"(?:Geographic|Geographical)\s+(?:Information|Segment|Revenue|Area|Region|Breakdown|Data)",
        r"(?:Item\s+9|\Z)",
    ),
}

# Human-readable labels shown in the frontend
SECTION_LABELS: dict[str, str] = {
    "business":     "Item 1 — Business",
    "risk_factors": "Item 1A — Risk Factors",
    "mda":          "Item 7 — MD&A",
    "financials":   "Item 8 — Financial Statements",
    "geography":    "Geographic Revenue Segments",
}

# Regex patterns that match common geographic revenue table formats
_GEO_ROW_PATTERN = re.compile(
    r"(?:United\s+States|Americas|EMEA|Europe|Asia.Pacific|APAC|International|"
    r"Domestic|North\s+America|Latin\s+America|Middle\s+East|Africa|China|Japan)"
    r"[^$\d]{0,40}\$?\s*[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|B|M))?",
    re.IGNORECASE,
)

# ── In-process caches ─────────────────────────────────────────────────────────

_cik_cache: dict[str, Optional[str]] = {}
_filing_cache: dict[str, Optional[dict]] = {}
_section_cache: dict[str, Optional[str]] = {}


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 20) -> requests.Response:
    time.sleep(_RATE_DELAY)
    return requests.get(url, headers=_UA, timeout=timeout)


# ── CIK lookup ────────────────────────────────────────────────────────────────

def get_cik(ticker: str) -> Optional[str]:
    """Return zero-padded 10-digit CIK for *ticker*, or None if not found."""
    t = ticker.upper()
    if t in _cik_cache:
        return _cik_cache[t]
    try:
        resp = _get(f"{_SEC_BASE}/files/company_tickers.json")
        resp.raise_for_status()
        for entry in resp.json().values():
            if entry.get("ticker", "").upper() == t:
                cik = str(entry["cik_str"]).zfill(10)
                _cik_cache[t] = cik
                return cik
    except Exception:
        pass
    _cik_cache[t] = None
    return None


# ── Filing metadata ───────────────────────────────────────────────────────────

def get_latest_10k(ticker: str) -> Optional[dict]:
    """
    Return metadata for the most recent 10-K:

        {
            "cik":              "0001045810",
            "ticker":           "NVDA",
            "accession_number": "0001045810-24-000029",
            "filing_date":      "2024-02-21",
            "filing_url":       "https://www.sec.gov/Archives/…/nvda20240128.htm",
            "viewer_url":       "https://www.sec.gov/cgi-bin/browse-edgar?…",
            "section_urls": {
                "business":     "https://…#item1",
                "risk_factors": "https://…#item1a",
                "mda":          "https://…#item7",
                "financials":   "https://…#item8",
            }
        }
    """
    t = ticker.upper()
    if t in _filing_cache:
        return _filing_cache[t]

    cik = get_cik(t)
    if not cik:
        _filing_cache[t] = None
        return None

    try:
        resp = _get(f"{_EDGAR_BASE}/submissions/CIK{cik}.json")
        resp.raise_for_status()
        data    = resp.json()
        recent  = data.get("filings", {}).get("recent", {})
        forms   = recent.get("form", [])
        acc_nos = recent.get("accessionNumber", [])
        dates   = recent.get("filingDate", [])
        pdocs   = recent.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form == "10-K":
                acc_clean   = acc_nos[i].replace("-", "")
                cik_int     = int(cik)
                filing_url  = f"{_SEC_BASE}/Archives/edgar/data/{cik_int}/{acc_clean}/{pdocs[i]}"
                viewer_url  = (
                    f"{_SEC_BASE}/cgi-bin/browse-edgar"
                    f"?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=include&count=1"
                )
                result = {
                    "cik":              cik,
                    "ticker":           t,
                    "accession_number": acc_nos[i],
                    "filing_date":      dates[i],
                    "filing_url":       filing_url,
                    "viewer_url":       viewer_url,
                    "section_urls": {
                        "business":     filing_url + "#item1",
                        "risk_factors": filing_url + "#item1a",
                        "mda":          filing_url + "#item7",
                        "financials":   filing_url + "#item8",
                    },
                }
                _filing_cache[t] = result
                return result
    except Exception:
        pass

    _filing_cache[t] = None
    return None


# ── Section text extraction ───────────────────────────────────────────────────

def get_section_text(ticker: str, section: str, max_chars: int = 4000) -> Optional[str]:
    """
    Fetch and return plain text for *section* of the latest 10-K.
    Results are cached per ticker+section.

    *section* must be one of: business | risk_factors | mda | financials
    """
    cache_key = f"{ticker.upper()}:{section}"
    if cache_key in _section_cache:
        return _section_cache[cache_key]

    pattern_pair = _SECTION_PATTERNS.get(section)
    if not pattern_pair:
        return None

    filing = get_latest_10k(ticker)
    if not filing:
        return None

    try:
        resp = _get(filing["filing_url"], timeout=40)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)

        start_pat, end_pat = pattern_pair
        start_m = re.search(start_pat, text, re.IGNORECASE)
        if not start_m:
            _section_cache[cache_key] = None
            return None

        end_m = re.search(end_pat, text[start_m.end():], re.IGNORECASE)
        if end_m:
            excerpt = text[start_m.start(): start_m.end() + end_m.start()]
        else:
            excerpt = text[start_m.start(): start_m.start() + max_chars]

        excerpt = excerpt[:max_chars].strip()
        _section_cache[cache_key] = excerpt
        return excerpt
    except Exception:
        _section_cache[cache_key] = None
        return None


# ── Geographic revenue summary ────────────────────────────────────────────────

def get_geographic_summary(ticker: str, max_chars: int = 1200) -> Optional[str]:
    """
    Extract and return a geographic revenue breakdown from the latest 10-K.

    Searches first for a dedicated geographic section, then falls back to
    scanning the financials section for geo-revenue rows.

    Returns a compact plain-text summary, or None if not found.
    """
    # Try dedicated geographic section first
    geo_text = get_section_text(ticker, "geography", max_chars=max_chars)
    if geo_text and len(geo_text) > 100:
        return geo_text[:max_chars]

    # Fall back: scan financials section for geo-pattern matches
    fin_text = get_section_text(ticker, "financials", max_chars=8000)
    if not fin_text:
        return None

    matches = _GEO_ROW_PATTERN.findall(fin_text)
    if not matches:
        return None

    # Return deduplicated matches as bullet lines
    seen: set[str] = set()
    lines = ["Geographic Revenue Breakdown (extracted from financial statements):"]
    for m in matches:
        clean = re.sub(r"\s+", " ", m.strip())
        if clean not in seen:
            seen.add(clean)
            lines.append(f"  • {clean}")
        if len(lines) > 12:   # cap at ~10 geo rows
            break

    return "\n".join(lines) if len(lines) > 1 else None


# ── Agent grounding block ─────────────────────────────────────────────────────

def get_sec_grounding_context(ticker: str, max_chars_per_section: int = 1800) -> str:
    """
    Return a compact SEC grounding block for injection into agent prompts.
    Includes Risk Factors, MD&A, and geographic revenue data from the latest 10-K.
    Returns an empty string if EDGAR is unavailable (never raises).
    """
    filing = get_latest_10k(ticker)
    if not filing:
        return ""

    lines = [
        f"═══ SEC 10-K GROUNDING ({ticker.upper()}, filed {filing['filing_date']}) ═══",
        f"Source: {filing['filing_url']}",
        "When citing a claim from this filing, set sec_section to the matching item name.",
        "",
    ]

    for section_key, label in [
        ("risk_factors", "ITEM 1A — RISK FACTORS"),
        ("mda",          "ITEM 7 — MD&A"),
    ]:
        text = get_section_text(ticker, section_key, max_chars=max_chars_per_section)
        if text:
            lines += [f"── {label} ──", text[:max_chars_per_section], ""]

    # Geographic revenue data (compact — max 600 chars to stay within token budget)
    geo = get_geographic_summary(ticker, max_chars=600)
    if geo:
        lines += ["── GEOGRAPHIC REVENUE DATA ──", geo, ""]

    return "\n".join(lines)
