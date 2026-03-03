# -*- coding: utf-8 -*-
"""
Finanzberatung Classification Service Tests
Tests for app/services/finanz_classification_service.py
"""

import pytest
from unittest.mock import patch, MagicMock


class TestKeywordClassification:
    """Test keyword-based classification (mock mode)."""

    @pytest.fixture
    def service(self):
        from app.services.finanz_classification_service import FinanzClassificationService
        return FinanzClassificationService()

    def test_classify_bu_keywords(self, service):
        """Test BU classification via keywords."""
        text = "Berufsunfaehigkeitsversicherung bei der Allianz, BU-Rente 1500 EUR"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'bu'
        assert result['confidence'] > 0.3

    def test_classify_riester_keywords(self, service):
        """Test Riester classification via keywords."""
        text = "Riester-Rente Zulagenrente staatliche Foerderung"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'riester'

    def test_classify_kfz_keywords(self, service):
        """Test KFZ classification via keywords."""
        text = "KFZ-Versicherung SF-Klasse 12 HSN 0005 TSN 123"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'kfz_auto'

    def test_classify_hausrat_keywords(self, service):
        """Test Hausrat classification via keywords."""
        text = "Hausratversicherung Allianz Hausrat"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'hausrat'

    def test_classify_zzv_keywords(self, service):
        """Test ZZV classification via keywords."""
        text = "Zahnzusatzversicherung ZZV Zahnersatz"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'zzv'

    def test_classify_empty_text_returns_sonstige(self, service):
        """Test that empty text returns 'sonstige'."""
        result = service._classify_keywords('')
        assert result['type_key'] == 'sonstige'
        assert result['confidence'] == 0.1

    def test_classify_no_match_returns_sonstige(self, service):
        """Test that unrecognized text returns 'sonstige'."""
        result = service._classify_keywords('Lorem ipsum dolor sit amet')
        assert result['type_key'] == 'sonstige'
        assert result['confidence'] == 0.1

    def test_confidence_range(self, service):
        """Test that confidence is in valid range 0.1-0.9."""
        text = "Berufsunfaehigkeitsversicherung BU-Versicherung BU-Rente"
        result = service._classify_keywords(text)
        assert 0.1 <= result['confidence'] <= 0.9

    def test_type_label_returned(self, service):
        """Test that classification returns a human-readable label."""
        text = "Rechtsschutzversicherung Rechtsschutz"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'rechtsschutz'
        assert 'type_label' in result
        assert len(result['type_label']) > 0

    def test_all_keyword_types_covered(self):
        """Test that CLASSIFICATION_KEYWORDS covers all non-legacy CONTRACT_TYPES."""
        from app.config.finanz_checklist import CONTRACT_TYPES, CLASSIFICATION_KEYWORDS

        # All types from checklist should have keywords
        for type_key in CONTRACT_TYPES:
            assert type_key in CLASSIFICATION_KEYWORDS, (
                f"Type '{type_key}' missing from CLASSIFICATION_KEYWORDS"
            )

    def test_keyword_matching_weighted_by_length(self, service):
        """Test that longer keyword matches get higher scores."""
        # 'berufsunfaehigkeitsversicherung' is longer than 'bu'
        text = "Berufsunfaehigkeitsversicherung"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'bu'
        assert result['confidence'] > 0.5

    def test_classify_basisrente(self, service):
        """Test Basisrente/Ruerup classification."""
        text = "Basisrente Ruerup Ruerup-Rente"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'basisrente'

    def test_classify_unfallversicherung(self, service):
        """Test Unfallversicherung classification."""
        text = "Unfallversicherung Unfall Invaliditaet Progression"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'unfallversicherung'

    def test_classify_sterbegeld(self, service):
        """Test Sterbegeld classification."""
        text = "Sterbegeldversicherung Bestattungsvorsorge"
        result = service._classify_keywords(text)
        assert result['type_key'] == 'sterbegeld'
