# -*- coding: utf-8 -*-
"""
T2-Closer-System Blueprint
Random Closer-Zuweisung mit Bucket-System und Ticket-Management
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime, timedelta, date
import json
import logging
import random
import uuid
from typing import Dict, List, Optional
from collections import defaultdict
from app.core.extensions import csrf

t2_bp = Blueprint('t2', __name__, url_prefix='/t2')
logger = logging.getLogger(__name__)

# Register bucket system routes
from app.routes.t2_bucket_routes import register_bucket_routes
register_bucket_routes(t2_bp)

# T2-Closer-Konfiguration
# COACHES (würfelbar) - Aktuell KEINE Schreibrechte (bis nach Wochenende)
# BERATER (ausführend) - MIT Schreibrechten
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

T2_CONFIG = {
    "slot_duration_minutes": 120,
    "booking_hours": ["09:00", "11:00", "14:00", "16:00", "18:00"],
    "working_days": [1, 2, 3, 4, 5],  # Mo-Fr
    "max_advance_days": 14,
    "min_notice_hours": 24,
    "tickets_per_month": 4,  # Max 4 T2-Termine pro Monat
}

# ========== HELPER FUNCTIONS ==========

def get_coaches() -> List[str]:
    """
    Gibt Liste aller Coaches zurück (würfelbar).
    Coaches sind: David, Alexander, Jose
    """
    return [name for name, info in T2_CLOSERS.items() if info.get('role') == 'coach']


def get_beraters() -> List[str]:
    """
    Gibt Liste aller Berater zurück (können Termine ausführen).
    Berater sind: Alle 6 Closer (Christian, Daniel, Tim + David, Alexander, Jose)
    """
    return list(T2_CLOSERS.keys())


def get_available_beraters() -> List[str]:
    """
    Gibt Liste aller Berater mit Google Calendar Schreibrechten zurück.
    Aktuell: Christian, Daniel, Tim
    """
    return [name for name, info in T2_CLOSERS.items() if info.get('can_write', False)]


def is_mock_required(closer_name: str) -> bool:
    """
    Prüft ob für Closer ein Mock nötig ist (keine Schreibrechte).

    Args:
        closer_name: Name des Closers

    Returns:
        True wenn Mock nötig (keine Schreibrechte), False sonst
    """
    if closer_name not in T2_CLOSERS:
        return True
    return not T2_CLOSERS[closer_name].get('can_write', False)


from app.utils.decorators import require_login
from app.utils.rate_limiting import rate_limit_t2, rate_limit_api
from app.services.t2_analytics_service import t2_analytics_service
from app.services.t2_dynamic_availability import t2_dynamic_availability
from app.services.tracking_system import tracking_system
from app.core.google_calendar import GoogleCalendarService
from app.services.data_persistence import data_persistence

# ========== HAUPTROUTEN ==========

@t2_bp.route("/")
@require_login
def dashboard():
    """T2-Dashboard mit Würfel-System"""
    user = session.get('user')

    dashboard_data = {
        'user': user,
        'is_admin': is_admin_user(user),
        'tickets_remaining': get_user_tickets_remaining(user),
        'tickets_total': T2_CONFIG['tickets_per_month'],
        'user_bookings': get_user_t2_bookings(user),
        'next_appointments': get_next_t2_appointments(user),
        'current_assigned_closer': session.get('t2_current_closer'),
    }

    return render_template('t2/dashboard.html', **dashboard_data)


@csrf.exempt
@t2_bp.route("/api/roll-closer", methods=['POST'])
@require_login
@rate_limit_api
def api_roll_closer():
    """Neuen Closer würfeln mit Fairness-System"""
    try:
        user = session.get('user')

        # Fairness-Algorithmus: Closer mit wenigsten Buchungen bevorzugen
        assigned_closer = assign_fair_closer(user)

        # In Session speichern
        session['t2_current_closer'] = assigned_closer

        closer_info = T2_CLOSERS[assigned_closer]

        return jsonify({
            'success': True,
            'closer': assigned_closer,
            'color': closer_info['color']
        })

    except Exception as e:
        logger.error(f"Error rolling closer: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/booking-calendly")
@require_login
def booking_calendly():
    """
    Neue Calendly-Style T2-Buchungsseite.

    Flow:
    1. Berater-Auswahl (nach Würfel)
    2. Monats-Kalender
    3. 2h-Slot-Auswahl (gruppiert)
    4. Kundeninfo-Formular
    """
    user = session.get('user')

    # Check: Coach wurde gewürfelt?
    coach = session.get('t2_current_closer')
    logger.info(f"Booking access: user={user}, coach={coach}, session_keys={list(session.keys())}")

    if not coach or coach not in T2_CLOSERS:
        logger.warning(f"Missing/invalid coach in session: coach={coach}, in_T2_CLOSERS={coach in T2_CLOSERS if coach else False}")
        flash('Bitte ziehe zuerst einen Coach im Würfelsystem.', 'warning')
        return redirect(url_for('t2.draw_page'))

    # Check: Tickets verfügbar?
    tickets_remaining = get_user_tickets_remaining(user)
    if tickets_remaining <= 0:
        return render_template('t2/no_tickets.html',
                             user=user,
                             next_reset=get_next_ticket_reset())

    return render_template('t2/booking_calendly.html',
                         user=user,
                         coach=coach,
                         T2_CLOSERS=T2_CLOSERS,
                         tickets_remaining=tickets_remaining)


@t2_bp.route("/calendar")
@require_login
def calendar_view():
    """Kalender-Übersicht für T2-Termine"""
    user = session.get('user')

    # Check if user is closer or opener
    user_is_closer = is_closer(user)

    # Get all closers list for dropdown
    closers_list = list(T2_CLOSERS.keys())

    # Nächste 30 Tage laden
    calendar_data = get_calendar_data(user)

    return render_template('t2/calendar.html',
                         user=user,
                         is_closer=user_is_closer,
                         closers_list=closers_list,
                         **calendar_data)


# DEPRECATED: Alte /stats Route wurde durch /my-analytics ersetzt
# @t2_bp.route("/stats")
# @require_login
# def stats_page():
#     """T2-Statistiken (DEPRECATED - use /my-analytics instead)"""
#     user = session.get('user')
#     is_admin = is_admin_user(user)
#     stats_data = get_stats_data(user, is_admin)
#     return render_template('t2/stats.html',
#                          user=user,
#                          is_admin=is_admin,
#                          **stats_data)


# ========== API-ENDPOINTS ==========

@csrf.exempt
@t2_bp.route("/api/book", methods=['POST'])
@require_login
@rate_limit_t2
def api_book_slot():
    """T2-Termin buchen mit zugewiesenem Closer"""
    try:
        user = session.get('user')
        data = request.get_json()

        # Zugewiesener Closer aus Session
        assigned_closer = session.get('t2_current_closer')
        if not assigned_closer:
            return jsonify({
                'success': False,
                'error': 'Kein Closer zugewiesen. Bitte würfeln.'
            }), 400

        # Tickets prüfen
        tickets_remaining = get_user_tickets_remaining(user)
        if tickets_remaining <= 0:
            return jsonify({
                'success': False,
                'error': 'Keine Tickets mehr verfügbar'
            }), 403

        date_str = data.get('date')
        time_str = data.get('time')
        topic = data.get('topic', '')

        if not all([date_str, time_str]):
            return jsonify({
                'success': False,
                'error': 'Datum und Uhrzeit erforderlich'
            }), 400

        # Buchung durchführen
        result = book_t2_slot(user, assigned_closer, date_str, time_str, topic)

        if result['success']:
            # Ticket verbrauchen
            consume_user_ticket(user)

            # Assigned Closer aus Session entfernen
            session.pop('t2_current_closer', None)

            logger.info(f"T2 booking: {user} -> {assigned_closer} on {date_str} {time_str}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"T2 booking error: {e}")
        return jsonify({
            'success': False,
            'error': 'Buchungsfehler'
        }), 500


@t2_bp.route("/api/availability/<date_str>")
@require_login
def api_availability(date_str):
    """Verfügbare Zeitslots für Datum (unabhängig vom Closer)"""
    try:
        assigned_closer = session.get('t2_current_closer')
        if not assigned_closer:
            return jsonify({'success': False, 'error': 'Kein Closer zugewiesen'}), 400

        slots = get_closer_availability(assigned_closer, date_str)

        return jsonify({
            'success': True,
            'date': date_str,
            'closer': assigned_closer,
            'slots': slots
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== FAIRNESS-SYSTEM ==========

def assign_fair_closer(username: str) -> str:
    """
    Fairen Closer zuweisen basierend auf Monats-Statistiken
    Ziel: Am Monatsende sollten alle Closer gleich viele Termine haben
    """
    current_month = datetime.now().strftime('%Y-%m')

    # Buchungen diesen Monat pro Closer laden
    monthly_stats = get_monthly_closer_stats(current_month)

    # Closer nach Anzahl Termine sortieren (aufsteigend)
    closer_bookings = [
        (closer, monthly_stats.get(closer, 0))
        for closer in T2_CLOSERS.keys()
    ]
    closer_bookings.sort(key=lambda x: x[1])

    # Closer mit wenigsten Terminen bevorzugen (Weighted Random)
    weights = []
    total_bookings = sum(count for _, count in closer_bookings)

    for closer, count in closer_bookings:
        # Invertierte Gewichtung: Weniger Termine = höhere Chance
        max_weight = len(T2_CLOSERS) * 10
        weight = max_weight - count
        weights.append(weight)

    # Weighted Random Selection
    selected_closer = random.choices(
        [c for c, _ in closer_bookings],
        weights=weights,
        k=1
    )[0]

    logger.info(f"Assigned closer {selected_closer} to {username} (fairness: {monthly_stats})")

    return selected_closer


def get_monthly_closer_stats(month_str: str) -> Dict[str, int]:
    """Anzahl Termine pro Closer im Monat"""
    try:
        from app.services.data_persistence import data_persistence

        bookings_data = data_persistence.load_data('t2_bookings', {'bookings': []})
        # Handle both list and dict formats
        if isinstance(bookings_data, dict):
            bookings = bookings_data.get('bookings', [])
        else:
            bookings = bookings_data  # Legacy list format

        stats = defaultdict(int)
        for booking in bookings:
            booking_date = booking.get('date', '')
            if booking_date.startswith(month_str):
                closer = booking.get('closer')
                if closer:
                    stats[closer] += 1

        return dict(stats)

    except Exception as e:
        logger.error(f"Error loading monthly stats: {e}")
        return {}


# ========== TICKET-SYSTEM ==========

def get_user_tickets_remaining(username: str) -> int:
    """Verbleibende Tickets für User diesen Monat"""
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
    """Ticket verbrauchen"""
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
    """Nächstes Ticket-Reset-Datum"""
    now = datetime.now()
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    return next_month.strftime('%d.%m.%Y')


# ========== BUCHUNGSLOGIK ==========

def book_t2_slot(username: str, closer_name: str, date_str: str, time_str: str, topic: str) -> Dict:
    """T2-Slot buchen"""
    try:
        booking_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        # Validierungen
        min_notice = datetime.now() + timedelta(hours=T2_CONFIG['min_notice_hours'])
        if booking_datetime < min_notice:
            return {
                'success': False,
                'error': f'Mindestvorlaufzeit: {T2_CONFIG["min_notice_hours"]} Stunden'
            }

        # Verfügbarkeit prüfen
        availability = get_closer_availability(closer_name, date_str)
        slot_available = any(
            slot['time'] == time_str and slot['available']
            for slot in availability
        )

        if not slot_available:
            return {
                'success': False,
                'error': 'Zeitslot nicht verfügbar'
            }

        # Buchung speichern
        booking_data = {
            'id': generate_booking_id(),
            'user': username,
            'closer': closer_name,
            'date': date_str,
            'time': time_str,
            'duration': 120,
            'topic': topic,
            'status': 'confirmed',
            'created_at': datetime.now().isoformat(),
        }

        save_t2_booking(booking_data)

        return {
            'success': True,
            'booking_id': booking_data['id'],
            'booking': booking_data
        }

    except Exception as e:
        logger.error(f"Booking error: {e}")
        return {
            'success': False,
            'error': 'Fehler beim Buchen'
        }


def get_closer_availability(closer_name: str, date_str: str) -> List[Dict]:
    """Verfügbarkeit für Closer und Datum"""
    available_slots = []

    for time_str in T2_CONFIG['booking_hours']:
        # Alle Slots verfügbar (kein Google Calendar für T2)
        available_slots.append({
            'time': time_str,
            'duration': 120,
            'available': True
        })

    return available_slots


# ========== DATENBANK-OPERATIONEN ==========

def save_t2_booking(booking_data: Dict):
    """Buchung speichern"""
    try:
        from app.services.data_persistence import data_persistence

        bookings_data = data_persistence.load_data('t2_bookings', {'bookings': []})
        # Handle both list and dict formats
        if isinstance(bookings_data, dict):
            bookings = bookings_data.get('bookings', [])
        else:
            bookings = bookings_data  # Legacy list format

        bookings.append(booking_data)
        # Always save in dict format
        data_persistence.save_data('t2_bookings', {'bookings': bookings})

        logger.info(f"T2 booking saved: {booking_data['id']}")

    except Exception as e:
        logger.error(f"Error saving booking: {e}")
        raise


def load_t2_bookings() -> List[Dict]:
    """Alle T2-Buchungen laden"""
    try:
        from app.services.data_persistence import data_persistence
        bookings_data = data_persistence.load_data('t2_bookings', {'bookings': []})
        # Handle both list and dict formats
        if isinstance(bookings_data, dict):
            return bookings_data.get('bookings', [])
        else:
            return bookings_data  # Legacy list format
    except:
        return []


def get_user_t2_bookings(username: str) -> List[Dict]:
    """Benutzer-T2-Buchungen"""
    bookings = load_t2_bookings()
    user_bookings = [b for b in bookings if b.get('user') == username]

    # Nach Datum sortieren
    user_bookings.sort(key=lambda x: x.get('date', ''), reverse=True)

    return user_bookings


def get_next_t2_appointments(username: str) -> List[Dict]:
    """Nächste T2-Termine"""
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
    """
    return booking.get('user') == username or is_admin_user(username)


