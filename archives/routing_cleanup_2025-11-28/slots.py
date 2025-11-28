# -*- coding: utf-8 -*-
"""
Slot-Booking System Blueprint
Integration der bestehenden Slot-Booking-App als Microservice unter /slots
"""

from flask import Blueprint, redirect, url_for, render_template, session, request, jsonify, make_response
from datetime import datetime, timedelta
import pytz
import logging

# Bestehende Services und Funktionen importieren
from app.config.base import slot_config
from app.services.booking_service import (
    load_availability,
    get_effective_availability,
    get_day_availability,
    get_slot_status,
    extract_weekly_summary,
    extract_detailed_summary,
    get_slot_suggestions
)
from app.utils.helpers import get_week_days, get_week_start, get_current_kw
from app.core.extensions import cache_manager, level_system
from app.utils.decorators import require_login
from app.utils.rate_limiting import rate_limit_booking, rate_limit_api

# Blueprint erstellen
slots_bp = Blueprint('slots', __name__, url_prefix='/slots')
TZ = pytz.timezone(slot_config.TIMEZONE)

logger = logging.getLogger(__name__)

# ========== HAUPTROUTEN ==========

@slots_bp.route("/")
@require_login
def index():
    """
    Slots-Dashboard - Hauptseite der Slot-Booking-App
    Zeigt Übersicht und leitet zu heutigem Tag weiter
    """
    user = session.get('user')
    logger.info(f"User {user} accessed slots dashboard")

    # Heute als Default-Tag
    today = datetime.today().strftime("%Y-%m-%d")

    # Dashboard-Daten sammeln
    dashboard_data = get_slots_dashboard_data(user)

    return render_template('slots/dashboard.html', **dashboard_data)


