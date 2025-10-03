# -*- coding: utf-8 -*-
"""
Central Business Tool Hub - Main Dashboard Blueprint
Landing Page mit Tool-Navigation und Overview
"""

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from datetime import datetime, timedelta
import json
import logging

# Blueprint erstellen
hub_bp = Blueprint('hub', __name__)

# Logger konfigurieren
logger = logging.getLogger(__name__)

@hub_bp.route('/')
def dashboard():
    """
    Central Hub Dashboard - Landing Page
    Zeigt alle verfügbaren Tools und Quick-Stats
    """
    user = session.get('user')

    # Wenn nicht eingeloggt, zur Login-Seite weiterleiten
    if not user:
        return redirect(url_for('auth.login', next=request.url))

    # Dashboard-Daten sammeln
    dashboard_data = get_dashboard_data(user)

    return render_template('hub/dashboard.html', **dashboard_data)


@hub_bp.route('/api/dashboard-stats')
def api_dashboard_stats():
    """
    API-Endpoint für Dashboard-Statistiken
    Für AJAX-Updates der Dashboard-Widgets
    """
    user = session.get('user')

    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    stats = get_live_stats(user)
    return jsonify(stats)


@hub_bp.route('/api/notifications')
def api_notifications():
    """
    API-Endpoint für Benutzer-Benachrichtigungen
    """
    user = session.get('user')

    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    notifications = get_user_notifications_detailed(user)
    return jsonify(notifications)


@hub_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def api_mark_notification_read(notification_id):
    """
    Benachrichtigung als gelesen markieren
    """
    user = session.get('user')

    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    success = mark_notification_read(user, notification_id)
    return jsonify({'success': success})


@hub_bp.route('/tool/<tool_id>')
def tool_redirect(tool_id):
    """
    Smart-Redirect zu Tools mit Tool-ID
    """
    user = session.get('user')

    if not user:
        return redirect(url_for('auth.login', next=request.url))

    # Tool-URL-Mapping
    tool_urls = {
        'slots': '/slots/',
        't2': '/t2/',
        'analytics': '/analytics/',
        'tool4': '#',
        'tool5': '#',
        'tool6': '#'
    }

    url = tool_urls.get(tool_id)
    if not url or url == '#':
        return render_template('hub/tool_not_available.html', tool_id=tool_id)

    return redirect(url)


def get_dashboard_data(username):
    """
    Dashboard-Daten für Benutzer sammeln
    """
    # Basis-Informationen
    dashboard_data = {
        'user': username,
        'current_time': datetime.now(),
        'greeting': get_time_based_greeting(),
        'is_admin': is_admin_user(username),
        'app_version': '3.2',
        'current_year': datetime.now().year
    }

    # Quick-Stats
    dashboard_data['quick_stats'] = get_quick_stats(username)

    # Verfügbare Tools
    dashboard_data['tools'] = get_user_tools(username)

    # Letzte Aktivitäten
    dashboard_data['recent_activities'] = get_recent_activities(username)

    # System-Status
    dashboard_data['system_status'] = get_system_status()

    # Benachrichtigungen
    dashboard_data['notifications'] = get_user_notifications_detailed(username)

    # Gamification-Overview (falls eingeloggt in Slots)
    dashboard_data['gamification'] = get_gamification_overview(username)

    return dashboard_data


def get_time_based_greeting():
    """
    Zeitbasierte Begrüßung
    """
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return "Guten Morgen"
    elif 12 <= hour < 18:
        return "Guten Tag"
    elif 18 <= hour < 22:
        return "Guten Abend"
    else:
        return "Gute Nacht"


def get_quick_stats(username):
    """
    Quick-Statistics für Dashboard
    """
    stats = {
        'total_tools': len(get_user_tools(username)),
        'active_tools': len([t for t in get_user_tools(username) if t['status'] == 'active']),
        'unread_notifications': get_unread_notification_count(username),
        'last_activity': session.get('last_activity', datetime.now().isoformat())
    }

    # Tool-spezifische Stats
    if has_tool_access(username, 'slots'):
        slots_stats = get_slots_stats(username)
        stats.update(slots_stats)

    if has_tool_access(username, 't2'):
        t2_stats = get_t2_stats(username)
        stats.update(t2_stats)

    return stats


