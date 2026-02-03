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
# T2 CLOSERS CONFIGURATION (from t2_legacy.py line 27-73)
# ============================================================================

T2_CLOSERS = {
    # === COACHES (würfelbar) - MIT Schreibrechten ===
    "David": {
        "calendar_id": "david.nehm@googlemail.com",
        "email": "david.nehm@googlemail.com",
        "role": "coach",
        "can_write": True,  # Coaches können eigene Termine buchen
        "color": "#9C27B0"
    },
    "Alex": {
        "calendar_id": "qfcpmp08okjoljs3noupl64m2c@group.calendar.google.com",  # Group Calendar
        "email": "alexandernehm84@gmail.com",
        "role": "coach",
        "can_write": True,  # Coaches können eigene Termine buchen
        "color": "#2196F3"
    },
    "Jose": {
        "calendar_id": "jtldiw@gmail.com",
        "email": "jtldiw@gmail.com",
        "role": "coach",
        "can_write": True,  # Coaches können eigene Termine buchen
        "color": "#795548"
    },

    # === BERATER (ausführend) - MIT Schreibrechten ===
    "Christian": {
        "calendar_id": "chmast95@gmail.com",
        "email": "chmast95@gmail.com",
        "role": "berater",
        "can_write": True,
        "color": "#4CAF50"
    },
    "Daniel": {
        "calendar_id": "daniel.herbort.zfa@gmail.com",
        "email": "daniel.herbort.zfa@gmail.com",
        "role": "berater",
        "can_write": True,
        "color": "#FF9800"
    },
    "Tim": {
        "calendar_id": "tim.kreisel71@gmail.com",
        "email": "tim.kreisel71@gmail.com",
        "role": "berater",
        "can_write": True,
        "color": "#00BCD4"
    }
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


def return_user_ticket(username: str):
    """
    Gibt Ticket zurück nach Stornierung.

    Reduziert used-Counter um 1 für aktuellen Monat.

    MIGRATED FROM: t2_legacy.py line 685
    """
    try:
        from app.services.data_persistence import data_persistence

        current_month = datetime.now().strftime('%Y-%m')
        ticket_data = data_persistence.load_data('t2_tickets', {})

        if username in ticket_data and current_month in ticket_data[username]:
            current_used = ticket_data[username][current_month].get('used', 0)
            ticket_data[username][current_month]['used'] = max(0, current_used - 1)

            data_persistence.save_data('t2_tickets', ticket_data)

            logger.info(f"Ticket returned for {username} in {current_month} (new used: {ticket_data[username][current_month]['used']})")
        else:
            logger.warning(f"No ticket data found for {username} in {current_month}")

    except Exception as e:
        logger.error(f"Error returning ticket: {e}")


def get_next_ticket_reset() -> str:
    """
    Nächstes Ticket-Reset-Datum

    MIGRATED FROM: t2_legacy.py line 452
    """
    now = datetime.now()
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    return next_month.strftime('%d.%m.%Y')


# ============================================================================
# BOOKING FUNCTIONS (from t2_legacy.py line 533-668)
# ============================================================================

def save_t2_booking(booking_data: Dict):
    """
    Buchung speichern (DUAL-WRITE: PostgreSQL + JSON)

    Strategy:
    1. Try PostgreSQL (if enabled)
    2. Always write to JSON as backup
    3. Log if PostgreSQL fails but continue with JSON

    MIGRATED FROM: t2_legacy.py line 533
    """
    try:
        from app.services.data_persistence import data_persistence
        from app.models import T2Booking, get_db_session, is_postgres_enabled
        from datetime import datetime

        # WRITE TO POSTGRESQL FIRST
        postgres_success = False
        if is_postgres_enabled():
            try:
                session = get_db_session()
                if session:
                    # Convert booking_data to T2Booking model
                    booking = T2Booking(
                        booking_id=booking_data['id'],
                        coach=booking_data.get('coach', ''),
                        berater=booking_data.get('berater', ''),
                        customer=booking_data.get('customer', ''),
                        date=datetime.strptime(booking_data['date'], '%Y-%m-%d').date() if booking_data.get('date') else None,
                        time=booking_data.get('time', ''),
                        topic=booking_data.get('topic', ''),
                        email=booking_data.get('email', ''),
                        user=booking_data.get('user', ''),
                        event_id=booking_data.get('event_id'),
                        calendar_id=booking_data.get('calendar_id'),
                        status=booking_data.get('status', 'active'),
                        is_rescheduled_from=booking_data.get('is_rescheduled_from')
                        # Note: created_at/updated_at are set automatically by Base class
                    )

                    session.add(booking)
                    session.commit()
                    postgres_success = True
                    logger.info(f"✅ T2 booking saved to PostgreSQL: {booking_data['id']}")
                    session.close()
            except Exception as e:
                logger.error(f"⚠️ PostgreSQL save failed for T2 booking {booking_data['id']}: {e}")
                # Continue to JSON fallback

        # ALWAYS WRITE TO JSON (Backup)
        bookings_data = data_persistence.load_data('t2_bookings', {'bookings': []})
        # Handle both list and dict formats
        if isinstance(bookings_data, dict):
            bookings = bookings_data.get('bookings', [])
        else:
            bookings = bookings_data  # Legacy list format

        bookings.append(booking_data)
        # Always save in dict format
        data_persistence.save_data('t2_bookings', {'bookings': bookings})

        if postgres_success:
            logger.info(f"✅ T2 booking saved (PostgreSQL + JSON): {booking_data['id']}")
        else:
            logger.info(f"⚠️ T2 booking saved (JSON only): {booking_data['id']}")

    except Exception as e:
        logger.error(f"Error saving booking: {e}")
        raise


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


def can_modify_booking(booking: Dict, username: str) -> bool:
    """
    Prüft ob User berechtigt ist Buchung zu ändern/stornieren.

    Args:
        booking: Buchungs-Dictionary
        username: Aktueller User

    Returns:
        True wenn User = Booker ODER User = Admin

    MIGRATED FROM: t2_legacy.py line 671
    """
    return booking.get('user') == username or is_admin_user(username)


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
    """
    try:
        appointment_date = datetime.fromisoformat(date_str).date()
        hour, minute = map(int, time_str.split(':'))

        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return None

        naive_dt = datetime.combine(appointment_date, datetime.min.time().replace(hour=hour, minute=minute))
        return TZ.localize(naive_dt)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid date/time: date_str={date_str}, time_str={time_str}: {e}")
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
        data: Request data dictionary with keys: first_name, last_name, date, time, berater/coach

    Returns:
        (is_valid: bool, error_message: str)
    """
    if not data:
        return False, "No data provided"

    # Required fields
    required = ['first_name', 'last_name', 'date', 'time']
    for field in required:
        if not data.get(field):
            return False, f"{field} is required"

    # Validate date format
    try:
        booking_date = datetime.fromisoformat(data['date']).date()
        if booking_date < date.today():
            return False, "Cannot book in the past"
    except ValueError:
        return False, "Invalid date format (expected YYYY-MM-DD)"

    # Validate time format
    try:
        hour, minute = map(int, data['time'].split(':'))
        if hour < 8 or hour > 20:
            return False, "Time must be between 08:00 and 20:00"
    except (ValueError, AttributeError):
        return False, "Invalid time format (expected HH:MM)"

    # Validate berater if provided
    if data.get('berater') and data['berater'] not in T2_CLOSERS:
        return False, f"Invalid berater: {data['berater']}"

    if data.get('coach') and data['coach'] not in T2_CLOSERS:
        return False, f"Invalid coach: {data['coach']}"

    return True, ""


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
