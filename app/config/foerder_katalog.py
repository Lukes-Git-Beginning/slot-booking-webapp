# -*- coding: utf-8 -*-
"""
Foerder-Katalog - Eligibility Rules for German Subsidies

Each subsidy defines:
- name, kategorie, beschreibung
- max_vorteil: Human-readable benefit description
- check(data) -> bool: Whether the customer is eligible
- details(data) -> str: Personalized hint for the customer
- schaetz_vorteil(data) -> float: Estimated yearly benefit in EUR

Data dict keys match FinanzFoerderFragebogen field names.
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _parse_json_list(value):
    """Parse a JSON string list or return empty list."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _ist_verheiratet(data):
    return data.get('familienstand') in ('verheiratet', 'eingetragene_lp')


def _kinder_count(data):
    return data.get('kinder_anzahl') or 0


def _kinder_ab_2008(data):
    """Count children born 2008 or later."""
    jahre = _parse_json_list(data.get('kinder_geburtsjahre'))
    return sum(1 for j in jahre if j and int(j) >= 2008)


def _kinder_vor_2008(data):
    """Count children born before 2008."""
    jahre = _parse_json_list(data.get('kinder_geburtsjahre'))
    return sum(1 for j in jahre if j and int(j) < 2008)


def _alter(data):
    """Calculate age from geburtsdatum."""
    geb = data.get('geburtsdatum')
    if not geb:
        return None
    try:
        birth = datetime.strptime(str(geb), '%Y-%m-%d')
        today = datetime.now()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except (ValueError, TypeError):
        return None


def _zve(data):
    return data.get('zve') or 0


def _brutto(data):
    return data.get('bruttojahreseinkommen') or 0


def _zve_grenze(data, single_limit, paar_limit):
    """Check if zvE is within limit (considering marital status)."""
    limit = paar_limit if _ist_verheiratet(data) else single_limit
    return _zve(data) <= limit


def _ist_angestellt(data):
    return data.get('beschaeftigung') in ('angestellt', 'ausbildung')


def _ist_rv_pflichtig(data):
    if data.get('rv_pflichtig') is True:
        return True
    return data.get('beschaeftigung') in ('angestellt', 'ausbildung', 'beamtet')


# ---------------------------------------------------------------------------
# Foerder-Definitionen
# ---------------------------------------------------------------------------

