# -*- coding: utf-8 -*-
"""
Availability Change Detector
Pure Utility für Vergleich von Availability-Daten (alt vs. neu)
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pytz

logger = logging.getLogger(__name__)


def _parse_slot_timestamp(slot_key: str, tz: pytz.BaseTzInfo) -> Optional[datetime]:
    """
    Parse slot timestamp from key (format: "YYYY-MM-DD HH:MM")

    Args:
        slot_key: Slot key (e.g., "2026-01-09 09:00")
        tz: Timezone (e.g., pytz.timezone('Europe/Berlin'))

    Returns:
        Timezone-aware datetime or None if parsing fails
    """
    try:
        # Parse naive datetime
        dt_naive = datetime.strptime(slot_key, "%Y-%m-%d %H:%M")
        # Localize to Berlin timezone
        dt_aware = tz.localize(dt_naive)
        return dt_aware
    except (ValueError, TypeError) as e:
        # Log warning but don't crash
        logger.warning(f"Failed to parse slot timestamp '{slot_key}': {e}")
        return None


def _filter_future_slots(
    availability: Dict[str, List[str]],
    now: datetime
) -> Dict[str, List[str]]:
    """
    Filter availability dict to only include FUTURE slots

    Args:
        availability: Original availability dict
        now: Current timezone-aware or naive datetime

    Returns:
        Filtered dict containing only future slots
    """
    tz = now.tzinfo if now.tzinfo else pytz.timezone('Europe/Berlin')

    # Ensure now is timezone-aware
    if now.tzinfo is None:
        logger.warning("Received timezone-naive datetime, localizing to Europe/Berlin")
        now = tz.localize(now)

    future_slots = {}
    for slot_key, consultants in availability.items():
        slot_dt = _parse_slot_timestamp(slot_key, tz)

        # If parsing failed, include slot (safer to include than exclude)
        if slot_dt is None:
            future_slots[slot_key] = consultants
            continue

        # Only include if slot is in the future
        if slot_dt > now:
            future_slots[slot_key] = consultants

    return future_slots


def detect_availability_changes(
    old_availability: Dict[str, List[str]],
    new_availability: Dict[str, List[str]],
    now: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Vergleiche alte vs. neue Availability und finde Deletions

    NEW: Filters out PAST slots before comparison to avoid false positives

    Args:
        old_availability: Alte availability.json Daten
            Format: {"2025-01-15 09:00": ["Daniel", "Christian"], ...}
        new_availability: Neue availability.json Daten
            Format: {"2025-01-15 09:00": ["Christian"], ...}
        now: Current time (optional, defaults to Berlin time now)

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
    # Determine current time
    if now is None:
        berlin_tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(berlin_tz)

    # Filter both old and new to only FUTURE slots
    old_future = _filter_future_slots(old_availability, now)
    new_future = _filter_future_slots(new_availability, now)

    logger.info(f"Change detection: {len(old_availability)} old slots -> {len(old_future)} future old slots")
    logger.info(f"Change detection: {len(new_availability)} new slots -> {len(new_future)} future new slots")
    logger.info(f"Reference time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    deletions = []

    # Lade Berater-Mapping für Vollnamen
    consultant_mapping = _load_consultant_mapping()

    # Iteriere durch alle Slots in old_future (nur zukünftige Slots)
    for slot, old_consultants in old_future.items():
        # Hole neue Consultants für diesen Slot (oder leere Liste falls Slot komplett entfernt)
        new_consultants = new_future.get(slot, [])

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
