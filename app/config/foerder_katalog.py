# -*- coding: utf-8 -*-
"""
Foerder-Katalog - Eligibility Rules for German Subsidies

Based on the ZFA Erfassungsbogen für Förderungen PDF.
Each subsidy has Mandant + Partner dual assessment.

Data dict comes from FinanzFoerderFragebogen.to_full_dict() which merges
stamm fields + JSON answers into a flat dict.
"""

import json
import logging

logger = logging.getLogger(__name__)


def _get(data, key, default=None):
    """Safely get a value, treating empty strings as None."""
    val = data.get(key)
    if val is None or val == '' or val == 'null' or val == 'None':
        return default
    return val


def _bool(data, key):
    """Get a boolean value."""
    val = _get(data, key)
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    return str(val).lower() in ('true', '1', 'ja', 'yes', 'on')


def _float(data, key):
    """Get a float value."""
    val = _get(data, key)
    if val is None:
        return 0
    try:
        return float(str(val).replace(',', '.'))
    except (ValueError, TypeError):
        return 0


def _kinder_count(data):
    kinder = data.get('kinder', [])
    if isinstance(kinder, str):
        try:
            kinder = json.loads(kinder)
        except (json.JSONDecodeError, TypeError):
            return 0
    return len(kinder) if isinstance(kinder, list) else 0


def _kg_berechtigt(data):
    return data.get('anzahl_kindergeldberechtigt') or _kinder_count(data)


# ---------------------------------------------------------------------------
# Förder-Definitionen (nach ZFA PDF)
# ---------------------------------------------------------------------------