def return_user_ticket(username: str):
    """
    Gibt Ticket zurück nach Stornierung.

    Reduziert used-Counter um 1 für aktuellen Monat.
    """
    try:
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


# ========== STATISTIKEN ==========

def get_calendar_data(username: str) -> Dict:
    """Kalender-Daten für 30 Tage"""
    user_bookings = get_user_t2_bookings(username)

    # Nächste 30 Tage
    calendar_days = []
    today = date.today()

    for day_offset in range(30):
        check_date = today + timedelta(days=day_offset)
        date_str = check_date.strftime('%Y-%m-%d')

        day_bookings = [
            b for b in user_bookings
            if b.get('date') == date_str
        ]

        calendar_days.append({
            'date': date_str,
            'date_obj': check_date,
            'weekday': check_date.weekday(),
            'bookings': day_bookings,
            'has_bookings': len(day_bookings) > 0
        })

    return {
        'calendar_days': calendar_days,
        'user_bookings': user_bookings
    }


def get_stats_data(username: str, is_admin: bool) -> Dict:
    """Statistik-Daten"""
    user_bookings = get_user_t2_bookings(username)

    # User Stats
    current_month = datetime.now().strftime('%Y-%m')
    month_bookings = [b for b in user_bookings if b.get('date', '').startswith(current_month)]

    # Closer-Verteilung
    closer_distribution = defaultdict(int)
    for booking in user_bookings:
        closer = booking.get('closer')
        if closer:
            closer_distribution[closer] += 1

    user_stats = {
        'total_bookings': len(user_bookings),
        'month_bookings': len(month_bookings),
        'tickets_remaining': get_user_tickets_remaining(username),
        'closer_distribution': dict(closer_distribution),
        'recent_bookings': user_bookings[:10]
    }

    # Admin Stats
    admin_stats = {}
    if is_admin:
        all_bookings = load_t2_bookings()
        monthly_closer_stats = get_monthly_closer_stats(current_month)

        # Current month closer distribution
        month_all_bookings = [b for b in all_bookings if b.get('date', '').startswith(current_month)]
        current_month_distribution = defaultdict(int)
        for booking in month_all_bookings:
            closer = booking.get('closer')
            if closer:
                current_month_distribution[closer] += 1

        admin_stats = {
            'total_system_bookings': len(all_bookings),
            'total_this_month': len(month_all_bookings),
            'current_month_distribution': dict(current_month_distribution),
            'monthly_closer_stats': monthly_closer_stats,
            'all_bookings': all_bookings[:50]
        }

    return {
        'user_stats': user_stats,
        'admin_stats': admin_stats
    }


