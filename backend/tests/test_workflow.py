"""
Unit tests for pure workflow helpers in workflow.py.

External dependencies (LangGraph, agents, tools, RAG) are stubbed in
conftest.py, allowing these tests to run without any running services.
"""

import sys
from unittest.mock import MagicMock, patch
import pytest

# Stub langgraph before workflow is imported so the graph compilation
# doesn't attempt to connect to anything.
for _mod in ["langgraph", "langgraph.graph"]:
    sys.modules.setdefault(_mod, MagicMock())

# Stub the backend modules that call external services at import time
for _mod in ["tools", "agents", "rag", "rag.retriever", "rag.historical_analogs"]:
    sys.modules.setdefault(_mod, MagicMock())

from workflow import (
    _run_with_retry,
    _should_verify_facts,
    _ensure_evaluated_scenarios,
    _ensure_model_output,
)
from schemas import (
    BullAnalysis,
    BearAnalysis,
    JudgeRecommendation,
    ConfidenceBreakdown,
    EvaluatedScenario,
    VerifiedClaim,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_bull(pe: float | None = None, confidence: int = 7) -> BullAnalysis:
    return BullAnalysis(
        competitive_advantages=[VerifiedClaim(claim="Moat", is_speculative=False)],
        growth_catalysts=[VerifiedClaim(claim="AI demand", is_speculative=True)],
        valuation_justification="Justified by growth",
        best_case_target=500.0,
        best_case_timeline="2 years",
        confidence=confidence,
        pe_ratio=pe,
    )


def _make_bear(pe: float | None = None, confidence: int = 6) -> BearAnalysis:
    return BearAnalysis(
        competition_threats=[VerifiedClaim(claim="AMD competition", is_speculative=False)],
        valuation_concerns="High P/E",
        cyclical_risks=[VerifiedClaim(claim="Macro slowdown", is_speculative=True)],
        worst_case_target=200.0,
        worst_case_timeline="1 year",
        confidence=confidence,
        pe_ratio=pe,
    )


def _make_judge(confidence: int = 72) -> JudgeRecommendation:
    bd = ConfidenceBreakdown(
        growth_potential=70, risk_level=65,
        portfolio_fit=68, timing=72, execution_clarity=75,
    )
    return JudgeRecommendation(
        action="buy",
        recommended_amount=10000.0,
        reasoning="Strong fundamentals",
        confidence_overall=confidence,
        confidence_breakdown=bd,
        entry_strategy="DCA over 4 weeks",
        risk_management="Stop at -15%",
        key_factors=["AI demand", "margin expansion"],
    )


# ── _ensure_model_output ──────────────────────────────────────────────────────

class TestEnsureModelOutput:
    def test_already_correct_type_returned(self):
        bull = _make_bull()
        result = _ensure_model_output("Bull", bull, BullAnalysis)
        assert result is bull

    def test_dict_coerced_to_model(self):
        bull = _make_bull()
        as_dict = bull.model_dump()
        result = _ensure_model_output("Bull", as_dict, BullAnalysis)
        assert isinstance(result, BullAnalysis)

    def test_none_raises_value_error(self):
        with pytest.raises(ValueError, match="returned empty output"):
            _ensure_model_output("Bull", None, BullAnalysis)

    def test_wrong_type_raises_value_error(self):
        with pytest.raises(ValueError, match="invalid output type"):
            _ensure_model_output("Bull", "not a model", BullAnalysis)


# ── _run_with_retry ───────────────────────────────────────────────────────────

class TestRunWithRetry:
    def test_succeeds_on_first_call(self):
        bull = _make_bull()
        result = _run_with_retry("Bull", BullAnalysis, lambda: bull)
        assert result is bull

    def test_succeeds_after_one_failure(self):
        bull = _make_bull()
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("transient error")
            return bull

        result = _run_with_retry(
            "Bull", BullAnalysis, flaky,
            max_retries=3, retry_delay_seconds=0,
        )
        assert result is bull
        assert calls["n"] == 2

    def test_raises_after_all_retries_exhausted(self):
        def always_fails():
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="failed after 2 attempts"):
            _run_with_retry(
                "Bull", BullAnalysis, always_fails,
                max_retries=2, retry_delay_seconds=0,
            )

    def test_validates_output_schema(self):
        # Return a raw dict — should be coerced to BullAnalysis
        bull = _make_bull()
        result = _run_with_retry(
            "Bull", BullAnalysis, lambda: bull.model_dump(),
            max_retries=1, retry_delay_seconds=0,
        )
        assert isinstance(result, BullAnalysis)


