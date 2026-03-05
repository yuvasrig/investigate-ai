"""
Centralized configuration management.

Switch providers with a single env var:
  LLM_PROVIDER=ollama      → all agents use local Ollama
  LLM_PROVIDER=anthropic   → all agents use Claude
  LLM_PROVIDER=openai      → all agents use GPT-4o
  LLM_PROVIDER=mixed       → analysts use Claude, judge uses GPT-4o (default)
"""

import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class Provider(str, Enum):
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    MIXED = "mixed"  # Claude for analysts, GPT-4o for judge


# ── Provider selection ────────────────────────────────────────────────────────

def _get_provider() -> Provider:
    raw = os.getenv("LLM_PROVIDER", "mixed").lower().strip()
    try:
        return Provider(raw)
    except ValueError:
        valid = [p.value for p in Provider]
        raise ValueError(
            f"Invalid LLM_PROVIDER='{raw}'. Must be one of: {valid}"
        )


PROVIDER: Provider = _get_provider()

# ── Model names ───────────────────────────────────────────────────────────────

# Defaults per provider (override with ANALYST_MODEL / JUDGE_MODEL env vars)
_ANALYST_DEFAULTS = {
    Provider.OLLAMA: "llama3.1",
    Provider.ANTHROPIC: "claude-sonnet-4-6",
    Provider.OPENAI: "gpt-4o",
    Provider.MIXED: "claude-sonnet-4-6",   # Claude for analysts in mixed mode
}

_JUDGE_DEFAULTS = {
    Provider.OLLAMA: "llama3.1",
    Provider.ANTHROPIC: "claude-sonnet-4-6",
    Provider.OPENAI: "gpt-4o",
    Provider.MIXED: "gpt-4o",              # GPT-4o for judge in mixed mode
}

ANALYST_MODEL: str = os.getenv("ANALYST_MODEL", _ANALYST_DEFAULTS[PROVIDER])
JUDGE_MODEL: str = os.getenv("JUDGE_MODEL", _JUDGE_DEFAULTS[PROVIDER])

# ── Provider-specific settings ────────────────────────────────────────────────

TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# Ollama
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# API keys (only required when the relevant provider is active)
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")


def validate() -> None:
    """Raise early with a clear message if required keys are missing."""
    needs_anthropic = PROVIDER in (Provider.ANTHROPIC, Provider.MIXED)
    needs_openai = PROVIDER in (Provider.OPENAI, Provider.MIXED)

    if needs_anthropic and not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            f"LLM_PROVIDER={PROVIDER.value} requires ANTHROPIC_API_KEY to be set."
        )
    if needs_openai and not OPENAI_API_KEY:
        raise EnvironmentError(
            f"LLM_PROVIDER={PROVIDER.value} requires OPENAI_API_KEY to be set."
        )


def summary() -> dict:
    """Return a human-readable config summary (safe to expose in /providers)."""
    return {
        "provider": PROVIDER.value,
        "analyst_model": ANALYST_MODEL,
        "judge_model": JUDGE_MODEL,
        "temperature": TEMPERATURE,
        "ollama_base_url": OLLAMA_BASE_URL if PROVIDER == Provider.OLLAMA else None,
        "anthropic_key_set": bool(ANTHROPIC_API_KEY),
        "openai_key_set": bool(OPENAI_API_KEY),
    }
