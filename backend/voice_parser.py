"""
Voice-to-investment-intent parser.

Uses:
  1. OpenAI Whisper (whisper-1)  — audio → transcript
  2. GPT-4o-mini                 — transcript → structured JSON intent

If OPENAI_API_KEY is not set, the audio transcription step is skipped
and only text-based intent parsing is available (good for demos where
typing is used instead of actual voice recording).
"""

from __future__ import annotations

import json
import re
import io
from typing import Optional

import config

# ── Company-name → ticker lookup ──────────────────────────────────────────────

_COMPANY_MAP: dict[str, str] = {
    "nvidia": "NVDA",
    "nvda": "NVDA",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "apple": "AAPL",
    "aapl": "AAPL",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "amazon": "AMZN",
    "amzn": "AMZN",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "googl": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "gamestop": "GME",
    "gme": "GME",
    "spy": "SPY",
    "qqq": "QQQ",
    "voo": "VOO",
    "vti": "VTI",
    "netflix": "NFLX",
    "nflx": "NFLX",
}

SUPPORTED_TICKERS = set(_COMPANY_MAP.values())


# ── Regex fallback parser ─────────────────────────────────────────────────────

def _regex_parse(text: str) -> dict:
    """
    Best-effort regex parse when no LLM is available.
    Handles patterns like:
      "I want to buy $5,000 of NVIDIA"
      "Should I invest 3k in Tesla?"
      "analyze Apple for 10 thousand dollars"
    """
    t = text.lower()

    # ── Amount ────────────────────────────────────────────────────────────────
    amount = 0.0
    # "$5,000" / "$5000" (with optional trailing k)
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k)?\b", t)
    if m:
        amount = float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
    if not amount:
        # "5k" / "10k"
        m = re.search(r"\b([\d,]+(?:\.\d+)?)\s*k\b", t)
        if m:
            amount = float(m.group(1).replace(",", "")) * 1000
    if not amount:
        # word numbers "five thousand"
        word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        for w, n in word_map.items():
            if f"{w} thousand" in t:
                amount = n * 1000
                break
            if f"{w} hundred" in t:
                amount = n * 100
                break
    if not amount:
        # bare number: "invest 5000 in" / "5000 dollars" — grab largest reasonable number
        for m in re.finditer(r"\b([\d,]+)\b", t):
            val = float(m.group(1).replace(",", ""))
            if 100 <= val <= 10_000_000:   # plausible investment amounts
                amount = val
                break

    # ── Ticker ───────────────────────────────────────────────────────────────
    ticker: Optional[str] = None
    # Exact uppercase ticker first
    m = re.search(r"\b([A-Z]{2,5})\b", text)
    if m and m.group(1).upper() in SUPPORTED_TICKERS:
        ticker = m.group(1).upper()

    if not ticker:
        for name, sym in _COMPANY_MAP.items():
            if name in t:
                ticker = sym
                break

    # ── Action ────────────────────────────────────────────────────────────────
    action = "analyze"
    if any(w in t for w in ["buy", "invest", "purchase", "put", "long"]):
        action = "buy"
    elif any(w in t for w in ["sell", "short", "avoid"]):
        action = "sell"

    return {
        "ticker": ticker or "",
        "amount": amount,
        "action": action,
        "confidence": 0.6 if ticker and amount else 0.3,
        "raw_text": text,
    }


# ── OpenAI-backed parser ──────────────────────────────────────────────────────

def _openai_parse_intent(text: str) -> dict:
    """Use GPT-4o-mini to extract structured investment intent from text."""
    try:
        from openai import OpenAI
    except ImportError:
        return _regex_parse(text)

    if not config.OPENAI_API_KEY:
        return _regex_parse(text)

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    system = (
        "Extract investment intent from text. Return JSON only.\n\n"
        "Format:\n"
        '{"ticker": "STOCK_SYMBOL", "amount": numeric_value, '
        '"action": "buy|sell|analyze", "confidence": 0.0-1.0}\n\n'
        "Company name mappings:\n"
        "NVIDIA/Nvidia → NVDA, Tesla → TSLA, Apple → AAPL, "
        "Microsoft → MSFT, Amazon → AMZN, Google → GOOGL, "
        "Meta → META, GameStop → GME\n\n"
        "Amount parsing:\n"
        "$5,000 / 5000 dollars / five thousand → 5000\n"
        "3k / 3 thousand → 3000"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    result = json.loads(resp.choices[0].message.content)
    result["raw_text"] = text

    ticker = result.get("ticker", "").upper()
    if ticker not in SUPPORTED_TICKERS:
        # Try company map
        ticker = _COMPANY_MAP.get(ticker.lower(), ticker)
        result["ticker"] = ticker

    return result


def transcribe_audio(audio_bytes: bytes, filename: str = "recording.wav") -> str:
    """
    Transcribe raw audio bytes using OpenAI Whisper.
    Returns the transcript string.
    Raises RuntimeError if OpenAI is not configured.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    if not config.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Add it to .env to enable voice transcription."
        )

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    resp = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="en",
    )
    return resp.text


def parse_investment_intent(text: str) -> dict:
    """
    Extract ticker, amount and action from natural language.

    Uses GPT-4o-mini when OPENAI_API_KEY is set, regex fallback otherwise.

    Returns:
        {
            "ticker": "NVDA",
            "amount": 5000.0,
            "action": "buy",
            "confidence": 0.95,
            "raw_text": "original input",
        }
    """
    if config.OPENAI_API_KEY:
        return _openai_parse_intent(text)
    return _regex_parse(text)