def get_user_tools(username):
    """
    Tools für Benutzer basierend auf Berechtigungen
    """
    all_tools = [
        {
            'id': 'slots',
            'name': 'Slot-Booking',
            'description': 'Terminbuchungs-System',
            'icon': '🎯',
            'url': '/slots/',
            'status': 'active',
            'users': 25,
            'color': '#2196F3',
            'features': ['Terminbuchung', 'Kalender-View', 'Gamification'],
            'last_used': get_tool_last_used(username, 'slots')
        },
        {
            'id': 't2',
            'name': 'T2-Closer',
            'description': 'T2-Termin-Management',
            'icon': '👥',
            'url': '/t2/',
            'status': 'active',
            'users': 8,
            'color': '#4CAF50',
            'features': ['2h-Termine', '6 Closer', 'Analytics'],
            'last_used': get_tool_last_used(username, 't2')
        },
        {
            'id': 'analytics',
            'name': 'Analytics',
            'description': 'Business Intelligence',
            'icon': '📊',
            'url': '/analytics/',
            'status': 'coming_soon',
            'users': 0,
            'color': '#FF9800',
            'features': ['Reports', 'KPIs', 'Forecasting'],
            'last_used': None
        },
        {
            'id': 'tool4',
            'name': 'Tool #4',
            'description': 'Coming Soon',
            'icon': '🔧',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#9E9E9E',
            'features': ['TBD'],
            'last_used': None
        },
        {
            'id': 'tool5',
            'name': 'Tool #5',
            'description': 'Coming Soon',
            'icon': '⚙️',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#9E9E9E',
            'features': ['TBD'],
            'last_used': None
        },
        {
            'id': 'tool6',
            'name': 'Tool #6',
            'description': 'Coming Soon',
            'icon': '🚀',
            'url': '#',
            'status': 'coming_soon',
            'users': 0,
            'color': '#9E9E9E',
            'features': ['TBD'],
            'last_used': None
        }
    ]

    # Berechtigungen prüfen
    user_tools = [tool for tool in all_tools if has_tool_access(username, tool['id'])]

    return user_tools


def get_recent_activities(username):
    """
    Letzte Aktivitäten des Benutzers
    """
    # Hier würde später echtes Activity-Tracking implementiert
    activities = [
        {
            'id': 1,
            'type': 'booking',
            'tool': 'slots',
            'action': 'Termin gebucht',
            'details': '15:00 - 16:00 Uhr',
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'icon': '📅'
        },
        {
            'id': 2,
            'type': 'gamification',
            'tool': 'slots',
            'action': 'Badge erhalten',
            'details': 'Pünktlichkeits-Meister',
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
            'icon': '🏆'
        },
        {
            'id': 3,
            'type': 'login',
            'tool': 'hub',
            'action': 'Anmeldung',
            'details': 'Dashboard aufgerufen',
            'timestamp': datetime.now().isoformat(),
            'icon': '🔓'
        }
    ]

    return activities[:5]  # Nur die letzten 5


def get_system_status():
    """
    System-Status für Dashboard
    """
    return {
        'overall': 'healthy',
        'services': {
            'hub': 'healthy',
            'slots': 'healthy',
            't2': 'healthy',
            'auth': 'healthy',
            'api': 'healthy'
        },
        'uptime': '99.9%',
        'response_time': '< 200ms'
    }


def get_gamification_overview(username):
    """
    Gamification-Overview für Dashboard
    """
    # Hier würden echte Gamification-Daten geladen
    return {
        'level': 15,
        'xp': 3750,
        'xp_next_level': 4000,
        'badges_count': 12,
        'recent_badge': {
            'name': 'Termintreu',
            'rarity': 'rare',
            'icon': '⭐'
        },
        'daily_streak': 7,
        'points_today': 125
    }


def get_slots_stats(username):
    """
    Slots-spezifische Statistiken
    """
    return {
        'slots_total_bookings': 47,
        'slots_this_week': 3,
        'slots_success_rate': 95.5
    }


def get_t2_stats(username):
    """
    T2-spezifische Statistiken
    """
    return {
        't2_total_sessions': 12,
        't2_this_month': 4,
        't2_avg_duration': '1.8h'
    }


def get_user_notifications_detailed(username):
    """
    Detaillierte Benachrichtigungen für Benutzer
    """
    notifications = [
        {
            'id': 1,
            'type': 'info',
            'title': 'Willkommen im Tool Hub!',
            'message': 'Du hast jetzt Zugang zu allen Business-Tools.',
            'timestamp': datetime.now().isoformat(),
            'read': False,
            'actions': []
        },
        {
            'id': 2,
            'type': 'success',
            'title': 'T2-System verfügbar',
            'message': 'Das neue T2-Closer-System ist jetzt live!',
            'timestamp': (datetime.now() - timedelta(hours=3)).isoformat(),
            'read': False,
            'actions': [{'text': 'T2 öffnen', 'url': '/t2/'}]
        }
    ]

    return notifications


