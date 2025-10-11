# -*- coding: utf-8 -*-
"""
T2-Closer-System Blueprint
Random Closer-Zuweisung mit Bucket-System und Ticket-Management
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta, date
import json
import logging
import random
from typing import Dict, List, Optional
from collections import defaultdict

t2_bp = Blueprint('t2', __name__, url_prefix='/t2')
logger = logging.getLogger(__name__)

# Register bucket system routes
from app.routes.t2_bucket_routes import register_bucket_routes
register_bucket_routes(t2_bp)

# T2-Closer-Konfiguration
T2_CLOSERS = {
    "Alexander": {
        "calendar_id": "qfcpmp08okjoljs3noupl64m2c@group.calendar.google.com",
        "email": "alexander@domain.de",
        "color": "#FF5722"
    },
    "Christian": {
        "calendar_id": "chmast95@gmail.com",
        "email": "chmast95@gmail.com",
        "color": "#4CAF50"
    },
    "Daniel": {
        "calendar_id": "daniel.herbort.zfa@gmail.com",
        "email": "daniel.herbort.zfa@gmail.com",
        "color": "#2196F3"
    },
    "David": {
        "calendar_id": "david.nehm@googlemail.com",
        "email": "david.nehm@googlemail.com",
        "color": "#9C27B0"
    },
    "Tim": {
        "calendar_id": "tim.kreisel71@gmail.com",
        "email": "tim.kreisel71@gmail.com",
        "color": "#FF9800"
    },
    "Jose": {
        "calendar_id": "jtldiw@gmail.com",
        "email": "jtldiw@gmail.com",
        "color": "#795548"
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

from app.utils.decorators import require_login

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


@t2_bp.route("/api/roll-closer", methods=['POST'])
@require_login
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


@t2_bp.route("/booking")
@require_login
def booking_page():
    """T2-Buchungsseite - vereinfacht ohne Closer-Auswahl"""
    user = session.get('user')

    # Aktuell zugewiesener Closer
    assigned_closer = session.get('t2_current_closer')
    if not assigned_closer:
        # Automatisch einen Closer zuweisen
        assigned_closer = assign_fair_closer(user)
        session['t2_current_closer'] = assigned_closer

    tickets_remaining = get_user_tickets_remaining(user)

    if tickets_remaining <= 0:
        return render_template('t2/no_tickets.html',
                             user=user,
                             next_reset=get_next_ticket_reset())

    return render_template('t2/booking.html',
                         user=user,
                         assigned_closer=assigned_closer,
                         closer_info=T2_CLOSERS[assigned_closer],
                         tickets_remaining=tickets_remaining,
                         config=T2_CONFIG,
                         datetime=datetime,
                         timedelta=timedelta)


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


@t2_bp.route("/stats")
@require_login
def stats_page():
    """T2-Statistiken"""
    user = session.get('user')
    is_admin = is_admin_user(user)

    stats_data = get_stats_data(user, is_admin)

    return render_template('t2/stats.html',
                         user=user,
                         is_admin=is_admin,
                         **stats_data)


# ========== API-ENDPOINTS ==========

@t2_bp.route("/api/book", methods=['POST'])
@require_login
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

        bookings = data_persistence.load_data('t2_bookings', [])

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
        # TODO: Echte Google Calendar-Integration
        # Aktuell: Mock mit Random
        import random
        available = random.random() > 0.3

        available_slots.append({
            'time': time_str,
            'duration': 120,
            'available': available
        })

    return available_slots


# ========== DATENBANK-OPERATIONEN ==========

def save_t2_booking(booking_data: Dict):
    """Buchung speichern"""
    try:
        from app.services.data_persistence import data_persistence

        bookings = data_persistence.load_data('t2_bookings', [])
        bookings.append(booking_data)
        data_persistence.save_data('t2_bookings', bookings)

        logger.info(f"T2 booking saved: {booking_data['id']}")

    except Exception as e:
        logger.error(f"Error saving booking: {e}")
        raise


def load_t2_bookings() -> List[Dict]:
    """Alle T2-Buchungen laden"""
    try:
        from app.services.data_persistence import data_persistence
        return data_persistence.load_data('t2_bookings', [])
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
CLOSERS_LIST = ["Jose", "Alexander", "David", "Daniel", "Christian", "Tim"]

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
