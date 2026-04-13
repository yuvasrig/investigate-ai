"""
Pytest configuration for backend unit tests.

Adds the backend directory to sys.path so all backend modules are importable
without installing the package, and stubs out heavyweight external dependencies
so tests that exercise pure logic don't need running services.
"""

import sys
import os
from unittest.mock import MagicMock

# Make backend/ importable as the root package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Stub modules that require external services (LLMs, ChromaDB, yfinance).
# Only stubs modules not already loaded — safe to call multiple times.
_EXTERNAL_STUBS = [
    "chromadb",
    "langchain_openai",
    "langchain_anthropic",
    "langchain_community",
    "langchain_core",
    "langchain_core.language_models",
    "yfinance",
    "fpdf2",
    "plaid",
]

for _mod in _EXTERNAL_STUBS:
    sys.modules.setdefault(_mod, MagicMock())