FOERDER_KATALOG = [
    {
        'id': 'riester',
        'name': 'Riester-Zulage',
        'kategorie': 'Altersvorsorge',
        'beschreibung': 'Staatliche Zulagen und Steuervorteile für zertifizierte Altersvorsorge.',
        'max_vorteil': '175 EUR/Jahr + 300 EUR/Kind',
        'check': lambda d: (
            _ist_rv_pflichtig(d) or
            (_ist_verheiratet(d) and not d.get('hat_riester'))
        ) and not d.get('hat_riester'),
        'details': lambda d: (
            f"Grundzulage: 175 EUR/Jahr"
            + (f" + {_kinder_ab_2008(d) * 300 + _kinder_vor_2008(d) * 185} EUR Kinderzulage/Jahr"
               if _kinder_count(d) > 0 else "")
            + ". Mindesteigenbeitrag: 4% des Vorjahres-Brutto abzgl. Zulagen."
        ),
        'schaetz_vorteil': lambda d: (
            175
            + _kinder_ab_2008(d) * 300
            + _kinder_vor_2008(d) * 185
        ),
    },
    {
        'id': 'riester_berufseinsteiger',
        'name': 'Riester Berufseinsteigerbonus',
        'kategorie': 'Altersvorsorge',
        'beschreibung': 'Einmaliger Bonus von 200 EUR für Riester-Starter unter 25.',
        'max_vorteil': '200 EUR (einmalig)',
        'check': lambda d: (
            _ist_rv_pflichtig(d)
            and (_alter(d) is not None and _alter(d) < 25)
            and not d.get('hat_riester')
        ),
        'details': lambda d: "Einmalig 200 EUR Bonus im ersten Beitragsjahr.",
        'schaetz_vorteil': lambda d: 200,
    },
    {
        'id': 'ruerup',
        'name': 'Rürup / Basisrente',
        'kategorie': 'Altersvorsorge',
        'beschreibung': 'Steuerlich absetzbare Altersvorsorge (Schicht 1), besonders für Selbständige.',
        'max_vorteil': 'Bis 30.826 EUR/Jahr absetzbar',
        'check': lambda d: (
            d.get('beschaeftigung') == 'selbstaendig'
            and not d.get('hat_ruerup')
        ),
        'details': lambda d: (
            f"Bis zu {'61.652' if _ist_verheiratet(d) else '30.826'} EUR/Jahr "
            "als Sonderausgaben absetzbar. 100% steuerlich wirksam."
        ),
        'schaetz_vorteil': lambda d: min(_brutto(d) * 0.15, 30826),
    },
    {
        'id': 'bav',
        'name': 'Betriebliche Altersvorsorge',
        'kategorie': 'Altersvorsorge',
        'beschreibung': 'Steuer- und SV-freie Entgeltumwandlung mit AG-Zuschuss.',
        'max_vorteil': '15% AG-Zuschuss + Steuerersparnis',
        'check': lambda d: (
            _ist_angestellt(d)
            and d.get('arbeitgeber_bav') is not False
            and not d.get('hat_bav')
        ),
        'details': lambda d: (
            "Bis 8.112 EUR/Jahr steuerfrei, 4.056 EUR SV-frei. "
            "Gesetzlicher AG-Zuschuss: mind. 15% des umgewandelten Entgelts."
        ),
        'schaetz_vorteil': lambda d: min(_brutto(d) * 0.04, 4056) * 0.15 + min(_brutto(d) * 0.04, 4056) * 0.35,
    },
    {
        'id': 'bav_geringverdiener',
        'name': 'BAV Geringverdiener-Förderung',
        'kategorie': 'Altersvorsorge',
        'beschreibung': 'Zusätzliche AG-Förderung für Geringverdiener (§100 EStG).',
        'max_vorteil': 'Bis 288 EUR/Jahr Steuergutschrift für AG',
        'check': lambda d: (
            _ist_angestellt(d)
            and _brutto(d) > 0
            and _brutto(d) / 12 <= 2575
        ),
        'details': lambda d: (
            "Bei Bruttogehalt bis 2.575 EUR/Monat: AG erhält 30% Steuergutschrift "
            "auf Zusatzbeiträge (240-960 EUR/Jahr)."
        ),
        'schaetz_vorteil': lambda d: 288,
    },
    {
        'id': 'vl_sparzulage',
        'name': 'VL + Arbeitnehmersparzulage',
        'kategorie': 'Altersvorsorge',
        'beschreibung': 'Staatliche Zulage auf vermögenswirksame Leistungen.',
        'max_vorteil': 'Bis 123 EUR/Jahr',
        'check': lambda d: (
            _ist_angestellt(d)
            and _zve_grenze(d, 40000, 80000)
            and not d.get('hat_vl_vertrag')
        ),
        'details': lambda d: (
            "Bausparen: 9% auf max. 470 EUR = 43 EUR/Jahr. "
            "Fondssparen: 20% auf max. 400 EUR = 80 EUR/Jahr. "
            "Beides kombinierbar: max. 123 EUR/Jahr."
        ),
        'schaetz_vorteil': lambda d: 123 if not _ist_verheiratet(d) else 246,
    },
    {
        'id': 'wohnungsbauspraemie',
        'name': 'Wohnungsbauprämie',
        'kategorie': 'Wohnen',
        'beschreibung': 'Staatliche Prämie auf Bauspar-Einzahlungen.',
        'max_vorteil': '70 EUR/Jahr (Singles) / 140 EUR/Jahr (Paare)',
        'check': lambda d: (
            d.get('bausparvertrag') is True
            and _zve_grenze(d, 35000, 70000)
        ),
        'details': lambda d: (
            f"10% Prämie auf max. {'1.400' if _ist_verheiratet(d) else '700'} EUR/Jahr Sparleistung."
        ),
        'schaetz_vorteil': lambda d: 140 if _ist_verheiratet(d) else 70,
    },
    {
        'id': 'wohn_riester',
        'name': 'Wohn-Riester',
        'kategorie': 'Wohnen',
        'beschreibung': 'Riester-Förderung für selbstgenutztes Wohneigentum.',
        'max_vorteil': '175 EUR/Jahr + Kinderzulage',
        'check': lambda d: (
            _ist_rv_pflichtig(d)
            and d.get('immobilie_geplant') in ('neubau', 'kauf', 'sanierung')
            and d.get('wohnsituation') != 'eigentuemer'
        ),
        'details': lambda d: (
            "Riester-Zulagen für Kauf, Bau oder Tilgung von Wohneigentum. "
            "Achtung: nachgelagerte Besteuerung über Wohnförderkonto."
        ),
        'schaetz_vorteil': lambda d: 175 + _kinder_ab_2008(d) * 300 + _kinder_vor_2008(d) * 185,
    },
    {
        'id': 'kfw_wef300',
        'name': 'KfW Wohneigentum für Familien',
        'kategorie': 'Wohnen',
        'beschreibung': 'Zinsgünstige KfW-Darlehen für Familien mit Kindern (Neubau).',
        'max_vorteil': 'Kredit bis 270.000 EUR ab 0,01% Zins',
        'check': lambda d: (
            _kinder_count(d) > 0
            and d.get('immobilie_geplant') == 'neubau'
            and _zve(d) <= (90000 + _kinder_count(d) * 10000)
        ),
        'details': lambda d: (
            f"Einkommensgrenze: {90000 + _kinder_count(d) * 10000:,.0f} EUR zvE "
            f"({_kinder_count(d)} Kind{'er' if _kinder_count(d) > 1 else ''}). "
            "Voraussetzung: Effizienzhaus-Standard."
        ),
        'schaetz_vorteil': lambda d: 5000,  # Estimated interest savings
    },
    {
        'id': 'kfw_jung_kauft_alt',
        'name': 'KfW Jung kauft Alt',
        'kategorie': 'Wohnen',
        'beschreibung': 'Zinsgünstige KfW-Darlehen für Familien beim Bestandskauf.',
        'max_vorteil': 'Kredit bis 150.000 EUR ab 0,01% Zins',
        'check': lambda d: (
            _kinder_count(d) > 0
            and d.get('kinder_im_haushalt_u18', 0) > 0
            and d.get('immobilie_geplant') == 'kauf'
            and _zve(d) <= (90000 + _kinder_count(d) * 10000)
        ),
        'details': lambda d: (
            "Für Familien mit Kindern unter 18. Bestandserwerb mit Sanierungspflicht "
            "(EH 85 EE innerhalb 54 Monaten)."
        ),
        'schaetz_vorteil': lambda d: 3000,
    },
    {
        'id': 'v0800',
        'name': 'Kindererziehungszeiten (V0800)',
        'kategorie': 'Kinder & Familie',
        'beschreibung': 'Rentenansprüche für Kindererziehung — Antrag bei der DRV ist Pflicht!',
        'max_vorteil': 'Ca. 41 EUR/Monat Rente pro Erziehungsjahr',
        'check': lambda d: (
            _kinder_count(d) > 0
            and d.get('v0800_beantragt') is not True
        ),
        'details': lambda d: (
            f"Für {_kinder_count(d)} Kind{'er' if _kinder_count(d) > 1 else ''}: "
            f"bis zu {_kinder_count(d) * 3} Jahre anrechenbar = "
            f"ca. {_kinder_count(d) * 122:.0f} EUR/Monat zusätzliche Rente. "
            "WICHTIG: Antrag nicht vergessen, wird nicht automatisch gutgeschrieben!"
        ),
        'schaetz_vorteil': lambda d: _kinder_count(d) * 122 * 12,
    },
    {
        'id': 'kinderzuschlag',
        'name': 'Kinderzuschlag',
        'kategorie': 'Kinder & Familie',
        'beschreibung': 'Bis 297 EUR/Monat pro Kind für Familien mit geringem Einkommen.',
        'max_vorteil': '297 EUR/Monat pro Kind',
        'check': lambda d: (
            (d.get('kinder_im_haushalt_u18') or 0) > 0
            and _brutto(d) > 0
            and _brutto(d) / 12 >= (900 if _ist_verheiratet(d) else 600)
            and _brutto(d) <= 60000
        ),
        'details': lambda d: (
            f"Für {d.get('kinder_im_haushalt_u18', 0)} Kind(er) unter 18: "
            f"bis zu {(d.get('kinder_im_haushalt_u18') or 0) * 297} EUR/Monat. "
            "Voraussetzung: Kindergeldbezug, kein Bürgergeld-Anspruch."
        ),
        'schaetz_vorteil': lambda d: (d.get('kinder_im_haushalt_u18') or 0) * 297 * 6,
    },
    {
        'id': 'elterngeld',
        'name': 'Elterngeld / ElterngeldPlus',
        'kategorie': 'Kinder & Familie',
        'beschreibung': 'Einkommensersatz nach Geburt (65-67% Netto, 300-1.800 EUR/Monat).',
        'max_vorteil': 'Bis 1.800 EUR/Monat für 14 Monate',
        'check': lambda d: (
            d.get('schwangerschaft_geplant') is True
            and _zve(d) <= 175000
        ),
        'details': lambda d: (
            "Basiselterngeld: 65-67% des Nettoeinkommens (300-1.800 EUR/Monat). "
            "ElterngeldPlus: halber Betrag, doppelte Dauer. "
            "Partnerschaftsbonus bei Teilzeit möglich."
        ),
        'schaetz_vorteil': lambda d: min(max(_brutto(d) * 0.65 / 12, 300), 1800) * 12,
    },
    {
        'id': 'pflege_bahr',
        'name': 'Pflege-Bahr',
        'kategorie': 'Versicherung',
        'beschreibung': 'Staatlich geförderte Pflegezusatzversicherung (60 EUR/Jahr Zulage).',
        'max_vorteil': '60 EUR/Jahr',
        'check': lambda d: (
            (_alter(d) is not None and _alter(d) >= 18)
            and not d.get('hat_pflegezusatz')
        ),
        'details': lambda d: (
            "5 EUR/Monat Staatszulage bei mind. 10 EUR/Monat Eigenbeitrag. "
            "Keine Gesundheitsprüfung erforderlich (Kontrahierungszwang)."
        ),
        'schaetz_vorteil': lambda d: 60,
    },
    {
        'id': 'bu_bav',
        'name': 'BU über BAV',
        'kategorie': 'Versicherung',
        'beschreibung': 'Berufsunfähigkeitsversicherung über betriebliche Altersvorsorge — günstiger durch Brutto-Beiträge.',
        'max_vorteil': '40-60% Beitragsersparnis vs. privat',
        'check': lambda d: (
            _ist_angestellt(d)
            and d.get('hat_bu') != 'bav'
            and d.get('arbeitgeber_bav') is not False
        ),
        'details': lambda d: (
            "BU-Beiträge aus dem Brutto: ca. 30-45% Steuer- + 20% SV-Ersparnis. "
            "AG-Zuschuss: mind. 15%. Hinweis: BU-Rente im Leistungsfall voll steuerpflichtig."
        ),
        'schaetz_vorteil': lambda d: 600,  # Estimated yearly savings on premiums
    },
    {
        'id': 'bafoeg',
        'name': 'BAföG (für Kinder)',
        'kategorie': 'Kinder & Familie',
        'beschreibung': 'Ausbildungsförderung für Kinder in Studium/Ausbildung.',
        'max_vorteil': 'Bis 992 EUR/Monat',
        'check': lambda d: (
            (d.get('kinder_in_ausbildung') or 0) > 0
        ),
        'details': lambda d: (
            f"Für {d.get('kinder_in_ausbildung', 0)} Kind(er) in Ausbildung/Studium. "
            "50% Zuschuss, 50% zinsloses Darlehen (max. 10.010 EUR Rückzahlung). "
            "Freibeträge abhängig vom Elterneinkommen."
        ),
        'schaetz_vorteil': lambda d: (d.get('kinder_in_ausbildung') or 0) * 500 * 12,
    },
]


