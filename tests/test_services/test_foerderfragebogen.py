# -*- coding: utf-8 -*-
"""Tests for the Foerder-Katalog eligibility engine (v2 — ZFA PDF schema)."""

from app.config.foerder_katalog import (
    calculate_eligibility,
    get_eligible_foerderungen,
    get_total_yearly_benefit,
)


def _base_data(**overrides):
    """Create base test data matching ZFA PDF Mandant/Partner schema."""
    data = {
        'mandant_vorname': 'Max',
        'mandant_nachname': 'Mustermann',
        'mandant_geburtsdatum': '1990-06-15',
        'partner_vorname': 'Anna',
        'partner_nachname': 'Mustermann',
        'brutto_mandant': 45000,
        'brutto_partner': 30000,
        'kinder': [{'name': 'Tim', 'alter': 5}, {'name': 'Lisa', 'alter': 2}],
        'anzahl_kindergeldberechtigt': 2,
    }
    data.update(overrides)
    return data


class TestEligibilityEngine:

    def test_calculate_returns_all_programs(self):
        results = calculate_eligibility(_base_data())
        assert len(results) == 13  # 13 programs (Baukindergeld entfernt)

    def test_ja_nein_triggers_eligibility(self):
        data = _base_data(bav_mandant_ja=True, bav_mandant_summe=1200)
        eligible = get_eligible_foerderungen(data)
        ids = [f['id'] for f in eligible]
        assert 'bav' in ids

    def test_partner_also_triggers(self):
        data = _base_data(pflege_partner_ja=True, pflege_partner_summe=60)
        eligible = get_eligible_foerderungen(data)
        ids = [f['id'] for f in eligible]
        assert 'pflege' in ids

    def test_v0800_with_kinder_auto_eligible(self):
        """V0800 should be eligible when children exist and no explicit answer."""
        data = _base_data()
        eligible = get_eligible_foerderungen(data)
        ids = [f['id'] for f in eligible]
        assert 'v0800' in ids

    def test_summe_aggregation(self):
        data = _base_data(
            vl_mandant_ja=True, vl_mandant_summe=100,
            vl_partner_ja=True, vl_partner_summe=80,
        )
        eligible = get_eligible_foerderungen(data)
        vl = next(f for f in eligible if f['id'] == 'vl')
        assert vl['schaetz_vorteil'] == 180

    def test_no_answers_minimal_eligible(self):
        results = calculate_eligibility({})
        eligible = [r for r in results if r['eligible']]
        # Without any Ja answers, only V0800 might trigger (if kinder present)
        assert len(eligible) <= 1

    def test_total_benefit_positive_with_answers(self):
        data = _base_data(
            bav_mandant_ja=True, bav_mandant_summe=1500,
            pflege_mandant_ja=True, pflege_mandant_summe=60,
        )
        total = get_total_yearly_benefit(data)
        assert total >= 1560

    def test_multiple_categories(self):
        data = _base_data(
            tilgungszulage_mandant_ja=True, tilgungszulage_mandant_summe=500,
            bav_mandant_ja=True, bav_mandant_summe=1000,
            vl_mandant_ja=True, vl_mandant_summe=123,
        )
        eligible = get_eligible_foerderungen(data)
        categories = set(f['kategorie'] for f in eligible)
        assert len(categories) >= 2  # At least Immobilien + Altersvorsorge + Vermögen

    def test_no_crash_on_bad_data(self):
        """Engine should handle weird/invalid data gracefully."""
        results = calculate_eligibility({'bav_mandant_ja': 'maybe', 'brutto_mandant': 'abc'})
        assert len(results) == 13
