"""
LLM provider abstraction layer.

Usage:
    from llm_factory import get_analyst_llm, get_judge_llm

    llm = get_analyst_llm().with_structured_output(MySchema)
    result = llm.invoke("...")

All four providers (ollama / anthropic / openai / mixed) return a LangChain
BaseChatModel with an identical interface, so agents never need to know which
provider is active.

Ollama note
-----------
We use Ollama's built-in OpenAI-compatible endpoint
(http://localhost:11434/v1) via ChatOpenAI instead of ChatOllama.
This gives us reliable `.with_structured_output()` across all models
that support JSON mode (llama3.1, mistral-nemo, qwen2.5, etc.).
Pull your model first:  ollama pull llama3.1
"""

from functools import lru_cache
from langchain_core.language_models import BaseChatModel
import config
from config import Provider


# ── Internal builders ─────────────────────────────────────────────────────────

def _build_anthropic(model: str) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic
    if not config.ANTHROPIC_API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
    return ChatAnthropic(
        model=model,
        api_key=config.ANTHROPIC_API_KEY,
        temperature=config.TEMPERATURE,
    )


def _build_openai(model: str) -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    if not config.OPENAI_API_KEY:
        raise EnvironmentError("OPENAI_API_KEY is not set.")
    return ChatOpenAI(
        model=model,
        api_key=config.OPENAI_API_KEY,
        temperature=config.TEMPERATURE,
    )


def _build_ollama(model: str) -> BaseChatModel:
    """
    Use Ollama via the OpenAI-compatible API endpoint.
    This gives consistent .with_structured_output() behaviour.
    Requires: ollama serve + ollama pull <model>
    """
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model,
        base_url=f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1",
        api_key="ollama",          # required field, ignored by Ollama
        temperature=config.TEMPERATURE,
    )


# ── Public interface ──────────────────────────────────────────────────────────

@lru_cache(maxsize=4)
def _cached_llm(role: str, model: str, provider: str) -> BaseChatModel:
    """
    Build and cache an LLM instance.  Keyed by (role, model, provider) so
    changing env vars between requests (in tests) gets a fresh instance.
    """
    if provider == Provider.OLLAMA:
        return _build_ollama(model)
    elif provider == Provider.ANTHROPIC:
        return _build_anthropic(model)
    elif provider == Provider.OPENAI:
        return _build_openai(model)
    elif provider == Provider.MIXED:
        # Analysts → Claude, Judge → GPT-4o
        if role == "judge":
            return _build_openai(model)
        return _build_anthropic(model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_analyst_llm() -> BaseChatModel:
    """Return the configured LLM for Bull / Bear / Strategist agents."""
    return _cached_llm(
        role="analyst",
        model=config.ANALYST_MODEL,
        provider=config.PROVIDER,
    )


def get_judge_llm() -> BaseChatModel:
    """Return the configured LLM for the Judge agent."""
    return _cached_llm(
        role="judge",
        model=config.JUDGE_MODEL,
        provider=config.PROVIDER,
    )


def health_check() -> dict:
    """
    Quick connectivity check — tries to instantiate both LLMs.
    Returns status per role so the /health endpoint can surface it.
    """
    results = {}
    for role, getter in (("analyst", get_analyst_llm), ("judge", get_judge_llm)):
        try:
            getter()
            results[role] = "ok"
        except Exception as exc:
            results[role] = f"error: {exc}"
    return results