def get_unread_notification_count(username):
    """
    Anzahl ungelesener Benachrichtigungen
    """
    notifications = get_user_notifications_detailed(username)
    return len([n for n in notifications if not n['read']])


def get_tool_last_used(username, tool_id):
    """
    Letzter Zugriff auf Tool
    """
    # Dummy-Implementation
    if tool_id == 'slots':
        return (datetime.now() - timedelta(hours=2)).isoformat()
    elif tool_id == 't2':
        return (datetime.now() - timedelta(days=1)).isoformat()

    return None


def get_live_stats(username):
    """
    Live-Statistiken für AJAX-Updates
    """
    return {
        'timestamp': datetime.now().isoformat(),
        'active_users': 12,
        'system_load': 23.5,
        'response_time': 156,
        'tools_online': 6
    }


def has_tool_access(username, tool_id):
    """
    Prüfen ob Benutzer Tool-Zugang hat
    """
    try:
        # Admin-Benutzer laden
        from app.config.base import Config
        admin_users = Config.get_admin_users()
    except:
        admin_users = ['admin', 'Jose', 'Simon', 'Alex', 'David']  # Fallback

    # Admins haben Zugang zu allen Tools
    if username in admin_users:
        return True

    # Standard-Benutzer haben Zugang zu Slots und T2
    if tool_id in ['slots', 't2']:
        return True

    # Andere Tools nur für Admins
    return False


def is_admin_user(username):
    """
    Prüfen ob Benutzer Admin ist
    """
    try:
        from app.config.base import Config
        admin_users = Config.get_admin_users()
        return username in admin_users
    except:
        return username in ['admin', 'Jose', 'Simon', 'Alex', 'David']


def mark_notification_read(username, notification_id):
    """
    Benachrichtigung als gelesen markieren
    """
    # Hier würde später echte Persistierung implementiert
    logger.info(f"Notification {notification_id} marked as read for user {username}")
    return True


@hub_bp.route('/profile')
def profile():
    """
    Benutzerprofil-Seite
    """
    user = session.get('user')

    if not user:
        return redirect(url_for('auth.login', next=request.url))

    # Profil-Daten sammeln
    profile_data = {
        'user': user,
        'is_admin': is_admin_user(user),
        'stats': get_user_profile_stats(user),
        'tools_access': get_user_tools(user),
        'recent_activities': get_recent_activities(user),
        'app_version': '3.2',
        'current_year': datetime.now().year
    }

    return render_template('hub/profile.html', **profile_data)


@hub_bp.route('/settings')
def settings():
    """
    Benutzer-Einstellungen
    """
    user = session.get('user')

    if not user:
        return redirect(url_for('auth.login', next=request.url))

    settings_data = {
        'user': user,
        'is_admin': is_admin_user(user),
        'current_settings': get_user_settings(user),
        'app_version': '3.2',
        'current_year': datetime.now().year
    }

    return render_template('hub/settings.html', **settings_data)


@hub_bp.route('/settings/update', methods=['POST'])
def update_settings():
    """
    Einstellungen aktualisieren
    """
    user = session.get('user')

    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    # Settings aus Request
    settings = request.json

    # Settings speichern (später mit echtem Persistenz-Layer)
    success = save_user_settings(user, settings)

    return jsonify({'success': success})


def get_user_profile_stats(username):
    """
    Statistiken für Benutzerprofil
    """
    return {
        'total_logins': 127,
        'account_created': '2024-01-15',
        'last_login': datetime.now().isoformat(),
        'tools_used': len(get_user_tools(username)),
        'total_actions': 450
    }


def get_user_settings(username):
    """
    Benutzereinstellungen laden
    """
    # Default-Settings
    return {
        'theme': 'dark',
        'notifications': True,
        'email_notifications': True,
        'dashboard_layout': 'grid',
        'language': 'de'
    }


def save_user_settings(username, settings):
    """
    Benutzereinstellungen speichern
    """
    logger.info(f"Saving settings for user {username}: {settings}")
    # Hier würde später echte Persistierung implementiert
    return True