FOERDER_KATALOG = [
    # === IMMOBILIENFOERDERUNG ===
    {
        'id': 'tilgungszulage',
        'name': 'Tilgungs-/Vermögensaufbauzulage',
        'kategorie': 'Immobilienförderung',
        'paragraph': '§10a EStG',
        'check': lambda d: _bool(d, 'tilgungszulage_mandant_ja') or _bool(d, 'tilgungszulage_partner_ja'),
        'details': lambda d: "Staatliche Zulage für Tilgung/Vermögensaufbau.",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'tilgungszulage_mandant_summe') or 0)
            + (_float(d, 'tilgungszulage_partner_summe') or 0)
        ),
    },
    {
        'id': 'wohnungsbauspraemie',
        'name': 'Wohnungsbauprämie',
        'kategorie': 'Immobilienförderung',
        'paragraph': 'WoPG 1996',
        'check': lambda d: _bool(d, 'wohnungsbauspraemie_mandant_ja') or _bool(d, 'wohnungsbauspraemie_partner_ja'),
        'details': lambda d: "10% Prämie auf Bauspar-Einzahlungen (max. 70/140 EUR/Jahr).",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'wohnungsbauspraemie_mandant_summe') or 0)
            + (_float(d, 'wohnungsbauspraemie_partner_summe') or 0)
        ),
    },
    {
        'id': 'kfw_darlehen',
        'name': 'KfW-Darlehen',
        'kategorie': 'Immobilienförderung',
        'paragraph': 'Zuschuss 124 BM des Inneren',
        'check': lambda d: _bool(d, 'kfw_darlehen_mandant_ja') or _bool(d, 'kfw_darlehen_partner_ja'),
        'details': lambda d: "Zinsgünstige KfW-Darlehen für Wohneigentum.",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'kfw_darlehen_mandant_summe') or 0)
            + (_float(d, 'kfw_darlehen_partner_summe') or 0)
        ),
    },
    # === ALTERSVORSORGE ===
    {
        'id': 'v0800',
        'name': 'Kindererziehungszeiten (V0800)',
        'kategorie': 'Altersvorsorge',
        'paragraph': '§56 SGB VI',
        'check': lambda d: (
            (_bool(d, 'v0800_mandant_ja') or _bool(d, 'v0800_partner_ja'))
            or (_kinder_count(d) > 0 and not _bool(d, 'v0800_mandant_ja') and not _bool(d, 'v0800_partner_ja'))
        ),
        'details': lambda d: (
            f"Ca. 41 EUR/Monat Rente pro Erziehungsjahr. "
            f"WICHTIG: Antrag bei DRV nicht vergessen!"
        ),
        'schaetz_vorteil': lambda d: (
            (_float(d, 'v0800_mandant_summe') or 0)
            + (_float(d, 'v0800_partner_summe') or 0)
            or _kinder_count(d) * 122 * 12
        ),
    },
    {
        'id': 'bav',
        'name': 'Betriebliche Altersvorsorge',
        'kategorie': 'Altersvorsorge',
        'paragraph': '§3 Nr. 63 EStG',
        'check': lambda d: _bool(d, 'bav_mandant_ja') or _bool(d, 'bav_partner_ja'),
        'details': lambda d: (
            "Bis 8.112 EUR/Jahr steuerfrei. AG-Zuschuss: mind. 15%."
        ),
        'schaetz_vorteil': lambda d: (
            (_float(d, 'bav_mandant_summe') or 0)
            + (_float(d, 'bav_partner_summe') or 0)
        ),
    },
    {
        'id': 'basisrente',
        'name': 'Basisrente',
        'kategorie': 'Altersvorsorge',
        'paragraph': '§10 Abs. 1 Nr. 2b EStG',
        'check': lambda d: _bool(d, 'basisrente_mandant_ja') or _bool(d, 'basisrente_partner_ja'),
        'details': lambda d: "Bis 30.826 EUR/Jahr als Sonderausgaben absetzbar (100%).",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'basisrente_mandant_summe') or 0)
            + (_float(d, 'basisrente_partner_summe') or 0)
        ),
    },

    # === VERMOEGENSAUFBAU ===
    {
        'id': 'vl',
        'name': 'Vermögenswirksame Leistungen',
        'kategorie': 'Vermögensaufbau',
        'paragraph': '5. VermBG',
        'check': lambda d: _bool(d, 'vl_mandant_ja') or _bool(d, 'vl_partner_ja'),
        'details': lambda d: "Arbeitnehmersparzulage: bis 123 EUR/Jahr (Single) / 246 EUR/Jahr (Paar).",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'vl_mandant_summe') or 0)
            + (_float(d, 'vl_partner_summe') or 0)
        ),
    },
    {
        'id': 'freistellungsauftrag',
        'name': 'Freistellungsauftrag für Kapitalerträge',
        'kategorie': 'Vermögensaufbau',
        'paragraph': '§44a EStG',
        'check': lambda d: _bool(d, 'freistellungsauftrag_mandant_ja') or _bool(d, 'freistellungsauftrag_partner_ja'),
        'details': lambda d: "Sparerpauschbetrag: 1.000 EUR (Single) / 2.000 EUR (Paar).",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'freistellungsauftrag_mandant_summe') or 0)
            + (_float(d, 'freistellungsauftrag_partner_summe') or 0)
        ),
    },
    {
        'id': 'freibetrag_kinder',
        'name': 'Freibetrag für Kapitalerträge bei Kindern',
        'kategorie': 'Vermögensaufbau',
        'paragraph': '§32a Abs. 1 Nr.1 EStG, §44a EStG',
        'check': lambda d: _bool(d, 'freibetrag_kinder_mandant_ja') or _bool(d, 'freibetrag_kinder_partner_ja'),
        'details': lambda d: "Kinder haben eigenen Grundfreibetrag + Sparerpauschbetrag.",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'freibetrag_kinder_mandant_summe') or 0)
            + (_float(d, 'freibetrag_kinder_partner_summe') or 0)
        ),
    },
    {
        'id': 'halbeinkuenfte',
        'name': 'Halbeinkünfteverfahren für Kapitalerträge',
        'kategorie': 'Vermögensaufbau',
        'paragraph': '§20 Abs. 1 Nr. 6 S.2 EStG',
        'check': lambda d: _bool(d, 'halbeinkuenfte_mandant_ja') or _bool(d, 'halbeinkuenfte_partner_ja'),
        'details': lambda d: "Nur 50% der Erträge steuerpflichtig bei Altverträgen vor 2005.",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'halbeinkuenfte_mandant_summe') or 0)
            + (_float(d, 'halbeinkuenfte_partner_summe') or 0)
        ),
    },

    # === WEITERE FOERDERUNGEN ===
    {
        'id': 'pflege',
        'name': 'Pflege-Bahr',
        'kategorie': 'Weitere Förderungen',
        'paragraph': '§127 Abs. 2 Nr. 4 SGB XI',
        'check': lambda d: _bool(d, 'pflege_mandant_ja') or _bool(d, 'pflege_partner_ja'),
        'details': lambda d: "60 EUR/Jahr Zulage bei mind. 10 EUR/Monat Eigenbeitrag.",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'pflege_mandant_summe') or 0)
            + (_float(d, 'pflege_partner_summe') or 0)
        ),
    },
    {
        'id': 'arbeitskraft',
        'name': 'Arbeitskraftabsicherung',
        'kategorie': 'Weitere Förderungen',
        'paragraph': '§10 Abs. 1 Nr. 2b EStG',
        'check': lambda d: _bool(d, 'arbeitskraft_mandant_ja') or _bool(d, 'arbeitskraft_partner_ja'),
        'details': lambda d: "BU/Grundfähigkeit über BAV: 40-60% Beitragsersparnis.",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'arbeitskraft_mandant_summe') or 0)
            + (_float(d, 'arbeitskraft_partner_summe') or 0)
        ),
    },
    {
        'id': 'kirchensteuer',
        'name': 'Kirchensteuer',
        'kategorie': 'Weitere Förderungen',
        'paragraph': 'KiSt',
        'check': lambda d: _bool(d, 'kirchensteuer_mandant_ja') or _bool(d, 'kirchensteuer_partner_ja'),
        'details': lambda d: "Kirchensteuer als Sonderausgabe absetzbar.",
        'schaetz_vorteil': lambda d: (
            (_float(d, 'kirchensteuer_mandant_summe') or 0)
            + (_float(d, 'kirchensteuer_partner_summe') or 0)
        ),
    },
]


def calculate_eligibility(data: dict) -> list:
    """Check all subsidy programs against customer data."""
    results = []
    for f in FOERDER_KATALOG:
        try:
            eligible = f['check'](data)
            result = {
                'id': f['id'],
                'name': f['name'],
                'kategorie': f['kategorie'],
                'paragraph': f.get('paragraph', ''),
                'eligible': eligible,
            }
            if eligible:
                result['details'] = f['details'](data)
                result['schaetz_vorteil'] = f['schaetz_vorteil'](data)
            results.append(result)
        except Exception as e:
            logger.warning("Eligibility check failed for %s: %s", f['id'], e)
            results.append({
                'id': f['id'], 'name': f['name'], 'kategorie': f['kategorie'],
                'paragraph': f.get('paragraph', ''), 'eligible': False,
            })
    return results


def get_eligible_foerderungen(data: dict) -> list:
    """Return only eligible subsidies."""
    return [f for f in calculate_eligibility(data) if f['eligible']]


def get_total_yearly_benefit(data: dict) -> float:
    """Total estimated yearly benefit across all eligible subsidies."""
    return sum(f.get('schaetz_vorteil', 0) for f in get_eligible_foerderungen(data))
