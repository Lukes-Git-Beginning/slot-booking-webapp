# -*- coding: utf-8 -*-
"""
T2 Shared Utilities - Common Helpers for T2 Blueprints

Functions:
- Date/time parsing and validation
- Booking parameter validation
- Error handling helpers
- Logger setup
- Common decorators

Migration Status: Phase 2 - Stub created, utilities will be extracted during Phase 4-6
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")


# ============================================================================
# DATE/TIME UTILITIES
# ============================================================================

def parse_appointment_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """
    Parse and validate appointment date/time

    Args:
        date_str: Date string (format: YYYY-MM-DD)
        time_str: Time string (format: HH:MM)

    Returns:
        datetime object (Berlin timezone) or None if invalid

    TODO Phase 5: Extract from t2_legacy.py lines 450-470
    """
    # Stub
    logger.warning("parse_appointment_datetime - stub implementation")
    return None


def format_berlin_datetime(dt: datetime) -> str:
    """
    Format datetime to Berlin timezone string

    Args:
        dt: datetime object

    Returns:
        ISO format string with Berlin timezone

    TODO Phase 4: Extract common datetime formatting logic
    """
    # Stub
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_booking_params(data: Dict) -> Tuple[bool, str]:
    """
    Validate booking request parameters

    Args:
        data: Request data dictionary

    Returns:
        (is_valid: bool, error_message: str)

    TODO Phase 5: Extract from t2_legacy.py lines 820-845
    """
    # Stub
    logger.warning("validate_booking_params - stub implementation")
    return False, "Phase 5 implementation pending"


def validate_closer_name(name: str) -> Tuple[bool, str]:
    """
    Validate closer name format

    Args:
        name: Closer name to validate

    Returns:
        (is_valid: bool, error_message: str)

    TODO Phase 6: Extract from bucket validation logic
    """
    # Stub
    if not name or len(name) < 2:
        return False, "Invalid closer name"
    return True, ""


# ============================================================================
# ERROR HANDLING UTILITIES
# ============================================================================

def handle_calendar_error(error: Exception) -> Dict:
    """
    Standardized Google Calendar error handling

    Args:
        error: Exception from Google Calendar API

    Returns:
        Error response dictionary

    TODO Phase 5: Extract common error handling patterns
    """
    # Stub
    logger.error(f"Calendar error: {error}")
    return {
        'success': False,
        'error': 'calendar_error',
        'message': str(error)
    }


def log_bucket_draw(username: str, result: Dict):
    """
    Log bucket draw for analytics

    Args:
        username: User who drew
        result: Draw result dictionary

    TODO Phase 6: Implement draw logging
    """
    # Stub
    logger.info(f"Bucket draw - user: {username}, result: {result.get('closer', 'unknown')}")


# ============================================================================
# DECORATORS
# ============================================================================

def admin_required_decorator():
    """
    Admin-only decorator (already implemented in admin.py)

    NOTE: This is defined in admin.py, kept here for reference
    """
    pass


# ============================================================================
# CONSTANTS
# ============================================================================

# API endpoint URLs for backward compatibility
BOOKING_API_ENDPOINTS = {
    'available_dates': '/t2/api/available-dates',
    'available_times': '/t2/api/available-times',
    'book_appointment': '/t2/api/book-appointment',
    'cancel_booking': '/t2/api/cancel-booking',
    'reschedule_booking': '/t2/api/reschedule-booking',
    'get_reschedule_slots': '/t2/api/get-reschedule-slots',
}

# Bucket system constants
BUCKET_DRAW_TIMEOUT_MINUTES = 5
MAX_DRAWS_BEFORE_RESET = 20
DEFAULT_CLOSER_PROBABILITY = 1.0


# ============================================================================
# TEMPLATE HELPERS
# ============================================================================

def get_api_urls_context() -> Dict:
    """
    Get API URL constants for Jinja2 templates

    Returns:
        Dictionary with API URLs

    Usage in templates:
        {{ T2_API_URLS.available_dates }}
    """
    return {'T2_API_URLS': BOOKING_API_ENDPOINTS}


# NOTE: Phase 4-6 will extract more utilities from t2_legacy.py as patterns emerge
