# -*- coding: utf-8 -*-
"""
Tests for FinanzScorecardService — rule-based and LLM modes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.models.finanzberatung import ScorecardCategory, TrafficLight
from app.services.finanz_scorecard_service import FinanzScorecardService


@pytest.fixture
def service():
    return FinanzScorecardService()


@pytest.fixture
def sample_contracts():
    """Contracts dict simulating gathered data."""
    mock_doc = MagicMock()
    mock_doc.id = 1
    return {
        "riester": [{
            "doc": mock_doc,
            "fields": {
                "beitrag": {"value": "162.17", "confidence": 0.9, "source_page": 1, "source_text": "", "verified": False},
                "anbieter": {"value": "DWS", "confidence": 0.8, "source_page": 1, "source_text": "", "verified": False},
            },
        }],
        "bu": [{
            "doc": mock_doc,
            "fields": {
                "beitrag": {"value": "89.00", "confidence": 0.9, "source_page": 1, "source_text": "", "verified": False},
            },
        }],
        "privathaftpflicht": [{
            "doc": mock_doc,
            "fields": {
                "beitrag": {"value": "5.50", "confidence": 0.9, "source_page": 1, "source_text": "", "verified": False},
            },
        }],
    }


class TestRuleBasedScoring:
    """Tests for rule-based evaluation (LLM disabled)."""

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_rule_based_when_llm_disabled(self, mock_config, service, sample_contracts):
        mock_config.FINANZ_LLM_ENABLED = False
        result = service._evaluate_category(ScorecardCategory.ALTERSVORSORGE, sample_contracts)
        assert result["category"] == ScorecardCategory.ALTERSVORSORGE
        assert result["rating"] in (TrafficLight.RED, TrafficLight.YELLOW, TrafficLight.GREEN)
        assert "assessment" in result

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_altersvorsorge_with_riester(self, mock_config, service, sample_contracts):
        mock_config.FINANZ_LLM_ENABLED = False
        result = service._eval_rule_based(ScorecardCategory.ALTERSVORSORGE, sample_contracts)
        assert result["rating"] in (TrafficLight.YELLOW, TrafficLight.GREEN)
        assert "1 Altersvorsorge" in result["assessment"]

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_altersvorsorge_empty(self, mock_config, service):
        mock_config.FINANZ_LLM_ENABLED = False
        result = service._eval_rule_based(ScorecardCategory.ALTERSVORSORGE, {})
        assert result["rating"] == TrafficLight.RED

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_absicherung_with_bu_and_haftpflicht(self, mock_config, service, sample_contracts):
        mock_config.FINANZ_LLM_ENABLED = False
        result = service._eval_rule_based(ScorecardCategory.ABSICHERUNG, sample_contracts)
        assert result["rating"] == TrafficLight.GREEN

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_steueroptimierung_with_riester(self, mock_config, service, sample_contracts):
        mock_config.FINANZ_LLM_ENABLED = False
        result = service._eval_rule_based(ScorecardCategory.STEUEROPTIMIERUNG, sample_contracts)
        assert result["rating"] == TrafficLight.YELLOW  # only 1 product


class TestLLMScoring:
    """Tests for LLM-based evaluation."""

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_llm_called_when_enabled(self, mock_config, service, sample_contracts):
        mock_config.FINANZ_LLM_ENABLED = True
        mock_config.FINANZ_LLM_TIMEOUT = 30

        llm_result = {"rating": "green", "assessment": "Gute Aufstellung.", "details": "Punkt 1 | Punkt 2"}
        with patch("app.services.llm_client.llm_client.chat_completion", return_value=llm_result) as mock_llm:
            result = service._evaluate_category(ScorecardCategory.ALTERSVORSORGE, sample_contracts)

        mock_llm.assert_called_once()
        assert result["rating"] == TrafficLight.GREEN
        assert result["assessment"] == "Gute Aufstellung."
        assert result["details"] == "Punkt 1 | Punkt 2"

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_llm_fallback_on_error(self, mock_config, service, sample_contracts):
        mock_config.FINANZ_LLM_ENABLED = True
        mock_config.FINANZ_LLM_TIMEOUT = 30

        with patch("app.services.llm_client.llm_client.chat_completion", return_value=None):
            result = service._evaluate_category(ScorecardCategory.ALTERSVORSORGE, sample_contracts)

        # Should fall back to rule-based
        assert result["category"] == ScorecardCategory.ALTERSVORSORGE
        assert result["rating"] in (TrafficLight.RED, TrafficLight.YELLOW, TrafficLight.GREEN)

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_llm_fallback_on_invalid_rating(self, mock_config, service, sample_contracts):
        mock_config.FINANZ_LLM_ENABLED = True
        mock_config.FINANZ_LLM_TIMEOUT = 30

        llm_result = {"rating": "blue", "assessment": "Test", "details": ""}
        with patch("app.services.llm_client.llm_client.chat_completion", return_value=llm_result):
            result = service._evaluate_category(ScorecardCategory.ALTERSVORSORGE, sample_contracts)

        # "blue" is invalid, should fall back to rule-based
        assert result["rating"] in (TrafficLight.RED, TrafficLight.YELLOW, TrafficLight.GREEN)

    @patch("app.services.finanz_scorecard_service.finanz_config")
    def test_llm_assessment_truncated_to_200(self, mock_config, service, sample_contracts):
        mock_config.FINANZ_LLM_ENABLED = True
        mock_config.FINANZ_LLM_TIMEOUT = 30

        long_text = "A" * 300
        llm_result = {"rating": "green", "assessment": long_text, "details": "Punkt 1"}
        with patch("app.services.llm_client.llm_client.chat_completion", return_value=llm_result):
            result = service._evaluate_category(ScorecardCategory.ALTERSVORSORGE, sample_contracts)

        assert len(result["assessment"]) == 200


class TestContractSummary:
    """Tests for the contract summary builder."""

    def test_build_summary_with_contracts(self, service, sample_contracts):
        summary = service._build_contract_summary(sample_contracts)
        assert "162.17" in summary
        assert "DWS" in summary

    def test_build_summary_empty(self, service):
        summary = service._build_contract_summary({})
        assert summary == "Keine Vertraege vorhanden."


class TestOverallScore:
    """Tests for overall score computation."""

    def test_overall_green(self, service):
        results = [
            {"category": ScorecardCategory.ALTERSVORSORGE, "rating": TrafficLight.GREEN},
            {"category": ScorecardCategory.ABSICHERUNG, "rating": TrafficLight.GREEN},
            {"category": ScorecardCategory.VERMOEGEN_KOSTEN, "rating": TrafficLight.GREEN},
            {"category": ScorecardCategory.STEUEROPTIMIERUNG, "rating": TrafficLight.GREEN},
        ]
        overall = service._compute_overall(results)
        assert overall["rating"] == TrafficLight.GREEN
        assert overall["is_overall"] is True

    def test_overall_red_with_critical(self, service):
        results = [
            {"category": ScorecardCategory.ALTERSVORSORGE, "rating": TrafficLight.RED},
            {"category": ScorecardCategory.ABSICHERUNG, "rating": TrafficLight.RED},
            {"category": ScorecardCategory.VERMOEGEN_KOSTEN, "rating": TrafficLight.RED},
            {"category": ScorecardCategory.STEUEROPTIMIERUNG, "rating": TrafficLight.RED},
        ]
        overall = service._compute_overall(results)
        assert overall["rating"] == TrafficLight.RED
        assert "Kritisch" in overall["assessment"]
