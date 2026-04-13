"""
Unit tests for Pydantic schema validators in schemas.py.

All tests are pure in-process — no LLM calls, no network, no DB.
"""

import pytest
from schemas import (
    BullAnalysis,
    BearAnalysis,
    StrategistAnalysis,
    ConfidenceBreakdown,
    JudgeRecommendation,
    EvaluatedScenario,
    AgentEvidenceScore,
    VerifiedClaim,
    _coerce_money_like_number,
)


# ── _coerce_money_like_number ─────────────────────────────────────────────────

class TestCoerceMoneyLikeNumber:
    def test_passthrough_int(self):
        assert _coerce_money_like_number(42) == 42.0

    def test_passthrough_float(self):
        assert _coerce_money_like_number(3.14) == 3.14

    def test_plain_string_number(self):
        assert _coerce_money_like_number("150.00") == 150.0

    def test_dollar_sign(self):
        assert _coerce_money_like_number("$1,200.50") == 1200.50

    def test_expression_with_equals(self):
        # LLMs sometimes emit "0.95 * $40,000 = $38,000"
        assert _coerce_money_like_number("0.95 * $40,000 = $38,000") == 38000.0

    def test_expression_picks_last_value(self):
        assert _coerce_money_like_number("$100 + $50 = $150") == 150.0

    def test_empty_string_returns_value(self):
        result = _coerce_money_like_number("")
        assert result == ""

    def test_none_passthrough(self):
        assert _coerce_money_like_number(None) is None


# ── BullAnalysis ──────────────────────────────────────────────────────────────

class TestBullAnalysis:
    def _make(self, **overrides):
        defaults = dict(
            competitive_advantages=[VerifiedClaim(claim="Wide moat", is_speculative=False)],
            growth_catalysts=[VerifiedClaim(claim="AI tailwind", is_speculative=True)],
            valuation_justification="Trading at reasonable multiple for growth",
            best_case_target=600.0,
            best_case_timeline="2 years",
            confidence=8,
        )
        return BullAnalysis(**{**defaults, **overrides})

    def test_valid_construction(self):
        bull = self._make()
        assert bull.confidence == 8
        assert bull.best_case_target == 600.0

    def test_price_target_coercion_from_expression(self):
        bull = self._make(best_case_target="0.9 * $500 = $450")
        assert bull.best_case_target == 450.0

    def test_price_target_coercion_dollar_string(self):
        bull = self._make(best_case_target="$750.00")
        assert bull.best_case_target == 750.0

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            self._make(confidence=11)
        with pytest.raises(Exception):
            self._make(confidence=-1)

    def test_optional_pe_ratio_defaults_none(self):
        bull = self._make()
        assert bull.pe_ratio is None

    def test_pe_ratio_set(self):
        bull = self._make(pe_ratio=35.2)
        assert bull.pe_ratio == 35.2


# ── JudgeRecommendation traffic light ────────────────────────────────────────

class TestTrafficLightDerivation:
    def _make_rec(self, confidence: int, color=None):
        bd = ConfidenceBreakdown(
            growth_potential=60, risk_level=50,
            portfolio_fit=55, timing=60, execution_clarity=70,
        )
        return JudgeRecommendation(
            action="buy",
            recommended_amount=10000.0,
            reasoning="Test reasoning",
            confidence_overall=confidence,
            confidence_breakdown=bd,
            entry_strategy="DCA over 4 weeks",
            risk_management="Stop at -15%",
            key_factors=["Factor A"],
            traffic_light_color=color,
        )

    def test_green_at_70(self):
        rec = self._make_rec(70)
        assert rec.traffic_light_color == "green"

    def test_green_above_70(self):
        rec = self._make_rec(85)
        assert rec.traffic_light_color == "green"

    def test_yellow_at_45(self):
        rec = self._make_rec(45)
        assert rec.traffic_light_color == "yellow"

    def test_yellow_at_69(self):
        rec = self._make_rec(69)
        assert rec.traffic_light_color == "yellow"

    def test_red_below_45(self):
        rec = self._make_rec(44)
        assert rec.traffic_light_color == "red"

    def test_red_at_zero(self):
        rec = self._make_rec(0)
        assert rec.traffic_light_color == "red"

    def test_explicit_color_preserved(self):
        # When caller explicitly sets a color it should not be overridden
        rec = self._make_rec(80, color="red")
        assert rec.traffic_light_color == "red"


