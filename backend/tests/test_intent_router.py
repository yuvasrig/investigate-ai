"""
Unit tests for the deterministic intent router (agents/intent_router.py).

No LLM calls — pure regex and string matching.
"""

import importlib.util
import os
import pytest

# Load intent_router directly from its file to avoid triggering agents/__init__.py,
# which transitively imports llm_factory → config → dotenv (not needed here).
_mod_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents", "intent_router.py")
_spec = importlib.util.spec_from_file_location("intent_router", _mod_path)
_intent_router = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_intent_router)

route_intent = _intent_router.route_intent
_extract_ticker = _intent_router._extract_ticker
_extract_scenarios = _intent_router._extract_scenarios


# ── Ticker extraction ─────────────────────────────────────────────────────────

class TestExtractTicker:
    def test_action_verb_buy(self):
        assert _extract_ticker("Should I buy NVDA?") == "NVDA"

    def test_action_verb_sell(self):
        assert _extract_ticker("sell TSLA now") == "TSLA"

    def test_action_verb_invest_in(self):
        assert _extract_ticker("I want to invest in AAPL") == "AAPL"

    def test_uppercase_token_fallback(self):
        assert _extract_ticker("Is MSFT a good pick?") == "MSFT"

    def test_stopwords_skipped(self):
        # "I", "A", "BUY" are all stopwords — should fall through to GOOGL
        assert _extract_ticker("Should I buy GOOGL or not?") == "GOOGL"

    def test_no_ticker_returns_none(self):
        assert _extract_ticker("what is the weather today?") is None

    def test_lowercase_action_verb(self):
        assert _extract_ticker("analyze amzn please") == "AMZN"


# ── Scenario detection ────────────────────────────────────────────────────────

class TestExtractScenarios:
    def test_ai_disruption_keyword_ai(self):
        assert "AI Disruption Analog" in _extract_scenarios("worried about AI replacing consultants")

    def test_ai_disruption_keyword_automate(self):
        assert "AI Disruption Analog" in _extract_scenarios("automation risk for IBM")

    def test_geopolitical_taiwan(self):
        assert "Geopolitical Escalation: Pacific Rim" in _extract_scenarios("Taiwan tensions are rising")

    def test_rates_shock_inflation(self):
        assert "Rates Shock / Stagflation Analog" in _extract_scenarios("with inflation still high")

    def test_recession_analog(self):
        assert "Demand Slowdown / Recession Analog" in _extract_scenarios("fear of recession next year")

    def test_valuation_compression(self):
        assert "Valuation Compression Analog" in _extract_scenarios("stock looks overvalued to me")

    def test_regulatory_crackdown(self):
        assert "Regulatory Crackdown Analog" in _extract_scenarios("antitrust probe incoming")

    def test_supply_chain_shock(self):
        assert "Supply Chain Shock Analog" in _extract_scenarios("supply chain issues persist")

    def test_commodity_shock(self):
        assert "Commodity Shock Analog" in _extract_scenarios("oil prices spiking")

    def test_crypto_volatility(self):
        assert "Crypto Volatility Analog" in _extract_scenarios("bitcoin halving is coming")

    def test_no_scenario(self):
        assert _extract_scenarios("what is the P/E ratio?") == []

    def test_multiple_scenarios_detected(self):
        scenarios = _extract_scenarios("recession and inflation fears with AI disruption")
        assert "Rates Shock / Stagflation Analog" in scenarios
        assert "Demand Slowdown / Recession Analog" in scenarios
        assert "AI Disruption Analog" in scenarios

    def test_ai_checked_before_valuation(self):
        # "AI bubble" matches AI Disruption first, not Valuation Compression
        scenarios = _extract_scenarios("is this an AI bubble forming?")
        assert "AI Disruption Analog" in scenarios


# ── Ticker-level auto-injection ───────────────────────────────────────────────

class TestTickerAutoInject:
    def test_acn_gets_ai_disruption(self):
        result = route_intent("Is ACN a good investment?", ticker="ACN")
        assert "AI Disruption Analog" in result.scenarios

    def test_ibm_gets_ai_disruption(self):
        result = route_intent("analyze IBM", ticker="IBM")
        assert "AI Disruption Analog" in result.scenarios

    def test_no_auto_inject_for_nvda(self):
        result = route_intent("buy NVDA?", ticker="NVDA")
        assert "AI Disruption Analog" not in result.scenarios

    def test_no_duplicate_when_query_and_ticker_match(self):
        result = route_intent("AI replacing ACN consultants", ticker="ACN")
        assert result.scenarios.count("AI Disruption Analog") == 1


# ── requires_deep_dive flag ───────────────────────────────────────────────────

class TestRequiresDeepDive:
    def test_buy_triggers_deep_dive(self):
        result = route_intent("should I buy TSLA?")
        assert result.requires_deep_dive is True

    def test_sell_triggers_deep_dive(self):
        result = route_intent("sell my AAPL position?")
        assert result.requires_deep_dive is True

    def test_scenario_triggers_deep_dive(self):
        result = route_intent("NVDA under a recession scenario")
        assert result.requires_deep_dive is True

    def test_general_question_no_deep_dive(self):
        result = route_intent("what does NVDA do?")
        assert result.requires_deep_dive is False


# ── Full route_intent integration ─────────────────────────────────────────────

class TestRouteIntent:
    def test_target_asset_extracted(self):
        result = route_intent("Should I buy MSFT with $10k?")
        assert result.target_asset == "MSFT"

    def test_explicit_ticker_used_as_fallback(self):
        result = route_intent("what do you think?", ticker="AMD")
        assert result.target_asset == "AMD"

    def test_query_ticker_overrides_fallback(self):
        result = route_intent("buy NVDA?", ticker="AMD")
        assert result.target_asset == "NVDA"
