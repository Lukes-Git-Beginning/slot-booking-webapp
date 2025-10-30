# -*- coding: utf-8 -*-
"""
Utility helper functions
Common functionality used across the application
"""

import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from app.config.base import config, slot_config


def is_admin(user: Optional[str]) -> bool:
    """Check if user has admin privileges"""
    if not user:
        return False
    return user in config.get_admin_users()


def get_userlist() -> Dict[str, str]:
    """Parse userlist from configuration"""
    userlist_str = config.USERLIST
    if not userlist_str:
        return {}

    users = {}
    for user_pass in userlist_str.split(","):
        if ":" in user_pass:
            username, password = user_pass.split(":", 1)
            users[username.strip()] = password.strip()
    return users


def get_week_days(anchor_date):
    """Get week days centered around anchor date for better navigation"""
    # Show 3 days before and 3 days after the current date for better navigation
    return [anchor_date + timedelta(days=i-3) for i in range(7)]


def get_week_start(d):
    """Get start of week from date"""
    return d - timedelta(days=d.weekday())


def get_current_kw(d):
    """Get current calendar week"""
    return d.isocalendar()[1]


def get_app_runtime_days():
    """Calculate application runtime in days"""
    # This was in original code - keeping for compatibility
    return 30  # Placeholder value


def get_color_mapping_status():
    """Get color mapping status - placeholder for migration"""
    return {"status": "active", "mappings": 8}






def week_key_from_date(dt):
    """Generate week key from datetime using ISO year"""
    iso_year, iso_week, iso_weekday = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"€{amount:.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage"""
    return f"{value:.1f}%"


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ========== USERNAME NORMALIZATION ==========

# Mapping von alten/inkonsistenten Usernames zu aktuellen vollständigen Namen
USERNAME_NORMALIZATION_MAP = {
    # Nur Vornamen → Volle Namen
    "ladislav": "ladislav.heka",
    "patrick": "patrick.woltschleger",
    "alexandra": "alexandra.scharrschmidt",
    "christian": "christian.mast",
    "tim": "tim.kreisel",
    "dominik": "dominik.mikic",
    "yasmine": "yasmine.schumacher",
    "daniel": "daniel.herbort",
    "jose": "jose.torspecken",
    "luke": "luke.hoppe",
    "david": "david.nehm",
    "alexander": "alexander.nehm",

    # Alte Kurzformen → Volle Namen (deprecated, nur für Legacy-Support)
    "l.heka": "ladislav.heka",
    "p.woltschleger": "patrick.woltschleger",
    "a.scharrschmidt": "alexandra.scharrschmidt",
    "t.kreisel": "tim.kreisel",
    "d.mikic": "dominik.mikic",
    "y.schumacher": "yasmine.schumacher",
    "d.herbort": "daniel.herbort",
    "j.torspecken": "jose.torspecken",
    "l.hoppe": "luke.hoppe",
    "d.nehm": "david.nehm",
    "a.nehm": "alexander.nehm",

    # Weitere Varianten mit verschiedenen Schreibweisen
    "ann.welge": "ann-kathrin.welge",
    "ann-kathrin": "ann-kathrin.welge",
    "sonja.mast": "sonja.mast",
    "sara.mast": "sara.mast",
}


def normalize_username(username: str) -> str:
    """
    Normalisiert Usernamen zu einem einheitlichen Format.

    Args:
        username: Der zu normalisierende Username (kann Vorname, Kurzform oder voller Name sein)

    Returns:
        Der normalisierte vollständige Username (z.B. "ladislav.heka")
    """
    if not username:
        return username

    # Zu Kleinbuchstaben konvertieren für case-insensitive Matching
    username_lower = username.lower().strip()

    # Prüfe ob Username im Mapping existiert
    if username_lower in USERNAME_NORMALIZATION_MAP:
        return USERNAME_NORMALIZATION_MAP[username_lower]

    # Falls nicht im Mapping, gebe Original zurück (könnte bereits korrekt sein)
    return username


def get_username_variants(username: str) -> list:
    """
    Gibt alle möglichen Varianten eines Usernames zurück.
    Nützlich für die Suche in Kalendern/Logs, die alte Formate verwenden.

    Args:
        username: Der Username (beliebiges Format)

    Returns:
        Liste aller möglichen Username-Varianten
    """
    if not username:
        return []

    # Normalisiere zuerst zum vollständigen Namen
    normalized = normalize_username(username)
    variants = [normalized, username]

    # Finde alle Varianten aus dem Mapping
    for old_name, new_name in USERNAME_NORMALIZATION_MAP.items():
        if new_name == normalized:
            variants.append(old_name)

    # Entferne Duplikate und behalte Reihenfolge
    seen = set()
    unique_variants = []
    for variant in variants:
        if variant not in seen:
            seen.add(variant)
            unique_variants.append(variant)

    return unique_variants


def normalize_data_usernames(data: dict) -> dict:
    """
    Normalisiert alle Usernames in einem Daten-Dictionary.

    Args:
        data: Dictionary mit Usernamen als Keys (z.B. scores, badges)

    Returns:
        Neues Dictionary mit normalisierten Usernames
    """
    normalized_data = {}

    for username, user_data in data.items():
        normalized_username = normalize_username(username)

        # Falls der normalisierte Username bereits existiert, merge die Daten
        if normalized_username in normalized_data:
            # Für scores: addiere Punkte
            if isinstance(user_data, dict) and all(isinstance(v, (int, float)) for v in user_data.values()):
                for month, points in user_data.items():
                    if month in normalized_data[normalized_username]:
                        normalized_data[normalized_username][month] += points
                    else:
                        normalized_data[normalized_username][month] = points
            else:
                # Für andere Daten: behalte das neuere/vollständigere
                normalized_data[normalized_username] = user_data
        else:
            normalized_data[normalized_username] = user_data

    return normalized_data