@slots_bp.route("/day/<date_str>")
@require_login
def day_view(date_str):
    """Display day view with available slots"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("slots.day_view", date_str=datetime.today().strftime("%Y-%m-%d")))

    # Load availability data (needed for summary calculations regardless of caching)
    availability = load_availability()

    # Check cache for effective availability
    effective_availability = get_day_availability(date_str)

    # Get weekly data for navigation and summary
    current_week_start = get_week_start(date_obj)
    week_days = get_week_days(current_week_start)

    current_kw = get_current_kw(date_obj)

    # Get summaries
    weekly_summary = extract_weekly_summary(availability, current_week_start)
    detailed_summary = extract_detailed_summary(availability, current_week_start)

    # Get slot suggestions
    suggestions = get_slot_suggestions(date_str)

    # Gamification data
    gamification_data = get_user_gamification_data(session.get('user'))

    return render_template('slots/day_view.html',
                         date_str=date_str,
                         date_obj=date_obj,
                         effective_availability=effective_availability,
                         week_days=week_days,
                         current_week_start=current_week_start,
                         current_kw=current_kw,
                         weekly_summary=weekly_summary,
                         detailed_summary=detailed_summary,
                         suggestions=suggestions,
                         **gamification_data)


# ========== BUCHUNGSROUTEN ==========

@slots_bp.route('/booking')
@require_login
def booking_page():
    """Buchungsseite anzeigen"""
    return render_template('slots/booking.html')


@slots_bp.route('/book', methods=['POST'])
@require_login
@rate_limit_booking
def book_slot():
    """Slot buchen - AJAX-Endpoint"""
    try:
        user = session.get('user')
        data = request.json or {}

        date_str = data.get('date')
        time_str = data.get('time')
        berater = data.get('berater')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        description = data.get('description', '')
        color_id = data.get('color_id', '9')

        # Import booking service for actual booking
        from app.services.booking_service import book_slot_for_user

        result = book_slot_for_user(
            user=user,
            date_str=date_str,
            time_str=time_str,
            berater=berater,
            first_name=first_name,
            last_name=last_name,
            description=description,
            color_id=color_id
        )

        if result.get('success'):
            logger.info(f"Successful booking by {user}: {date_str} {time_str} with {berater}")
            return jsonify(result)
        else:
            logger.warning(f"Failed booking attempt by {user}: {result.get('error')}")
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Booking error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== KALENDER-ROUTES ==========

@slots_bp.route('/calendar')
@require_login
def calendar_view():
    """Kalender-Ansicht"""
    return render_template('slots/calendar.html')


@slots_bp.route('/calendar/<date_str>')
@require_login
def calendar_day(date_str):
    """Kalender für spezifischen Tag"""
    return day_view(date_str)  # Weiterleitung zur day_view


# ========== GAMIFICATION-ROUTES ==========

@slots_bp.route('/gamification')
@require_login
def gamification():
    """Gamification-Dashboard"""
    user = session.get('user')

    # Gamification-Daten laden
    try:
        from app.services.achievement_system import achievement_system
        from app.services.level_system import level_system as level_svc

        user_data = {
            'badges': achievement_system.get_user_badges(user),
            'level': level_svc.get_user_level(user),
            'achievements': achievement_system.get_user_achievements(user),
            'progress': achievement_system.get_user_progress(user),
            'leaderboard': achievement_system.get_leaderboard(),
        }
    except ImportError as e:
        logger.warning(f"Gamification services not available: {e}")
        user_data = {}

    return render_template('slots/gamification.html', **user_data)


# ========== SCOREBOARD-ROUTES ==========

@slots_bp.route('/scoreboard')
@require_login
def scoreboard():
    """Scoreboard/Leaderboard anzeigen"""
    try:
        from app.services.achievement_system import achievement_system

        leaderboard_data = {
            'weekly': achievement_system.get_weekly_leaderboard(),
            'monthly': achievement_system.get_monthly_leaderboard(),
            'all_time': achievement_system.get_all_time_leaderboard(),
        }
    except ImportError:
        leaderboard_data = {}

    return render_template('slots/scoreboard.html', **leaderboard_data)


# ========== PROFIL-ROUTES ==========

@slots_bp.route('/profile')
@require_login
def profile():
    """Benutzerprofil anzeigen"""
    user = session.get('user')

    # Profil-Daten sammeln
    profile_data = get_user_profile_data(user)

    return render_template('slots/profile.html', **profile_data)


@slots_bp.route('/profile/update', methods=['POST'])
@require_login
def update_profile():
    """Profil aktualisieren"""
    user = session.get('user')

    # Profil-Update-Logic hier
    # TODO: Implementation

    return jsonify({'success': True, 'message': 'Profil aktualisiert'})


# ========== API-ROUTES ==========

@slots_bp.route('/api/availability/<date_str>')
@require_login
def api_availability(date_str):
    """API: Verfügbarkeit für spezifischen Tag"""
    try:
        availability = get_day_availability(date_str)
        return jsonify({'success': True, 'availability': availability})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@slots_bp.route('/api/user-stats')
@require_login
def api_user_stats():
    """API: Benutzer-Statistiken"""
    user = session.get('user')

    try:
        stats = get_user_stats(user)
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@slots_bp.route('/api/quick-book', methods=['POST'])
@require_login
@rate_limit_api
def api_quick_book():
    """API: Schnellbuchung"""
    try:
        user = session.get('user')
        data = request.get_json()

        # Quick-Book-Logic
        result = perform_quick_booking(user, data)

        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== ADMIN-ROUTES (für Slots-spezifische Admin-Features) ==========

@slots_bp.route('/admin')
@require_login
def slots_admin():
    """Slots-spezifische Admin-Funktionen"""
    user = session.get('user')

    # Admin-Check
    if not is_admin_user(user):
        return redirect(url_for('slots.index'))

    admin_data = get_slots_admin_data()

    return render_template('slots/admin.html', **admin_data)


# ========== HILFSFUNKTIONEN ==========

def get_slots_dashboard_data(username):
    """Dashboard-Daten für Slots-App sammeln"""
    data = {
        'user': username,
        'current_date': datetime.now().date(),
        'is_admin': is_admin_user(username),
    }

    try:
        # Verfügbarkeit laden
        availability = load_availability()

        # Quick-Stats berechnen
        data['stats'] = {
            'total_bookings': calculate_user_bookings(username),
            'this_week': calculate_weekly_bookings(username),
            'success_rate': calculate_success_rate(username),
            'next_appointment': get_next_appointment(username),
        }

        # Letzte Aktivitäten
        data['recent_bookings'] = get_recent_bookings(username)

        # Gamification-Overview
        data['gamification'] = get_user_gamification_data(username)

    except Exception as e:
        logger.error(f"Error loading dashboard data: {e}")
        data['stats'] = {}
        data['recent_bookings'] = []
        data['gamification'] = {}

    return data


def get_user_gamification_data(username):
    """Gamification-Daten für Benutzer laden"""
    try:
        from app.services.achievement_system import achievement_system
        from app.services.level_system import level_system as level_svc

        user_level = level_svc.get_user_level(username)
        user_xp = level_svc.get_user_xp(username)

        # XP für nächstes Level berechnen
        xp_next_level = level_svc.get_xp_for_level(user_level + 1) if hasattr(level_svc, 'get_xp_for_level') else user_xp + 1000

        return {
            'level': user_level,
            'xp': user_xp,
            'xp_next_level': xp_next_level,
            'badges': achievement_system.get_user_badges(username),
            'recent_achievements': achievement_system.get_recent_achievements(username),
        }
    except Exception as e:
        logger.warning(f"Could not load gamification data: {e}")
        return {
            'level': 1,
            'xp': 0,
            'xp_next_level': 1000,
            'badges': [],
            'recent_achievements': []
        }


def get_user_profile_data(username):
    """Profil-Daten für Benutzer sammeln"""
    return {
        'username': username,
        'is_admin': is_admin_user(username),
        'stats': get_user_stats(username),
        'preferences': get_user_preferences(username),
        'activity': get_user_activity_history(username),
    }


def get_user_stats(username):
    """Benutzer-Statistiken berechnen"""
    return {
        'total_bookings': calculate_user_bookings(username),
        'successful_bookings': calculate_successful_bookings(username),
        'cancelled_bookings': calculate_cancelled_bookings(username),
        'no_shows': calculate_no_shows(username),
        'success_rate': calculate_success_rate(username),
        'average_booking_time': calculate_avg_booking_time(username),
        'favorite_berater': get_favorite_berater(username),
        'member_since': get_member_since_date(username),
    }


def get_slots_admin_data():
    """Admin-Daten für Slots-System"""
    try:
        return {
            'total_users': get_total_users_count(),
            'total_bookings': get_total_bookings_count(),
            'availability_stats': get_availability_statistics(),
            'berater_stats': get_berater_statistics(),
            'system_health': get_slots_system_health(),
        }
    except Exception as e:
        logger.error(f"Error loading admin data: {e}")
        return {}


def is_admin_user(username):
    """Prüfen ob Benutzer Admin-Rechte hat"""
    try:
        from app.config.base import Config
        admin_users = Config.get_admin_users()
        return username in admin_users
    except:
        return username in ['admin', 'Jose', 'Simon', 'Alex', 'David']


# ========== DUMMY-IMPLEMENTIERUNGEN (später durch echte Services ersetzen) ==========

def calculate_user_bookings(username):
    """Gesamtanzahl Buchungen für Benutzer"""
    return 47  # Dummy

def calculate_weekly_bookings(username):
    """Buchungen diese Woche"""
    return 3  # Dummy

def calculate_success_rate(username):
    """Erfolgsrate der Buchungen"""
    return 95.5  # Dummy

def get_next_appointment(username):
    """Nächster Termin"""
    return {
        'date': '2024-10-15',
        'time': '14:00',
        'berater': 'Sara'
    }  # Dummy

def get_recent_bookings(username):
    """Letzte Buchungen"""
    return []  # Dummy

def get_user_preferences(username):
    """Benutzer-Einstellungen"""
    return {}  # Dummy

def get_user_activity_history(username):
    """Aktivitätsverlauf"""
    return []  # Dummy

def perform_quick_booking(username, data):
    """Schnellbuchung durchführen"""
    return {'success': True, 'message': 'Buchung erfolgreich'}  # Dummy

def calculate_successful_bookings(username):
    return 44  # Dummy

def calculate_cancelled_bookings(username):
    return 2  # Dummy

def calculate_no_shows(username):
    return 1  # Dummy

def calculate_avg_booking_time(username):
    return "14:30"  # Dummy

def get_favorite_berater(username):
    return "Sara"  # Dummy

def get_member_since_date(username):
    return "2024-01-15"  # Dummy

def get_total_users_count():
    return 25  # Dummy

def get_total_bookings_count():
    return 1247  # Dummy

def get_availability_statistics():
    return {}  # Dummy

def get_berater_statistics():
    return {}  # Dummy

def get_slots_system_health():
    return {'status': 'healthy'}  # Dummy