# ========== HILFSFUNKTIONEN ==========

def is_admin_user(username: str) -> bool:
    """Admin-Check"""
    try:
        from app.config.base import Config
        return username in Config.get_admin_users()
    except:
        return username in ['admin', 'Jose', 'Simon', 'Alex', 'David']


def generate_booking_id() -> str:
    """Booking-ID generieren"""
    import uuid
    return f"T2-{uuid.uuid4().hex[:8].upper()}"


# ========== NEUE AVAILABILITY & CALENDAR API-ENDPOINTS ==========

# Closers list for role detection
CLOSERS_LIST = ["Jose", "Alexander", "David"]

def is_closer(username: str) -> bool:
    """Check if user is a closer"""
    return username in CLOSERS_LIST

def is_opener(username: str) -> bool:
    """Check if user is an opener"""
    return not is_closer(username)


@t2_bp.route("/api/availability-calendar/<closer_name>")
@require_login
def api_availability_calendar(closer_name):
    """
    Get 6-week availability calendar for a closer
    Returns dates with available slots (for green dots)
    """
    try:
        from app.services.t2_availability_service import availability_service

        if closer_name not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Unknown closer'}), 400

        # Get available dates (dates with at least one free slot)
        available_dates = availability_service.get_available_dates(closer_name, days=42)

        return jsonify({
            'success': True,
            'closer': closer_name,
            'available_dates': available_dates
        })

    except Exception as e:
        logger.error(f"Error getting availability calendar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/availability/<closer_name>/<date_str>")
@require_login
def api_availability_by_date(closer_name, date_str):
    """
    Get available time slots for specific closer and date
    Returns list of free 2h slots (09:00-22:00)
    """
    try:
        from app.services.t2_availability_service import availability_service

        if closer_name not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Unknown closer'}), 400

        # Get cached availability
        availability = availability_service.get_cached_availability(closer_name, date_str)
        closer_data = availability.get(closer_name, {})
        slots = closer_data.get(date_str, [])

        return jsonify({
            'success': True,
            'closer': closer_name,
            'date': date_str,
            'available_slots': slots
        })

    except Exception as e:
        logger.error(f"Error getting availability: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/my-calendar-events/<date_str>")
