"""
ChromaDB vector store management for InvestiGate RAG.

Design:
  - One persistent ChromaDB directory (configurable via CHROMA_PERSIST_DIR)
  - One collection per ticker (e.g. "ticker_NVDA")
  - Documents stored with ingested_at timestamp for TTL-based freshness checks
  - Embedding function chosen automatically from the active LLM provider:
      openai / mixed  → text-embedding-3-small  (best quality, requires OPENAI_API_KEY)
      ollama          → nomic-embed-text         (local, no API key)
      anthropic-only  → text-embedding-3-small   (Anthropic has no embeddings API)
      fallback        → chromadb default          (sentence-transformers, fully local)
"""

import os
import time
from functools import lru_cache
from pathlib import Path

import chromadb

import config
from config import Provider

CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
DOC_TTL_HOURS: int = int(os.getenv("RAG_TTL_HOURS", "24"))


# ── Embedding function ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_embedding_fn():
    """
    Build and cache the embedding function.
    Called once — subsequent calls return the cached instance.
    """
    provider = config.PROVIDER

    if provider in (Provider.OPENAI, Provider.MIXED) and config.OPENAI_API_KEY:
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        return OpenAIEmbeddingFunction(
            api_key=config.OPENAI_API_KEY,
            model_name=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        )

    if provider == Provider.ANTHROPIC and config.OPENAI_API_KEY:
        # Anthropic has no embeddings API — use OpenAI even in anthropic-only mode
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        return OpenAIEmbeddingFunction(
            api_key=config.OPENAI_API_KEY,
            model_name="text-embedding-3-small",
        )

    if provider == Provider.OLLAMA:
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
        return OllamaEmbeddingFunction(
            url=f"{config.OLLAMA_BASE_URL}/api/embeddings",
            model_name=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        )

    # Fully local fallback — downloads sentence-transformers on first use
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    return DefaultEmbeddingFunction()


# ── ChromaDB client ───────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_client() -> chromadb.PersistentClient:
    Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def _collection_name(ticker: str) -> str:
    return f"ticker_{ticker.upper()}"


def _get_collection(ticker: str):
    return _get_client().get_or_create_collection(
        name=_collection_name(ticker),
        embedding_function=_get_embedding_fn(),
    )


# ── Public store API ──────────────────────────────────────────────────────────

def upsert_documents(ticker: str, documents: list[dict]) -> int:
    """
    Embed and upsert documents into the ticker's collection.
    Returns the number of documents added.
    """
    if not documents:
        return 0

    col = _get_collection(ticker)
    now = int(time.time())

    ids, texts, metadatas = [], [], []
    for i, doc in enumerate(documents):
        m = doc["metadata"]
        uid = (
            f"{ticker}_{m['source']}_"
            f"{m.get('form', m.get('fiscal_year', 'x'))}_"
            f"{m.get('section', 'x')}_"
            f"{m.get('chunk_index', i)}"
        )
        ids.append(uid)
        texts.append(doc["text"])
        metadatas.append({**doc["metadata"], "ingested_at": now})

    col.upsert(ids=ids, documents=texts, metadatas=metadatas)
    return len(ids)


def is_fresh(ticker: str, max_age_hours: int = DOC_TTL_HOURS) -> bool:
    """Return True if the ticker has recently indexed documents within the TTL."""
    try:
        col = _get_collection(ticker)
        if col.count() == 0:
            return False
        cutoff = int(time.time()) - max_age_hours * 3600
        results = col.get(where={"ingested_at": {"$gte": cutoff}}, limit=1)
        return len(results.get("ids", [])) > 0
    except Exception:
        return False


def similarity_search(ticker: str, query: str, n_results: int = 6) -> list[dict]:
    """Return the top-k most semantically relevant chunks for a query."""
    try:
        col = _get_collection(ticker)
        count = col.count()
        if count == 0:
            return []
        results = col.query(
            query_texts=[query],
            n_results=min(n_results, count),
        )
        return [
            {
                "text": text,
                "metadata": meta,
                "score": round(1.0 - dist, 4),
            }
            for text, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]
    except Exception:
        return []


def clear_ticker(ticker: str) -> None:
    """Delete the collection for a ticker (useful for forced refresh)."""
    try:
        _get_client().delete_collection(_collection_name(ticker))
        _get_embedding_fn.cache_clear()
    except Exception:
        pass


def collection_stats(ticker: str) -> dict:
    """Return document count and source breakdown for a ticker's collection."""
    try:
        col = _get_collection(ticker)
        total = col.count()
        if total == 0:
            return {"total": 0, "sources": {}}
        all_docs = col.get(include=["metadatas"])
        sources: dict[str, int] = {}
        for m in all_docs["metadatas"]:
            src = m.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        return {"total": total, "sources": sources}
    except Exception:
        return {"total": 0, "sources": {}}
