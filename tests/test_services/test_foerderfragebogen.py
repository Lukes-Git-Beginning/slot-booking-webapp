# -*- coding: utf-8 -*-
"""Tests for the Foerder-Katalog eligibility engine."""

import pytest
from app.config.foerder_katalog import (
    calculate_eligibility,
    get_eligible_foerderungen,
    get_total_yearly_benefit,
)


def _base_data(**overrides):
    """Create base test data with sensible defaults."""
    data = {
        'geburtsdatum': '1990-06-15',
        'familienstand': 'verheiratet',
        'kinder_anzahl': 2,
        'kinder_geburtsjahre': '[2018, 2021]',
        'beschaeftigung': 'angestellt',
        'rv_pflichtig': True,
        'bruttojahreseinkommen': 45000,
        'zve': 35000,
        'arbeitgeber_vl': True,
        'arbeitgeber_bav': True,
        'kinder_im_haushalt_u18': 2,
        'kinder_in_ausbildung': 0,
        'v0800_beantragt': False,
        'schwangerschaft_geplant': False,
        'wohnsituation': 'mieter',
        'immobilie_geplant': 'keine',
        'bausparvertrag': False,
        'hat_riester': False,
        'hat_ruerup': False,
        'hat_bav': False,
        'hat_bu': 'keine',
        'hat_pflegezusatz': False,
        'hat_vl_vertrag': False,
    }
    data.update(overrides)
    return data


class TestEligibilityEngine:
    """Test the core eligibility calculation."""

    def test_calculate_returns_all_programs(self):
        data = _base_data()
        results = calculate_eligibility(data)
        assert len(results) == 16  # All programs checked

    def test_angestellter_mit_kindern_gets_many(self):
        data = _base_data()
        eligible = get_eligible_foerderungen(data)
        ids = [f['id'] for f in eligible]

        assert 'riester' in ids  # RV-pflichtig, no existing Riester
        assert 'v0800' in ids  # Kinder, not applied
        assert 'pflege_bahr' in ids  # 18+, no existing Pflegezusatz
        assert 'bav' in ids  # Angestellt, AG offers BAV

    def test_riester_needs_rv_pflicht(self):
        # Single self-employed: no Riester (not RV-pflichtig, no spouse)
        data = _base_data(beschaeftigung='selbstaendig', rv_pflichtig=False, familienstand='ledig')
        eligible = get_eligible_foerderungen(data)
        ids = [f['id'] for f in eligible]

        assert 'riester' not in ids
        assert 'ruerup' in ids  # Selbständige get Rürup instead

    def test_riester_mittelbar_berechtigt(self):
        # Married self-employed: Riester via spouse (mittelbar berechtigt)
        data = _base_data(beschaeftigung='selbstaendig', rv_pflichtig=False, familienstand='verheiratet')
        eligible = get_eligible_foerderungen(data)
        ids = [f['id'] for f in eligible]

        assert 'riester' in ids  # Mittelbar berechtigt through spouse

    def test_existing_riester_blocks_new(self):
        data = _base_data(hat_riester=True)
        eligible = get_eligible_foerderungen(data)
        ids = [f['id'] for f in eligible]

        assert 'riester' not in ids

    def test_vl_sparzulage_income_limit(self):
        # Under limit
        data = _base_data(zve=35000, hat_vl_vertrag=False)
        eligible = get_eligible_foerderungen(data)
        assert 'vl_sparzulage' in [f['id'] for f in eligible]

        # Over limit (married: 80k)
        data = _base_data(zve=85000, hat_vl_vertrag=False)
        eligible = get_eligible_foerderungen(data)
        assert 'vl_sparzulage' not in [f['id'] for f in eligible]

    def test_wohnungsbauspraemie_needs_bauspar(self):
        data = _base_data(bausparvertrag=False)
        eligible = get_eligible_foerderungen(data)
        assert 'wohnungsbauspraemie' not in [f['id'] for f in eligible]

        data = _base_data(bausparvertrag=True, zve=30000)
        eligible = get_eligible_foerderungen(data)
        assert 'wohnungsbauspraemie' in [f['id'] for f in eligible]

    def test_kfw_needs_kinder_and_immobilie(self):
        data = _base_data(immobilie_geplant='neubau', zve=80000)
        eligible = get_eligible_foerderungen(data)
        assert 'kfw_wef300' in [f['id'] for f in eligible]

        data = _base_data(immobilie_geplant='keine')
        eligible = get_eligible_foerderungen(data)
        assert 'kfw_wef300' not in [f['id'] for f in eligible]

    def test_v0800_already_applied(self):
        data = _base_data(v0800_beantragt=True)
        eligible = get_eligible_foerderungen(data)
        assert 'v0800' not in [f['id'] for f in eligible]

    def test_no_kinder_skips_family(self):
        data = _base_data(kinder_anzahl=0, kinder_im_haushalt_u18=0)
        eligible = get_eligible_foerderungen(data)
        ids = [f['id'] for f in eligible]
        assert 'v0800' not in ids
        assert 'kinderzuschlag' not in ids

    def test_berufseinsteigerbonus_under_25(self):
        data = _base_data(geburtsdatum='2003-06-15')  # ~22 years old
        eligible = get_eligible_foerderungen(data)
        assert 'riester_berufseinsteiger' in [f['id'] for f in eligible]

    def test_total_benefit_positive(self):
        data = _base_data()
        total = get_total_yearly_benefit(data)
        assert total > 0

    def test_empty_data_no_crash(self):
        """Engine should not crash with empty/minimal data."""
        results = calculate_eligibility({})
        assert len(results) == 16
        # With empty data, most should be not eligible
        eligible = [r for r in results if r['eligible']]
        assert len(eligible) <= 2  # Maybe Pflege-Bahr if age check passes
