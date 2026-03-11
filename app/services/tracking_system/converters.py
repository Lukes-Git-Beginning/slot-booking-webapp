# -*- coding: utf-8 -*-
"""Conversion helpers: color→potential, title→outcome, status extraction, name cleaning."""

import re

from app.utils.color_mapping import get_outcome_from_color, get_potential_type

# Potential-Typ Mapping (für Analyse-Zwecke)
POTENTIAL_TYPES = {
    "2": "normal",          # Grün = Normales Potential
    "7": "top",            # Blau = Top Potential
    "5": "closer_needed",  # Gelb = Closer nötig
    "3": "recall",         # Weintraube = Rückholung
    "9": "standard",       # Graphit = Standard
    "10": "standard",      # Flamingo = Standard
    "11": "no_show",       # Tomate = Nicht erschienen
    "6": "cancelled"       # Mandarine = Abgesagt
}


def _get_potential_type(color_id):
    """Mappe Color ID zu Potential Type"""
    return POTENTIAL_TYPES.get(str(color_id), "unknown")


def _get_outcome_from_title_and_color(title, color_id):
    """
    Bestimme Outcome basierend auf Titel-Keywords (Priorität) und Farbe (Fallback)

    Args:
        title: Event-Titel (Kundenname)
        color_id: Google Calendar Color ID

    Returns:
        str: 'completed', 'no_show', 'ghost', 'cancelled', 'rescheduled', 'overhang'
    """
    title_lower = title.lower() if title else ""

    # 1. Priorität: Titel-basierte Erkennung
    if "ghost" in title_lower:
        return "ghost"
    elif "nicht erschienen" in title_lower:
        return "no_show"
    elif "abgesagt" in title_lower:
        return "cancelled"
    elif "überhang" in title_lower or "ueberhang" in title_lower:
        return "overhang"
    elif "verschoben" in title_lower:
        return "rescheduled"

    # 2. Fallback: Color-basierte Erkennung
    return get_outcome_from_color(color_id)


def _extract_status_from_title(title):
    """
    Extrahiere Status-Marker aus Event-Titel.
    1. Prioritaet: Geklammerte Marker "( status )" oder "(status)"
    2. Fallback: Un-geklammerte Keywords (konsistent mit _get_outcome_from_title_and_color)

    Args:
        title: Event-Titel (Kundenname mit optionalem Status-Marker)

    Returns:
        str: Status ('erschienen', 'nicht erschienen', 'ghost', 'verschoben', 'überhang', 'abgesagt', 'pending')
    """
    # 1. Prioritaet: Geklammerte Marker
    pattern = r'\(\s*(erschienen|nicht erschienen|ghost|verschoben|überhang|ueberhang|abgesagt|exit|vorbehalt)\s*\)'
    match = re.search(pattern, title, re.IGNORECASE)
    if match:
        return match.group(1).lower().strip()

    # 2. Fallback: Un-geklammerte Keywords (konsistent mit _get_outcome_from_title_and_color)
    title_lower = title.lower() if title else ""
    if "ghost" in title_lower:
        return "ghost"
    elif "nicht erschienen" in title_lower:
        return "nicht erschienen"
    elif "abgesagt" in title_lower:
        return "abgesagt"
    elif "überhang" in title_lower or "ueberhang" in title_lower:
        return "überhang"
    elif "verschoben" in title_lower:
        return "verschoben"

    return 'pending'


def _clean_customer_name(summary):
    """
    Entferne Status-Marker aus Kundennamen.

    Args:
        summary: Event-Titel mit optionalem Status-Marker

    Returns:
        str: Kundenname ohne Status-Marker
    """
    pattern = r'\s*\(\s*(erschienen|nicht erschienen|ghost|verschoben|abgesagt|exit|vorbehalt|überhang|ueberhang)\s*\)'
    return re.sub(pattern, '', summary, flags=re.IGNORECASE).strip()