@require_login
def api_my_calendar_events(date_str):
    """
    Get closer's own calendar events for specific date
    Only accessible by closers
    """
    try:
        user = session.get('user')

        if not is_closer(user):
            return jsonify({'success': False, 'error': 'Not authorized - Closers only'}), 403

        from app.core.google_calendar import get_google_calendar_service
        from app.services.t2_calendar_parser import calendar_parser

        calendar_service = get_google_calendar_service()
        if not calendar_service:
            return jsonify({'success': False, 'error': 'Calendar service unavailable'}), 500

        # Get calendar ID for this closer
        closer_data = T2_CLOSERS.get(user)
        if not closer_data:
            return jsonify({'success': False, 'error': 'Closer calendar not found'}), 404

        calendar_id = closer_data['calendar_id']

        # Get events for this date
        start_time = f"{date_str}T00:00:00Z"
        end_time = f"{date_str}T23:59:59Z"

        result = calendar_service.get_events(
            calendar_id=calendar_id,
            time_min=start_time,
            time_max=end_time,
            cache_duration=1800  # 30min cache
        )

        events = result.get('items', []) if result else []

        # Classify events
        classified_events = [calendar_parser.classify_appointment(event) for event in events]

        return jsonify({
            'success': True,
            'date': date_str,
            'events': classified_events
        })

    except Exception as e:
        logger.error(f"Error getting calendar events: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/my-upcoming-events")
@require_login
def api_my_upcoming_events():
    """
    Get closer's next 5 upcoming appointments
    Only accessible by closers
    """
    try:
        user = session.get('user')

        if not is_closer(user):
            return jsonify({'success': False, 'error': 'Not authorized - Closers only'}), 403

        from app.core.google_calendar import get_google_calendar_service
        from app.services.t2_calendar_parser import calendar_parser

        calendar_service = get_google_calendar_service()
        if not calendar_service:
            return jsonify({'success': False, 'error': 'Calendar service unavailable'}), 500

        # Get calendar ID
        closer_data = T2_CLOSERS.get(user)
        if not closer_data:
            return jsonify({'success': False, 'error': 'Closer calendar not found'}), 404

        calendar_id = closer_data['calendar_id']

        # Get next 14 days of events
        start_time = datetime.now().isoformat() + 'Z'
        end_time = (datetime.now() + timedelta(days=14)).isoformat() + 'Z'

        result = calendar_service.get_events(
            calendar_id=calendar_id,
            time_min=start_time,
            time_max=end_time,
            max_results=10,
            cache_duration=1800
        )

        events = result.get('items', []) if result else []

        # Classify and limit to 5
        classified_events = [calendar_parser.classify_appointment(event) for event in events]
        upcoming = classified_events[:5]

        return jsonify({
            'success': True,
            'upcoming_events': upcoming
        })

    except Exception as e:
        logger.error(f"Error getting upcoming events: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/my-bookings")
@require_login
def api_my_bookings():
    """
    Get all bookings for current user (opener)
    Returns bookings from t2_bookings.json
    """
    try:
        user = session.get('user')

        # Get all user bookings
        bookings = get_user_t2_bookings(user)

        return jsonify({
            'success': True,
            'bookings': bookings
        })

    except Exception as e:
        logger.error(f"Error getting user bookings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/my-upcoming-bookings")