def calculate_eligibility(data: dict) -> list:
    """
    Check all subsidy programs against customer data.

    Args:
        data: Dict with questionnaire answers (field names match model fields)

    Returns:
        List of dicts: [{id, name, kategorie, beschreibung, max_vorteil,
                         eligible, details, schaetz_vorteil}]
    """
    results = []
    for foerderung in FOERDER_KATALOG:
        try:
            eligible = foerderung['check'](data)
            result = {
                'id': foerderung['id'],
                'name': foerderung['name'],
                'kategorie': foerderung['kategorie'],
                'beschreibung': foerderung['beschreibung'],
                'max_vorteil': foerderung['max_vorteil'],
                'eligible': eligible,
            }
            if eligible:
                result['details'] = foerderung['details'](data)
                result['schaetz_vorteil'] = foerderung['schaetz_vorteil'](data)
            results.append(result)
        except Exception as e:
            logger.warning("Eligibility check failed for %s: %s", foerderung['id'], e)
            results.append({
                'id': foerderung['id'],
                'name': foerderung['name'],
                'kategorie': foerderung['kategorie'],
                'beschreibung': foerderung['beschreibung'],
                'max_vorteil': foerderung['max_vorteil'],
                'eligible': False,
            })
    return results


def get_eligible_foerderungen(data: dict) -> list:
    """Return only eligible subsidies with details."""
    return [f for f in calculate_eligibility(data) if f['eligible']]


def get_total_yearly_benefit(data: dict) -> float:
    """Calculate total estimated yearly benefit across all eligible subsidies."""
    eligible = get_eligible_foerderungen(data)
    return sum(f.get('schaetz_vorteil', 0) for f in eligible)
