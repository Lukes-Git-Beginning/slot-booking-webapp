# -*- coding: utf-8 -*-
"""
Availability Change Detector
Pure Utility für Vergleich von Availability-Daten (alt vs. neu)
"""

import os
from typing import Dict, List, Any


def detect_availability_changes(
    old_availability: Dict[str, List[str]],
    new_availability: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Vergleiche alte vs. neue Availability und finde Deletions

    Args:
        old_availability: Alte availability.json Daten
            Format: {"2025-01-15 09:00": ["Daniel", "Christian"], ...}
        new_availability: Neue availability.json Daten
            Format: {"2025-01-15 09:00": ["Christian"], ...}

    Returns:
        Dict mit Format:
        {
            'deletions': [
                {
                    'slot': '2025-01-15 09:00',
                    'consultant': 'Daniel',
                    'consultant_full': 'Daniel Herbort'
                }
            ],
            'total_deletions': 1
        }
    """
    deletions = []

    # Lade Berater-Mapping für Vollnamen
    consultant_mapping = _load_consultant_mapping()

    # Iteriere durch alle Slots in old_availability
    for slot, old_consultants in old_availability.items():
        # Hole neue Consultants für diesen Slot (oder leere Liste falls Slot komplett entfernt)
        new_consultants = new_availability.get(slot, [])

        # Finde entfernte Consultants
        old_set = set(old_consultants)
        new_set = set(new_consultants)
        removed = old_set - new_set

        # Erstelle Deletion-Records
        for consultant in removed:
            consultant_full = consultant_mapping.get(consultant, consultant)

            deletions.append({
                'slot': slot,
                'consultant': consultant,
                'consultant_full': consultant_full
            })

    return {
        'deletions': deletions,
        'total_deletions': len(deletions)
    }


def _load_consultant_mapping() -> Dict[str, str]:
    """
    Lade Berater-Mapping aus CONSULTANTS env variable

    CONSULTANTS Format: "Daniel:daniel@example.com,Christian:christian@example.com"

    Returns:
        Dict mit Format: {"Daniel": "Daniel Herbort", "Christian": "Christian Mast", ...}
    """
    consultants_str = os.getenv("CONSULTANTS", "")

    mapping = {}
    for entry in consultants_str.split(','):
        if ':' in entry:
            name, cal_id = entry.split(':', 1)
            short_name = name.strip()

            # Extrahiere Vollnamen aus Email
            # Format: "name.surname@example.com" -> "Name Surname"
            cal_id_clean = cal_id.strip()
            if '@' in cal_id_clean:
                email_local = cal_id_clean.split('@')[0]
                if '.' in email_local:
                    parts = email_local.split('.')
                    full_name = ' '.join([p.capitalize() for p in parts])
                    mapping[short_name] = full_name
                else:
                    # Fallback: Capitalize email local part
                    mapping[short_name] = email_local.capitalize()
            else:
                # Fallback: Use short name
                mapping[short_name] = short_name

    return mapping