@require_login
def api_my_upcoming_bookings():
    """
    Get next 5 upcoming bookings for current user (opener)
    """
    try:
        user = session.get('user')

        # Get upcoming appointments
        upcoming = get_next_t2_appointments(user)

        return jsonify({
            'success': True,
            'upcoming_bookings': upcoming
        })

    except Exception as e:
        logger.error(f"Error getting upcoming bookings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== ANALYTICS ROUTES ==========

@t2_bp.route("/my-analytics")
@require_login
def my_analytics():
    """
    Personal Analytics Hub - Würfel-Historie, Combined Stats, Quick Links
    """
    user = session.get('user')

    # Get initial stats for page load
    draw_stats = t2_analytics_service.get_user_draw_stats(user)
    combined_stats = t2_analytics_service.get_combined_user_stats(user)

    return render_template('t2/analytics.html',
                         user=user,
                         is_admin=is_admin_user(user),
                         draw_stats=draw_stats,
                         combined_stats=combined_stats)


@t2_bp.route("/my-bookings")
@require_login
def my_bookings():
    """
    My T2 2-Hour Bookings Management Page
    View, cancel, and reschedule 2-hour appointments
    """
    user = session.get('user')

    return render_template('t2/my_bookings.html',
                         user=user,
                         is_admin=is_admin_user(user))


@t2_bp.route("/api/my-draw-history")
@require_login
def api_my_draw_history():
    """
    API: Get user's draw history with pagination and filters
    Query params: limit, offset, start_date, end_date, closer
    """
    try:
        user = session.get('user')

        # Parse query params
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        closer_filter = request.args.get('closer')

        # Get draw history
        history = t2_analytics_service.get_user_draw_history(
            username=user,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            closer_filter=closer_filter
        )

        return jsonify({
            'success': True,
            **history
        })

    except Exception as e:
        logger.error(f"Error getting draw history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/my-draw-stats")
@require_login
def api_my_draw_stats():
    """
    API: Get aggregated draw statistics for user
    """
    try:
        user = session.get('user')
        stats = t2_analytics_service.get_user_draw_stats(user)

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error getting draw stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/combined-stats")
@require_login
def api_combined_stats():
    """
    API: Get combined statistics (T1 Slots + T2 Bookings + Draw Activity)
    """
    try:
        user = session.get('user')
        combined = t2_analytics_service.get_combined_user_stats(user)

        return jsonify({
            'success': True,
            'stats': combined
        })

    except Exception as e:
        logger.error(f"Error getting combined stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/search-draws")
@require_login
def api_search_draws():
    """
    API: Search draws by customer name or closer name
    Query params: q (query string)
    """
    try:
        user = session.get('user')
        query = request.args.get('q', '')

        if not query or len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Query must be at least 2 characters'
            }), 400

        results = t2_analytics_service.search_draws(user, query)

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        logger.error(f"Error searching draws: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route("/api/draw-timeline")
@require_login
def api_draw_timeline():
    """
    API: Get draw timeline data for charts (last N days)
    Query params: days (default: 30)
    """
    try:
        user = session.get('user')
        days = int(request.args.get('days', 30))

        timeline = t2_analytics_service.get_draw_timeline_data(user, days)

        return jsonify({
            'success': True,
            **timeline
        })

    except Exception as e:
        logger.error(f"Error getting draw timeline: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== NEW CALENDLY-STYLE BOOKING API ENDPOINTS ==========

@csrf.exempt
@t2_bp.route('/api/select-berater', methods=['POST'])
@require_login
@rate_limit_api
def api_select_berater():
    """
    API: Speichert Berater-Auswahl nach Würfel.

    Request JSON:
        {"berater": "Christian"}

    Response:
        {"success": true}
    """
    try:
        user = session.get('user')
        data = request.json

        if not data or 'berater' not in data:
            return jsonify({'success': False, 'error': 'Berater required'}), 400

        berater = data['berater']

        # Validation
        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        # Coach aus Session holen (vom Würfel)
        coach = session.get('t2_current_closer')

        if not coach:
            return jsonify({'success': False, 'error': 'No coach assigned. Please roll first.'}), 400

        # Session speichern
        session['t2_booking_coach'] = coach
        session['t2_booking_berater'] = berater

        logger.info(f"User {user}: Selected berater {berater} for coach {coach}")

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error selecting berater: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route('/api/month-availability/<berater>/<int:year>/<int:month>')
@require_login
@rate_limit_api
def api_month_availability(berater, year, month):
    """
    API: Lädt Verfügbarkeit für ganzen Monat.

    URL Params:
        berater: Berater-Name (z.B. "Christian")
        year: Jahr (z.B. 2025)
        month: Monat 1-12 (z.B. 11)

    Response:
        {
            "success": true,
            "days": {
                "2025-11-25": 3,  # 3 freie Slots
                "2025-11-26": 1
            }
        }
    """
    try:
        user = session.get('user')

        # Validation
        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        if month < 1 or month > 12:
            return jsonify({'success': False, 'error': 'Invalid month'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']

        logger.info(f"User {user}: Loading month availability for {berater} ({year}-{month:02d})")

        # Scan Monat
        availability = t2_dynamic_availability.get_month_availability(calendar_id, year, month)

        return jsonify({
            'success': True,
            'days': availability,
            'total_days': len(availability)
        })

    except Exception as e:
        logger.error(f"Error loading month availability: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route('/api/day-slots/<berater>/<date_str>')
@require_login
@rate_limit_api
def api_day_slots(berater, date_str):
    """
    API: Lädt gruppierte 2h-Slots für einen Tag.

    URL Params:
        berater: Berater-Name (z.B. "Christian")
        date_str: Datum im ISO-Format (z.B. "2025-11-25")

    Response:
        {
            "success": true,
            "slots": {
                "morning": ["08:00", "10:30"],
                "midday": ["12:00", "14:00"],
                "evening": ["16:30", "18:00"]
            }
        }
    """
    try:
        user = session.get('user')

        # Validation
        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        # Parse Date
        try:
            check_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']

        logger.info(f"User {user}: Loading day slots for {berater} on {date_str}")

        # Scan Tag
        slots = t2_dynamic_availability.find_2h_slots_non_overlapping(calendar_id, check_date)

        total_slots = len(slots['morning']) + len(slots['midday']) + len(slots['evening'])

        return jsonify({
            'success': True,
            'slots': slots,
            'total_slots': total_slots
        })

    except Exception as e:
        logger.error(f"Error loading day slots: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@csrf.exempt
@t2_bp.route('/api/book-2h-slot', methods=['POST'])
@require_login
@rate_limit_api
def api_book_2h_slot():
    """
    API: Führt 2h-Slot-Buchung durch.

    Request JSON:
        {
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max@example.com",  # optional
            "topic": "Verkaufsgespräch",  # optional
            "date": "2025-11-25",
            "time": "14:00"
        }

    Response:
        {
            "success": true,
            "booking_id": "T2-ABC12345",
            "redirect": "/t2/"
        }
    """
    try:
        user = session.get('user')
        data = request.json

        # Validation
        required_fields = ['first_name', 'last_name', 'date', 'time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} required'}), 400

        # Primär aus Request-Body lesen (session-unabhängig), Session als Fallback
        coach = data.get('coach') or session.get('t2_booking_coach')
        berater = data.get('berater') or session.get('t2_booking_berater')

        if not coach or not berater:
            return jsonify({
                'success': False,
                'error': 'Booking-Daten fehlen. Bitte starten Sie den Buchungsprozess neu.'
            }), 400

        # Validation: Coach und Berater müssen in T2_CLOSERS existieren
        if coach not in T2_CLOSERS or berater not in T2_CLOSERS:
            return jsonify({
                'success': False,
                'error': 'Ungültiger Coach oder Berater.'
            }), 400

        # 1. Ticket-Check
        tickets_remaining = get_user_tickets_remaining(user)
        if tickets_remaining <= 0:
            return jsonify({
                'success': False,
                'error': 'Keine Tickets verfügbar. Sie haben bereits alle 4 T2-Termine diesen Monat gebucht.'
            }), 403

        # 2. Parse Date + Time
        try:
            booking_date = datetime.fromisoformat(data['date']).date()
            hour, minute = map(int, data['time'].split(':'))
            booking_datetime = datetime.combine(booking_date, datetime.min.time().replace(hour=hour, minute=minute))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date or time format'}), 400

        # 3. Live Slot-Check
        calendar_id = T2_CLOSERS[berater]['calendar_id']

        is_free = t2_dynamic_availability.is_2h_slot_free(calendar_id, booking_date, data['time'])

        if not is_free:
            # Spezifische Error-Message je nach Situation
            if coach == berater:
                # Coach wollte selbst ausführen, aber hat Konflikt in eigenem Kalender
                error_msg = (
                    f"{coach} hat zu diesem Zeitpunkt bereits einen Termin im Kalender. "
                    f"Bitte wählen Sie einen anderen Zeitpunkt oder übertragen Sie den Termin "
                    f"an Christian, Daniel oder Tim."
                )
            else:
                # Berater ist belegt
                error_msg = (
                    f"{berater} ist zu diesem Zeitpunkt nicht verfügbar. "
                    f"Bitte wählen Sie einen anderen Zeitpunkt oder einen anderen Berater."
                )

            logger.warning(f"Slot conflict for {berater} at {booking_date} {data['time']}: Coach={coach}, Berater={berater}")

            return jsonify({
                'success': False,
                'error': error_msg
            }), 409

        # 4. Google Calendar Event erstellen
        customer_name = f"{data['last_name']}, {data['first_name']}"
        end_datetime = booking_datetime + timedelta(hours=2)

        # Event-Titel
        if coach == berater:
            event_title = f"T2 - Kunde: {customer_name} | Coach: {coach}"
        else:
            event_title = f"T2 - Kunde: {customer_name} | Coach: {coach}"

        # Description
        description_parts = [
            "T2-Termin",
            "",
            f"Kunde: {customer_name}",
            f"Coach: {coach}",
            f"Berater: {berater}",
        ]

        if data.get('topic'):
            description_parts.append(f"Thema: {data['topic']}")

        if data.get('email'):
            description_parts.append(f"Email: {data['email']}")

        description_parts.append("")
        description_parts.append(f"[Booked by: {user}]")

        event_description = "\n".join(description_parts)

        # Timezone-aware datetime (Europe/Berlin)
        import pytz
        berlin_tz = pytz.timezone('Europe/Berlin')
        start_iso = berlin_tz.localize(booking_datetime).isoformat()
        end_iso = berlin_tz.localize(end_datetime).isoformat()

        event_body = {
            'summary': event_title,
            'description': event_description,
            'start': {'dateTime': start_iso, 'timeZone': 'Europe/Berlin'},
            'end': {'dateTime': end_iso, 'timeZone': 'Europe/Berlin'},
            'colorId': '4'  # Flamingo (T2-Farbe)
        }

        # Nur schreiben wenn can_write=True
        if T2_CLOSERS[berater].get('can_write', False):
            try:
                from app.utils.error_messages import get_error_message
                from app.utils.error_tracking import generate_error_id

                calendar_service = GoogleCalendarService()
                result, error_context = calendar_service.create_event_with_context(calendar_id, event_body)

                if result:
                    logger.info(f"Google Calendar event created: {result.get('id')}")
                else:
                    error_id = generate_error_id("CAL")
                    error_category = error_context.get('category', 'CALENDAR_UNAVAILABLE')
                    error_msg = get_error_message(error_category)
                    logger.error(f"Google Calendar event creation failed {error_id}: category={error_category}, details={error_context}")
                    return jsonify({'success': False, 'error': error_msg['message'], 'error_id': error_id}), 500

            except Exception as e:
                from app.utils.error_tracking import generate_error_id
                error_id = generate_error_id("CAL")
                logger.error(f"Google Calendar write failed {error_id}: {e}")
                return jsonify({'success': False, 'error': f'Calendar-Fehler', 'error_id': error_id}), 500
        else:
            logger.info(f"Mock booking for {berater} (no write access yet)")

        # 5. Tracking (Dual-Write)

        # A) T2-JSON speichern
        booking_id = f"T2-{uuid.uuid4().hex[:8].upper()}"

        t2_booking_data = {
            'id': booking_id,
            'coach': coach,
            'berater': berater,
            'customer': customer_name,
            'date': data['date'],
            'time': data['time'],
            'topic': data.get('topic', ''),
            'email': data.get('email', ''),
            'user': user,
            'created_at': datetime.now().isoformat()
        }

        save_t2_booking(t2_booking_data)

        # B) PostgreSQL + JSONL via tracking_system
        tracking_system.track_booking(
            customer_name=customer_name,
            date=data['date'],
            time_slot=data['time'],
            user=user,
            color_id='4',  # T2-Farbe
            description=f"T2 - Coach: {coach} | Berater: {berater} | {data.get('topic', '')}"
        )

        # 6. Ticket verbrauchen
        consume_user_ticket(user)

        # 7. Cache invalidieren
        t2_dynamic_availability.clear_cache_for_berater(calendar_id, booking_date)

        # 8. Session clearen
        session.pop('t2_current_closer', None)
        session.pop('t2_booking_coach', None)
        session.pop('t2_booking_berater', None)

        logger.info(f"T2 booking successful: {booking_id} by {user}")

        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'redirect': url_for('t2.dashboard')
        })

    except Exception as e:
        logger.error(f"Error booking 2h slot: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route('/api/check-coach-availability/<coach>/<int:year>/<int:month>')
@require_login
@rate_limit_api
def api_check_coach_availability(coach, year, month):
    """
    API: Prüft ob Coach im gewählten Monat selbst verfügbar ist.

    Verwendet für Berater-Konflikt-Detection in Step 1.

    URL Params:
        coach: Coach-Name (z.B. "David")
        year: Jahr (z.B. 2025)
        month: Monat 1-12 (z.B. 11)

    Response:
        {
            "success": true,
            "can_execute_self": true|false,
            "available_days": 8,
            "recommendation": "self|delegate",
            "message": "David hat 8 freie Tage und kann selbst ausführen."
        }
    """
    try:
        user = session.get('user')

        # Validation
        if coach not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid coach'}), 400

        if month < 1 or month > 12:
            return jsonify({'success': False, 'error': 'Invalid month'}), 400

        logger.info(f"User {user}: Checking coach availability for {coach} ({year}-{month:02d})")

        # Prüfe: Hat Coach überhaupt Schreibrechte?
        if not T2_CLOSERS[coach].get('can_write', False):
            return jsonify({
                'success': True,
                'can_execute_self': False,
                'available_days': 0,
                'recommendation': 'delegate',
                'message': f"{coach} hat derzeit keine Kalender-Zugriffe. Termin muss an Berater übertragen werden."
            })

        # Scan Coach-Kalender für Monat
        calendar_id = T2_CLOSERS[coach]['calendar_id']
        availability = t2_dynamic_availability.get_month_availability(calendar_id, year, month)
        available_days = len(availability)

        logger.info(f"Coach {coach} has {available_days} available days in {year}-{month:02d}")

        # Empfehlung basierend auf Verfügbarkeit
        if available_days >= 5:
            recommendation = 'self'
            message = f"{coach} hat {available_days} freie Tage und kann selbst ausführen."
            can_execute = True
        elif available_days >= 1:
            recommendation = 'delegate'
            message = f"{coach} hat nur {available_days} freie Tage. Empfehlung: An Berater (Christian/Daniel/Tim) übertragen."
            can_execute = True
        else:
            recommendation = 'delegate'
            message = f"{coach} hat keine freien Slots in diesem Monat. Bitte an Berater übertragen."
            can_execute = False

        return jsonify({
            'success': True,
            'can_execute_self': can_execute,
            'available_days': available_days,
            'recommendation': recommendation,
            'message': message
        })

    except Exception as e:
        logger.error(f"Error checking coach availability: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@t2_bp.route('/api/admin/2h-analytics')
@require_login
@rate_limit_api
def api_admin_2h_analytics():
    """
    API: Lädt 2h-Buchungs-Statistiken für Admin-Dashboard.

    Admin-only Endpoint für Analytics-Tab.

    Query Params:
        days (int): Anzahl Tage zurück (default: 30)

    Response:
        {
            "success": true,
            "analytics": {
                "berater_stats": {...},
                "coach_stats": {...},
                "overall": {...}
            }
        }
    """
    try:
        user = session.get('user')

        # Admin-Check
        if not is_admin_user(user):
            return jsonify({
                'success': False,
                'error': 'Admin-Berechtigung erforderlich'
            }), 403

        # Parse days parameter
        days = int(request.args.get('days', 30))

        # Berechne Zeitraum
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        logger.info(f"Admin {user}: Loading 2h analytics for {days} days ({start_date} to {end_date})")

        # Analytics laden
        analytics = t2_analytics_service.get_2h_booking_analytics(start_date, end_date)

        return jsonify({
            'success': True,
            'analytics': analytics,
            'time_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            }
        })

    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid days parameter'}), 400
    except Exception as e:
        logger.error(f"Error loading 2h analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== CANCELLATION & RESCHEDULE API ENDPOINTS ==========

@t2_bp.route('/api/my-2h-bookings')
@require_login
@rate_limit_api
def api_my_2h_bookings():
    """
    API: Lädt alle 2h-Buchungen für aktuellen User.

    Response:
        {
            "success": true,
            "bookings": [
                {
                    "id": "T2-ABC12345",
                    "date": "2025-11-25",
                    "time": "14:00",
                    "customer": "Mustermann, Max",
                    "coach": "David",
                    "berater": "Christian",
                    "status": "active",
                    "topic": "...",
                    "created_at": "..."
                }
            ]
        }
    """
    try:
        user = session.get('user')

        # Lade User-Buchungen
        bookings = get_user_t2_bookings(user)

        # Filter: Nur Buchungen mit allen nötigen Feldern
        valid_bookings = []
        for booking in bookings:
            if all(k in booking for k in ['id', 'date', 'time', 'customer']):
                valid_bookings.append({
                    'id': booking['id'],
                    'date': booking['date'],
                    'time': booking['time'],
                    'customer': booking['customer'],
                    'coach': booking.get('coach', 'Unknown'),
                    'berater': booking.get('berater', 'Unknown'),
                    'status': booking.get('status', 'active'),
                    'topic': booking.get('topic', ''),
                    'email': booking.get('email', ''),
                    'created_at': booking.get('created_at', '')
                })

        logger.info(f"User {user}: Loaded {len(valid_bookings)} T2 bookings")

        return jsonify({
            'success': True,
            'bookings': valid_bookings,
            'count': len(valid_bookings)
        })

    except Exception as e:
        logger.error(f"Error loading user bookings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@csrf.exempt
@t2_bp.route('/api/cancel-booking', methods=['POST'])
@require_login
@rate_limit_api
def api_cancel_booking():
    """
    API: Storniert eine T2-Buchung.

    Auth: User = Booker ODER User = Admin
    Ticket wird zurückgegeben.

    Request JSON:
        {"booking_id": "T2-ABC12345"}

    Response:
        {"success": true, "message": "Buchung storniert. Ticket zurückgegeben."}
    """
    try:
        user = session.get('user')
        data = request.json

        if not data or 'booking_id' not in data:
            return jsonify({'success': False, 'error': 'booking_id required'}), 400

        booking_id = data['booking_id']

        # Lade alle Buchungen
        all_bookings_data = data_persistence.load_data('t2_bookings', {'bookings': []})
        all_bookings = all_bookings_data.get('bookings', [])

        # Finde Buchung
        booking = None
        booking_index = None
        for i, b in enumerate(all_bookings):
            if b.get('id') == booking_id:
                booking = b
                booking_index = i
                break

        if not booking:
            return jsonify({'success': False, 'error': 'Buchung nicht gefunden'}), 404

        # Auth-Check
        if not can_modify_booking(booking, user):
            return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

        # Bereits storniert?
        if booking.get('status') == 'cancelled':
            return jsonify({'success': False, 'error': 'Buchung bereits storniert'}), 400

        # 1. Google Calendar Event löschen (wenn Berater Schreibrechte hat)
        berater = booking.get('berater')
        if berater and berater in T2_CLOSERS and T2_CLOSERS[berater].get('can_write', False):
            # TODO: Event löschen via Google Calendar API
            # calendar_service.delete_event(calendar_id, event_id)
            # Problem: Wir haben die event_id nicht gespeichert!
            logger.warning(f"Calendar deletion not implemented (missing event_id) for booking {booking_id}")
        else:
            logger.info(f"Skipping calendar deletion for {berater} (no write access or mock)")

        # 2. Status auf cancelled setzen
        all_bookings[booking_index]['status'] = 'cancelled'
        all_bookings[booking_index]['cancelled_at'] = datetime.now().isoformat()
        all_bookings[booking_index]['cancelled_by'] = user

        # Speichern
        data_persistence.save_data('t2_bookings', {'bookings': all_bookings})

        # 3. Ticket zurückgeben
        booking_user = booking.get('user')
        if booking_user:
            return_user_ticket(booking_user)

        # 4. Cache invalidieren
        booking_date_str = booking.get('date')
        if booking_date_str and berater and berater in T2_CLOSERS:
            try:
                booking_date = datetime.fromisoformat(booking_date_str).date()
                calendar_id = T2_CLOSERS[berater]['calendar_id']
                t2_dynamic_availability.clear_cache_for_berater(calendar_id, booking_date)
            except Exception as e:
                logger.warning(f"Cache clear failed: {e}")

        logger.info(f"User {user}: Cancelled booking {booking_id}")

        return jsonify({
            'success': True,
            'message': 'Buchung storniert. Ticket zurückgegeben.'
        })

    except Exception as e:
        logger.error(f"Error cancelling booking: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@csrf.exempt
@t2_bp.route('/api/reschedule-booking', methods=['POST'])
@require_login
@rate_limit_api
def api_reschedule_booking():
    """
    API: Bucht T2-Termin um.

    Auth: User = Booker ODER User = Admin
    Ticket wird NICHT zurückgegeben (bleibt verbraucht).

    Request JSON:
        {
            "booking_id": "T2-ABC12345",
            "new_date": "2025-11-26",
            "new_time": "16:00"
        }

    Response:
        {
            "success": true,
            "new_booking_id": "T2-XYZ67890",
            "message": "Buchung erfolgreich umgebucht."
        }
    """
    try:
        user = session.get('user')
        data = request.json

        # Validation
        required = ['booking_id', 'new_date', 'new_time']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} required'}), 400

        booking_id = data['booking_id']
        new_date_str = data['new_date']
        new_time_str = data['new_time']

        # Lade alle Buchungen
        all_bookings_data = data_persistence.load_data('t2_bookings', {'bookings': []})
        all_bookings = all_bookings_data.get('bookings', [])

        # Finde Buchung
        booking = None
        booking_index = None
        for i, b in enumerate(all_bookings):
            if b.get('id') == booking_id:
                booking = b
                booking_index = i
                break

        if not booking:
            return jsonify({'success': False, 'error': 'Buchung nicht gefunden'}), 404

        # Auth-Check
        if not can_modify_booking(booking, user):
            return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

        # Bereits storniert/umgebucht?
        if booking.get('status') in ['cancelled', 'rescheduled']:
            return jsonify({'success': False, 'error': 'Buchung wurde bereits storniert/umgebucht'}), 400

        # Parse new date/time
        try:
            new_date = datetime.fromisoformat(new_date_str).date()
            hour, minute = map(int, new_time_str.split(':'))
            new_datetime = datetime.combine(new_date, datetime.min.time().replace(hour=hour, minute=minute))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date or time format'}), 400

        # Live Slot-Check
        berater = booking.get('berater')
        if berater not in T2_CLOSERS:
            return jsonify({'success': False, 'error': 'Invalid berater'}), 400

        calendar_id = T2_CLOSERS[berater]['calendar_id']
        is_free = t2_dynamic_availability.is_2h_slot_free(calendar_id, new_date, new_time_str)

        if not is_free:
            return jsonify({
                'success': False,
                'error': f'{berater} ist am {new_date_str} um {new_time_str} nicht verfügbar.'
            }), 409

        # 1. Alte Buchung auf 'rescheduled' setzen
        all_bookings[booking_index]['status'] = 'rescheduled'
        all_bookings[booking_index]['rescheduled_at'] = datetime.now().isoformat()
        all_bookings[booking_index]['rescheduled_by'] = user
        all_bookings[booking_index]['rescheduled_to'] = new_date_str

        # 2. Neue Buchung erstellen
        coach = booking.get('coach')
        customer = booking.get('customer')
        topic = booking.get('topic', '')
        email = booking.get('email', '')

        new_booking_id = f"T2-{uuid.uuid4().hex[:8].upper()}"
        end_datetime = new_datetime + timedelta(hours=2)

        # Event-Titel
        if coach == berater:
            event_title = f"T2 - Kunde: {customer} | Coach: {coach}"
        else:
            event_title = f"T2 - Kunde: {customer} | Coach: {coach}"

        # Description
        import pytz
        berlin_tz = pytz.timezone('Europe/Berlin')
        start_iso = berlin_tz.localize(new_datetime).isoformat()
        end_iso = berlin_tz.localize(end_datetime).isoformat()

        event_body = {
            'summary': event_title,
            'description': f"T2-Termin (UMGEBUCHT)\n\nKunde: {customer}\nCoach: {coach}\nBerater: {berater}\nThema: {topic}\nEmail: {email}\n\n[Booked by: {booking.get('user')}]\n[Rescheduled by: {user}]",
            'start': {'dateTime': start_iso, 'timeZone': 'Europe/Berlin'},
            'end': {'dateTime': end_iso, 'timeZone': 'Europe/Berlin'},
            'colorId': '4'
        }

        # Google Calendar Event erstellen (wenn Schreibrechte)
        if T2_CLOSERS[berater].get('can_write', False):
            try:
                from app.utils.error_messages import get_error_message
                from app.utils.error_tracking import generate_error_id

                calendar_service = GoogleCalendarService()
                result, error_context = calendar_service.create_event_with_context(calendar_id, event_body)

                if result:
                    logger.info(f"New calendar event created for rescheduled booking: {result.get('id')}")
                else:
                    error_id = generate_error_id("CAL")
                    error_category = error_context.get('category', 'CALENDAR_UNAVAILABLE')
                    error_msg = get_error_message(error_category)
                    logger.error(f"Calendar event creation failed for reschedule {error_id}: category={error_category}, details={error_context}")
                    # Continue with booking anyway (calendar failure doesn't stop reschedule)
            except Exception as e:
                from app.utils.error_tracking import generate_error_id
                error_id = generate_error_id("CAL")
                logger.error(f"Calendar write failed {error_id}: {e}")
                # Continue with booking anyway
        else:
            logger.info(f"Mock reschedule for {berater} (no write access)")

        # Neue Buchung speichern
        new_booking = {
            'id': new_booking_id,
            'coach': coach,
            'berater': berater,
            'customer': customer,
            'date': new_date_str,
            'time': new_time_str,
            'topic': topic,
            'email': email,
            'user': booking.get('user'),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'is_rescheduled_from': booking_id
        }

        all_bookings.append(new_booking)

        # Speichern
        data_persistence.save_data('t2_bookings', {'bookings': all_bookings})

        # Tracking (PostgreSQL + JSONL)
        tracking_system.track_booking(
            customer_name=customer,
            date=new_date_str,
            time_slot=new_time_str,
            user=booking.get('user'),
            color_id='4',
            description=f"T2 - Coach: {coach} | Berater: {berater} | {topic} (UMGEBUCHT)"
        )

        # Cache invalidieren (alte + neue Slots)
        try:
            # Alte Buchung
            old_date = datetime.fromisoformat(booking['date']).date()
            t2_dynamic_availability.clear_cache_for_berater(calendar_id, old_date)
            # Neue Buchung
            t2_dynamic_availability.clear_cache_for_berater(calendar_id, new_date)
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")

        logger.info(f"User {user}: Rescheduled booking {booking_id} → {new_booking_id}")

        return jsonify({
            'success': True,
            'new_booking_id': new_booking_id,
            'message': 'Buchung erfolgreich umgebucht.'
        })

    except Exception as e:
        logger.error(f"Error rescheduling booking: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
