# -*- coding: utf-8 -*-
"""
T2 Shared Utilities - Common Helpers for T2 Blueprints

MIGRATED FROM: t2_legacy.py (Phase 4)
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, Optional, Tuple, List
import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Europe/Berlin")


# ============================================================================
# T2 CONFIGURATION (from t2_legacy.py line 75-82)
# ============================================================================

T2_CONFIG = {
    "slot_duration_minutes": 120,
    "booking_hours": ["09:00", "11:00", "14:00", "16:00", "18:00"],
    "working_days": [1, 2, 3, 4, 5],  # Mo-Fr
    "max_advance_days": 14,
    "min_notice_hours": 24,
    "tickets_per_month": 4,  # Max 4 T2-Termine pro Monat
}


# ============================================================================
# ADMIN & USER CHECKS (from t2_legacy.py line 795-821)
# ============================================================================

def is_admin_user(username: str) -> bool:
    """
    Admin-Check

    MIGRATED FROM: t2_legacy.py line 795
    """
    try:
        from app.config.base import Config
        return username in Config.get_admin_users()
    except:
        return username in ['admin', 'Jose', 'Simon', 'Alex', 'David']


def is_closer(username: str) -> bool:
    """
    Check if user is a closer

    MIGRATED FROM: t2_legacy.py line 815
    """
    CLOSERS_LIST = ["Jose", "Alexander", "David"]
    return username in CLOSERS_LIST


def is_opener(username: str) -> bool:
    """
    Check if user is an opener

    MIGRATED FROM: t2_legacy.py line 819
    """
    return not is_closer(username)


# ============================================================================
# TICKET MANAGEMENT (from t2_legacy.py line 407-456)
# ============================================================================

def get_user_tickets_remaining(username: str) -> int:
    """
    Verbleibende Tickets für User diesen Monat

    MIGRATED FROM: t2_legacy.py line 407
    """
    try:
        from app.services.data_persistence import data_persistence

        current_month = datetime.now().strftime('%Y-%m')
        ticket_data = data_persistence.load_data('t2_tickets', {})

        user_tickets = ticket_data.get(username, {})
        month_tickets = user_tickets.get(current_month, {})

        used = month_tickets.get('used', 0)
        total = T2_CONFIG['tickets_per_month']

        return max(0, total - used)

    except Exception as e:
        logger.error(f"Error getting user tickets: {e}")
        return T2_CONFIG['tickets_per_month']


def consume_user_ticket(username: str):
    """
    Ticket verbrauchen

    MIGRATED FROM: t2_legacy.py line 428
    """
    try:
        from app.services.data_persistence import data_persistence

        current_month = datetime.now().strftime('%Y-%m')
        ticket_data = data_persistence.load_data('t2_tickets', {})

        if username not in ticket_data:
            ticket_data[username] = {}

        if current_month not in ticket_data[username]:
            ticket_data[username][current_month] = {'used': 0}

        ticket_data[username][current_month]['used'] += 1

        data_persistence.save_data('t2_tickets', ticket_data)

        logger.info(f"Ticket consumed for {username} in {current_month}")

    except Exception as e:
        logger.error(f"Error consuming ticket: {e}")


def get_next_ticket_reset() -> str:
    """
    Nächstes Ticket-Reset-Datum

    MIGRATED FROM: t2_legacy.py line 452
    """
    now = datetime.now()
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    return next_month.strftime('%d.%m.%Y')


# ============================================================================
# BOOKING FUNCTIONS (from t2_legacy.py line 602-668)
# ============================================================================

def load_t2_bookings() -> List[Dict]:
    """
    Alle T2-Buchungen laden (PostgreSQL-first, JSON fallback)

    Strategy:
    1. Try PostgreSQL (if enabled)
    2. Fallback to JSON if PostgreSQL fails or disabled

    MIGRATED FROM: t2_legacy.py line 602
    """
    try:
        from app.models import T2Booking, get_db_session, is_postgres_enabled

        # TRY POSTGRESQL FIRST
        if is_postgres_enabled():
            try:
                session = get_db_session()
                if session:
                    bookings = session.query(T2Booking).all()
                    session.close()

                    # Convert to dict format
                    result = [booking.to_dict() for booking in bookings]
                    logger.debug(f"✅ Loaded {len(result)} T2 bookings from PostgreSQL")
                    return result
            except Exception as e:
                logger.error(f"⚠️ PostgreSQL load failed for T2 bookings: {e}")
                # Fallback to JSON

        # FALLBACK TO JSON
        from app.services.data_persistence import data_persistence
        bookings_data = data_persistence.load_data('t2_bookings', {'bookings': []})
        # Handle both list and dict formats
        if isinstance(bookings_data, dict):
            result = bookings_data.get('bookings', [])
        else:
            result = bookings_data  # Legacy list format

        logger.debug(f"⚠️ Loaded {len(result)} T2 bookings from JSON (fallback)")
        return result
    except Exception as e:
        logger.error(f"Error loading bookings: {e}")
        return []


def get_user_t2_bookings(username: str) -> List[Dict]:
    """
    Benutzer-T2-Buchungen

    MIGRATED FROM: t2_legacy.py line 645
    """
    bookings = load_t2_bookings()
    user_bookings = [b for b in bookings if b.get('user') == username]

    # Nach Datum sortieren
    user_bookings.sort(key=lambda x: x.get('date', ''), reverse=True)

    return user_bookings


def get_next_t2_appointments(username: str) -> List[Dict]:
    """
    Nächste T2-Termine

    MIGRATED FROM: t2_legacy.py line 656
    """
    bookings = get_user_t2_bookings(username)
    today = date.today().isoformat()

    future_bookings = [
        b for b in bookings
        if b.get('date', '') >= today and b.get('status') == 'confirmed'
    ]

    future_bookings.sort(key=lambda x: (x.get('date', ''), x.get('time', '')))

    return future_bookings[:5]


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
    # Stub for Phase 5
    logger.warning("parse_appointment_datetime - stub implementation")
    return None


def format_berlin_datetime(dt: datetime) -> str:
    """
    Format datetime to Berlin timezone string

    Args:
        dt: datetime object

    Returns:
        ISO format string with Berlin timezone
    """
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
    # Stub for Phase 5
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
    logger.info(f"Bucket draw - user: {username}, result: {result.get('closer', 'unknown')}")


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