# ── EvaluatedScenario analog deduplication ───────────────────────────────────

class TestEvaluatedScenarioDeduplication:
    def test_duplicate_analogs_removed(self):
        s = EvaluatedScenario(
            scenario_name="AI Disruption Analog",
            verified_analogs_used=["Dot-com bust (2000)", "Dot-com bust (2000)", "GFC 2008"],
        )
        assert s.verified_analogs_used.count("Dot-com bust (2000)") == 1
        assert len(s.verified_analogs_used) == 2

    def test_legacy_single_field_migrated(self):
        s = EvaluatedScenario.model_validate({
            "scenario_name": "Rates Shock",
            "verified_analog_used": "1970s stagflation",
        })
        assert "1970s stagflation" in s.verified_analogs_used

    def test_legacy_and_list_merged_without_dupe(self):
        s = EvaluatedScenario.model_validate({
            "scenario_name": "Rates Shock",
            "verified_analog_used": "1970s stagflation",
            "verified_analogs_used": ["1970s stagflation", "2022 rate hike cycle"],
        })
        assert s.verified_analogs_used.count("1970s stagflation") == 1
        assert "2022 rate hike cycle" in s.verified_analogs_used

    def test_year_normalised_dedupe(self):
        # "(2000)" vs no year — same content after normalisation should dedupe
        s = EvaluatedScenario(
            scenario_name="Tech Bubble",
            verified_analogs_used=["Dot-com bust (2000)", "Dot-com bust"],
        )
        assert len(s.verified_analogs_used) == 1

    def test_string_coercion(self):
        s = EvaluatedScenario.model_validate({
            "scenario_name": "Test",
            "verified_analogs_used": "Single string instead of list",
        })
        assert isinstance(s.verified_analogs_used, list)
        assert len(s.verified_analogs_used) == 1


# ── AgentEvidenceScore clamping ───────────────────────────────────────────────

class TestAgentEvidenceScoreClamping:
    def test_total_clamped_above_40(self):
        score = AgentEvidenceScore(
            data_citations=10,
            calculation_rigor=10,
            historical_precedent=10,
            counterargument=10,
            total=99,  # LLM hallucinated an impossible total
        )
        assert score.total == 40

    def test_total_clamped_below_zero(self):
        score = AgentEvidenceScore(
            data_citations=0, calculation_rigor=0,
            historical_precedent=0, counterargument=0,
            total=-5,
        )
        assert score.total == 0

    def test_valid_total_preserved(self):
        score = AgentEvidenceScore(
            data_citations=8, calculation_rigor=7,
            historical_precedent=6, counterargument=9,
            total=30,
        )
        assert score.total == 30


# ── StrategistAnalysis alternative_options coercion ──────────────────────────

class TestStrategistAlternativeOptions:
    def _make(self, alternatives):
        return StrategistAnalysis(
            current_exposure="5% indirect via SPY",
            concentration_risk="MODERATE",
            concentration_explanation="Acceptable concentration",
            recommended_allocation=15000.0,
            reasoning="Balanced approach given risk tolerance",
            alternative_options=alternatives,
        )

    def test_plain_strings_unchanged(self):
        s = self._make(["VWO — emerging markets", "BND — bonds"])
        assert s.alternative_options == ["VWO — emerging markets", "BND — bonds"]

    def test_dict_coerced_to_string(self):
        # Ollama sometimes returns list[dict] instead of list[str]
        s = self._make([{"ticker": "VWO", "amount": "$20,000"}])
        assert isinstance(s.alternative_options[0], str)
        assert "VWO" in s.alternative_options[0]

    def test_non_list_wrapped(self):
        s = self._make("single string option")
        assert isinstance(s.alternative_options, list)
        assert len(s.alternative_options) == 1