# ── _should_verify_facts ──────────────────────────────────────────────────────

class TestShouldVerifyFacts:
    def _state(self, bull_pe, bear_pe):
        return {
            "bull_analysis": _make_bull(pe=bull_pe),
            "bear_analysis": _make_bear(pe=bear_pe),
        }

    def test_triggers_when_divergence_exceeds_threshold(self):
        state = self._state(bull_pe=45.0, bear_pe=30.0)  # diff = 15 > 10
        assert _should_verify_facts(state) is True

    def test_does_not_trigger_when_within_threshold(self):
        state = self._state(bull_pe=35.0, bear_pe=30.0)  # diff = 5
        assert _should_verify_facts(state) is False

    def test_does_not_trigger_at_exact_threshold(self):
        state = self._state(bull_pe=40.0, bear_pe=30.0)  # diff = 10, not > 10
        assert _should_verify_facts(state) is False

    def test_does_not_trigger_when_bull_pe_missing(self):
        state = self._state(bull_pe=None, bear_pe=30.0)
        assert _should_verify_facts(state) is False

    def test_does_not_trigger_when_bear_pe_missing(self):
        state = self._state(bull_pe=40.0, bear_pe=None)
        assert _should_verify_facts(state) is False

    def test_does_not_trigger_when_both_pe_missing(self):
        state = self._state(bull_pe=None, bear_pe=None)
        assert _should_verify_facts(state) is False

    def test_does_not_trigger_when_bull_analysis_missing(self):
        state = {"bull_analysis": None, "bear_analysis": _make_bear(pe=30.0)}
        assert _should_verify_facts(state) is False

    def test_does_not_trigger_when_bear_analysis_missing(self):
        state = {"bull_analysis": _make_bull(pe=45.0), "bear_analysis": None}
        assert _should_verify_facts(state) is False


# ── _ensure_evaluated_scenarios ───────────────────────────────────────────────

class TestEnsureEvaluatedScenarios:
    def _make_rec_with_scenarios(self, scenarios: list[EvaluatedScenario]) -> JudgeRecommendation:
        rec = _make_judge()
        return rec.model_copy(update={"evaluated_scenarios": scenarios})

    def test_no_scenarios_returns_recommendation_unchanged(self):
        rec = _make_judge()
        result = _ensure_evaluated_scenarios(rec, [])
        assert result is rec

    def test_existing_scenarios_preserved(self):
        existing = EvaluatedScenario(
            scenario_name="AI Disruption Analog",
            verified_analogs_used=["Dot-com bust 2000"],
        )
        rec = self._make_rec_with_scenarios([existing])
        result = _ensure_evaluated_scenarios(rec, ["AI Disruption Analog"])
        assert any(s.scenario_name == "AI Disruption Analog" for s in result.evaluated_scenarios)

    def test_fallback_analogs_merged_when_existing_empty(self):
        from unittest.mock import patch

        fallback = [
            {"scenario_name": "Rates Shock / Stagflation Analog", "verified_analogs_used": ["1970s stagflation"]}
        ]
        rec = self._make_rec_with_scenarios([])

        with patch("workflow.get_fallback_evaluated_scenarios", return_value=fallback):
            result = _ensure_evaluated_scenarios(rec, ["Rates Shock / Stagflation Analog"])

        assert any(s.scenario_name == "Rates Shock / Stagflation Analog" for s in result.evaluated_scenarios)

    def test_no_duplicate_analogs_after_merge(self):
        existing = EvaluatedScenario(
            scenario_name="AI Disruption Analog",
            verified_analogs_used=["Dot-com bust 2000"],
        )
        rec = self._make_rec_with_scenarios([existing])

        fallback = [
            {"scenario_name": "AI Disruption Analog", "verified_analogs_used": ["Dot-com bust 2000", "New analog"]}
        ]
        with patch("workflow.get_fallback_evaluated_scenarios", return_value=fallback):
            result = _ensure_evaluated_scenarios(rec, ["AI Disruption Analog"])

        merged = next(s for s in result.evaluated_scenarios if s.scenario_name == "AI Disruption Analog")
        assert merged.verified_analogs_used.count("Dot-com bust 2000") == 1
        assert "New analog" in merged.verified_analogs_used
