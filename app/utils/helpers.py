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
    """Get week days from anchor date"""
    week_start = anchor_date - timedelta(days=anchor_date.weekday())
    return [week_start + timedelta(days=i) for i in range(7)]


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


def load_availability() -> Dict[str, List[str]]:
    """Load availability data from static file"""
    import json
    import os

    availability_file = "static/availability.json"
    if os.path.exists(availability_file):
        try:
            with open(availability_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading availability: {e}")
            return {}
    return {}


def get_default_availability(date_str: str, hour: str) -> List[str]:
    """Get default consultant availability for a time slot"""
    from app.config.base import consultant_config

    # Basic availability logic - can be enhanced
    weekday = datetime.strptime(date_str, '%Y-%m-%d').weekday()

    # Weekend or evening hours get fewer consultants
    if weekday >= 5 or hour in ["20:00"]:  # Weekend or late evening
        return consultant_config.DEFAULT_STANDARD_CONSULTANTS[:2]
    else:
        return consultant_config.DEFAULT_STANDARD_CONSULTANTS


def get_effective_availability(date_str: str, hour: str) -> List[str]:
    """Get effective availability combining loaded and default data"""
    availability = load_availability()

    # Try to get from loaded data first
    if date_str in availability and hour in availability[date_str]:
        return availability[date_str][hour]

    # Fall back to default availability
    return get_default_availability(date_str, hour)


def week_key_from_date(dt):
    """Generate week key from datetime"""
    return f"{dt.year}-W{dt.isocalendar()[1]:02d}"


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