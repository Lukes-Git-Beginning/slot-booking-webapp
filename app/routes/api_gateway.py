# -*- coding: utf-8 -*-
"""
API Gateway Blueprint
Zentrale API-Schnittstelle für alle Tools im Business Hub
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, Any, Optional

# Blueprint erstellen
api_gateway_bp = Blueprint('api_gateway', __name__, url_prefix='/api/v1')

logger = logging.getLogger(__name__)

from app.utils.decorators import require_login

# ========== CROSS-TOOL APIS ==========

@api_gateway_bp.route("/tools/status")
@require_login
def tools_status():
    """
    Status aller verfügbaren Tools abrufen
    """
    try:
        tools_status = get_all_tools_status()

        return jsonify({
            'success': True,
            'tools': tools_status,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting tools status: {e}")
        return jsonify({'error': str(e)}), 500


@api_gateway_bp.route("/user/dashboard-data")
@require_login
def user_dashboard_data():
    """
    Gesammelte Dashboard-Daten für alle Tools
    """
    try:
        user = session.get('user')

        dashboard_data = {
            'user': user,
            'tools': get_user_accessible_tools(user),
            'notifications': get_user_notifications(user),
            'quick_stats': get_cross_tool_stats(user),
            'recent_activity': get_recent_activity(user),
            'gamification': get_user_gamification_summary(user)
        }

        return jsonify({
            'success': True,
            'data': dashboard_data,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({'error': str(e)}), 500


# ========== UNIFIED BOOKING API ==========

@api_gateway_bp.route("/booking/availability/<date_str>")
@require_login
def unified_availability(date_str):
    """
    Vereinheitlichte Verfügbarkeits-API für alle Buchungssysteme
    """
    try:
        tool = request.args.get('tool', 'all')  # slots, t2, all

        availability_data = {}

        if tool in ['all', 'slots']:
            # Slot-System Verfügbarkeit
            from app.routes.slots import get_effective_availability
            slots_availability = get_effective_availability(date_str)
            availability_data['slots'] = slots_availability

        if tool in ['all', 't2']:
            # T2-System Verfügbarkeit
            from app.routes.t2 import get_available_t2_slots
            t2_slots = get_available_t2_slots()
            availability_data['t2'] = t2_slots.get(date_str, {})

        return jsonify({
            'success': True,
            'date': date_str,
            'availability': availability_data
        })

    except Exception as e:
        logger.error(f"Error getting unified availability: {e}")
        return jsonify({'error': str(e)}), 500


@api_gateway_bp.route("/booking/create", methods=['POST'])
@require_login
def unified_booking():
    """
    Vereinheitlichte Buchungs-API
    """
    try:
        user = session.get('user')
        data = request.get_json()

        booking_system = data.get('system')  # 'slots' oder 't2'

        if not booking_system:
            return jsonify({'error': 'Booking system not specified'}), 400

        if booking_system == 'slots':
            from app.routes.slots import book_slot
            result = book_slot()

        elif booking_system == 't2':
            from app.routes.t2 import api_book_slot
            result = api_book_slot()

        else:
            return jsonify({'error': 'Unknown booking system'}), 400

        # Log successful booking
        if hasattr(result, 'json') and result.json.get('success'):
            log_cross_tool_activity(user, 'booking_created', {
                'system': booking_system,
                'date': data.get('date'),
                'time': data.get('time')
            })

        return result

    except Exception as e:
        logger.error(f"Error with unified booking: {e}")
        return jsonify({'error': str(e)}), 500


# ========== NOTIFICATIONS API ==========

@api_gateway_bp.route("/notifications")
@require_login
def user_notifications():
    """
    Benutzer-Benachrichtigungen von allen Tools
    """
    try:
        user = session.get('user')

        notifications = {
            'unread_count': get_unread_notifications_count(user),
            'notifications': get_user_notifications(user),
            'system_alerts': get_system_alerts()
        }

        return jsonify({
            'success': True,
            'data': notifications
        })

    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return jsonify({'error': str(e)}), 500


@api_gateway_bp.route("/notifications/<notification_id>/mark-read", methods=['POST'])
@require_login
def mark_notification_read(notification_id):
    """
    Benachrichtigung als gelesen markieren
    """
    try:
        user = session.get('user')

        result = mark_notification_as_read(user, notification_id)

        return jsonify({
            'success': result,
            'message': 'Notification marked as read' if result else 'Notification not found'
        })

    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({'error': str(e)}), 500


# ========== ANALYTICS & STATS API ==========

@api_gateway_bp.route("/analytics/overview")
@require_login
def analytics_overview():
    """
    Analytics-Übersicht für alle Tools
    """
    try:
        user = session.get('user')
        is_admin = is_admin_user(user)

        analytics_data = {
            'user_stats': get_user_analytics(user),
            'tool_usage': get_tool_usage_stats(user),
            'performance': get_user_performance_stats(user)
        }

        if is_admin:
            analytics_data['system_stats'] = get_system_analytics()

        return jsonify({
            'success': True,
            'data': analytics_data,
            'is_admin': is_admin
        })

    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        return jsonify({'error': str(e)}), 500


@api_gateway_bp.route("/analytics/tool/<tool_name>")
@require_login
def tool_analytics(tool_name):
    """
    Tool-spezifische Analytics
    """
    try:
        user = session.get('user')

        if tool_name == 'slots':
            from app.routes.slots import get_user_stats
            stats = get_user_stats(user)

        elif tool_name == 't2':
            from app.routes.t2 import get_user_t2_stats
            stats = get_user_t2_stats(user)

        else:
            return jsonify({'error': 'Unknown tool'}), 404

        return jsonify({
            'success': True,
            'tool': tool_name,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error getting tool analytics: {e}")
        return jsonify({'error': str(e)}), 500


# ========== GAMIFICATION API ==========

@api_gateway_bp.route("/user/<username>/badges")
@require_login
def api_user_badges(username):
    """Get user badges for scoreboard display"""
    try:
        from app.services.achievement_system import achievement_system
        user_badges_data = achievement_system.get_user_badges(username)

        # Format badges for frontend
        badges = user_badges_data.get('badges', [])
        formatted_badges = []
        for badge in badges:
            formatted_badges.append({
                'name': badge.get('name', ''),
                'emoji': badge.get('icon', '🏆'),
                'rarity': badge.get('rarity', 'common')
            })

        return jsonify({
            'success': True,
            'badges': formatted_badges
        })
    except Exception as e:
        logger.error(f"Error getting badges for {username}: {e}")
        return jsonify({'success': False, 'badges': []}), 200


@api_gateway_bp.route("/user/<username>/avatar")
@require_login
def api_user_avatar(username):
    """Get user avatar cosmetics"""
    try:
        from app.services.cosmetics_shop import CosmeticsShop
        cosmetics_shop = CosmeticsShop()
        user_cosmetics = cosmetics_shop.get_user_cosmetics(username)

        active = user_cosmetics.get('active', {})

        return jsonify({
            'success': True,
            'avatar': active.get('avatar', '🧑‍💼'),
            'theme': active.get('theme', 'default'),
            'title': active.get('title'),
            'effects': active.get('effects', [])
        })
    except Exception as e:
        logger.error(f"Error getting avatar for {username}: {e}")
        return jsonify({
            'success': False,
            'avatar': '🧑‍💼',
            'theme': 'default',
            'title': None,
            'effects': []
        }), 200


@api_gateway_bp.route("/gamification/status")
@require_login
def gamification_status():
    """
    Gamification-Status für alle Tools
    """
    try:
        user = session.get('user')

        gamification_data = get_comprehensive_gamification_data(user)

        return jsonify({
            'success': True,
            'data': gamification_data
        })

    except Exception as e:
        logger.error(f"Error getting gamification status: {e}")
        return jsonify({'error': str(e)}), 500


@api_gateway_bp.route("/gamification/leaderboard")
@require_login
def leaderboard():
    """
    Leaderboard für alle Tools
    """
    try:
        leaderboard_type = request.args.get('type', 'overall')  # overall, weekly, monthly

        leaderboard_data = get_cross_tool_leaderboard(leaderboard_type)

        return jsonify({
            'success': True,
            'type': leaderboard_type,
            'leaderboard': leaderboard_data
        })

    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return jsonify({'error': str(e)}), 500


# ========== SYSTEM HEALTH API ==========

@api_gateway_bp.route("/system/health")
@require_login
def system_health():
    """
    System-Gesundheitsstatus für alle Tools
    """
    try:
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': get_services_health(),
            'uptime': get_system_uptime(),
            'version': get_system_version()
        }

        # Determine overall health
        service_statuses = list(health_data['services'].values())
        if 'error' in service_statuses:
            health_data['status'] = 'error'
        elif 'warning' in service_statuses:
            health_data['status'] = 'warning'

        status_code = 200 if health_data['status'] == 'healthy' else 503

        return jsonify({
            'success': True,
            'health': health_data
        }), status_code

    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return jsonify({'error': str(e)}), 500


# ========== ADMIN APIS ==========

@api_gateway_bp.route("/admin/tools/manage", methods=['POST'])
@require_login
def manage_tools():
    """
    Tool-Management für Admins
    """
    try:
        user = session.get('user')

        if not is_admin_user(user):
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json()
        action = data.get('action')  # 'enable', 'disable', 'restart'
        tool_name = data.get('tool')

        result = perform_tool_management_action(action, tool_name)

        return jsonify({
            'success': result['success'],
            'message': result['message'],
            'action': action,
            'tool': tool_name
        })

    except Exception as e:
        logger.error(f"Error managing tools: {e}")
        return jsonify({'error': str(e)}), 500


@api_gateway_bp.route("/admin/system/stats")
@require_login
def admin_system_stats():
    """
    System-Statistiken für Admins
    """
    try:
        user = session.get('user')

        if not is_admin_user(user):
            return jsonify({'error': 'Admin access required'}), 403

        system_stats = {
            'users': get_user_statistics(),
            'tools': get_tool_statistics(),
            'performance': get_system_performance_stats(),
            'usage': get_usage_statistics(),
            'errors': get_error_statistics()
        }

        return jsonify({
            'success': True,
            'stats': system_stats
        })

    except Exception as e:
        logger.error(f"Error getting admin system stats: {e}")
        return jsonify({'error': str(e)}), 500


# ========== UTILITY FUNCTIONS ==========

def get_all_tools_status() -> Dict[str, Any]:
    """Status aller Tools abrufen"""
    tools = {
        'hub': {
            'name': 'Business Hub',
            'status': 'active',
            'health': 'healthy',
            'version': '1.0.0'
        },
        'slots': {
            'name': 'Slot-Booking',
            'status': 'active',
            'health': 'healthy',
            'version': '3.2.0'
        },
        't2': {
            'name': 'T2-Closer',
            'status': 'active',
            'health': 'healthy',
            'version': '1.0.0'
        }
    }

    # Check actual health for each tool
    for tool_id, tool_data in tools.items():
        try:
            health = check_tool_health(tool_id)
            tool_data['health'] = health
        except Exception as e:
            tool_data['health'] = 'error'
            tool_data['error'] = str(e)

    return tools


def get_user_accessible_tools(username: str) -> list:
    """Tools, auf die der Benutzer Zugriff hat"""
    from app.routes.hub import get_available_tools
    return get_available_tools()


def get_cross_tool_stats(username: str) -> Dict[str, Any]:
    """Übergreifende Statistiken"""
    stats = {
        'total_bookings': 0,
        'active_sessions': 0,
        'completion_rate': 95.5,
        'tools_used': 0
    }

    try:
        # Slots stats
        from app.routes.slots import get_user_stats
        slots_stats = get_user_stats(username)
        stats['total_bookings'] += slots_stats.get('total_bookings', 0)
        stats['tools_used'] += 1

        # T2 stats
        from app.routes.t2 import get_user_t2_stats
        t2_stats = get_user_t2_stats(username)
        stats['total_bookings'] += t2_stats.get('total_bookings', 0)
        if t2_stats.get('total_bookings', 0) > 0:
            stats['tools_used'] += 1

    except Exception as e:
        logger.warning(f"Error getting cross-tool stats: {e}")

    return stats


def get_user_gamification_summary(username: str) -> Dict[str, Any]:
    """Gamification-Zusammenfassung"""
    try:
        from app.services.achievement_system import achievement_system
        from app.services.level_system import level_system as level_svc

        return {
            'level': level_svc.get_user_level(username),
            'xp': level_svc.get_user_xp(username),
            'badges_count': len(achievement_system.get_user_badges(username)),
            'recent_achievements': achievement_system.get_recent_achievements(username)[:3]
        }
    except Exception as e:
        logger.warning(f"Error getting gamification summary: {e}")
        return {}


def get_user_notifications(username: str) -> list:
    """Benutzer-Benachrichtigungen"""
    # Mock notifications for demo
    notifications = [
        {
            'id': 'notif_1',
            'title': 'Termin-Erinnerung',
            'message': 'Du hast einen Termin morgen um 14:00',
            'type': 'reminder',
            'read': False,
            'timestamp': datetime.now().isoformat(),
            'source': 'slots'
        },
        {
            'id': 'notif_2',
            'title': 'Neues Achievement',
            'message': 'Du hast das Badge "Regelmäßiger Nutzer" erhalten!',
            'type': 'achievement',
            'read': False,
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'source': 'gamification'
        }
    ]

    return notifications


def get_recent_activity(username: str) -> list:
    """Letzte Aktivitäten"""
    activities = [
        {
            'id': 'act_1',
            'action': 'Termin gebucht',
            'details': 'Slot-Booking mit Sara am 15.04.2024',
            'timestamp': datetime.now().isoformat(),
            'tool': 'slots',
            'icon': 'fas fa-calendar-plus'
        },
        {
            'id': 'act_2',
            'action': 'T2-Closer konsultiert',
            'details': 'Alexander - Premium-Beratung',
            'timestamp': (datetime.now() - timedelta(hours=3)).isoformat(),
            'tool': 't2',
            'icon': 'fas fa-user-tie'
        }
    ]

    return activities


def check_tool_health(tool_id: str) -> str:
    """Gesundheitsstatus eines Tools prüfen"""
    try:
        if tool_id == 'slots':
            # Check slots system health
            from app.services.data_persistence import data_persistence
            data_persistence.verify_integrity()

        elif tool_id == 't2':
            # Check T2 system health
            from app.routes.t2 import T2_CLOSERS
            if len(T2_CLOSERS) == 0:
                return 'error'

        return 'healthy'

    except Exception as e:
        logger.error(f"Health check failed for {tool_id}: {e}")
        return 'error'


def get_services_health() -> Dict[str, str]:
    """Gesundheitsstatus aller Services"""
    return {
        'database': 'healthy',
        'cache': 'healthy',
        'calendar': 'healthy',
        'gamification': 'healthy',
        'notifications': 'healthy'
    }


def get_system_uptime() -> str:
    """System-Uptime"""
    return "99.8%"


def get_system_version() -> str:
    """System-Version"""
    return "3.2.0"


def is_admin_user(username: str) -> bool:
    """Prüfen ob Benutzer Admin ist"""
    try:
        from app.config.base import Config
        admin_users = Config.get_admin_users()
        return username in admin_users
    except:
        return username in ['admin', 'Jose', 'Simon', 'Alex', 'David']


def log_cross_tool_activity(username: str, action: str, data: Dict):
    """Tool-übergreifende Aktivitäten protokollieren"""
    try:
        from app.services.tracking_system import tracking_system
        tracking_system.log_activity(username, action, data)
    except Exception as e:
        logger.warning(f"Failed to log activity: {e}")


# Mock functions für Demo
def get_unread_notifications_count(username: str) -> int:
    return 2

def mark_notification_as_read(username: str, notification_id: str) -> bool:
    return True

def get_system_alerts() -> list:
    return []

def get_user_analytics(username: str) -> Dict:
    return {}

def get_tool_usage_stats(username: str) -> Dict:
    return {}

def get_user_performance_stats(username: str) -> Dict:
    return {}

def get_system_analytics() -> Dict:
    return {}

def get_comprehensive_gamification_data(username: str) -> Dict:
    return get_user_gamification_summary(username)

def get_cross_tool_leaderboard(leaderboard_type: str) -> list:
    return []

def perform_tool_management_action(action: str, tool_name: str) -> Dict:
    return {'success': True, 'message': f'Tool {tool_name} {action}d successfully'}

def get_user_statistics() -> Dict:
    return {}

def get_tool_statistics() -> Dict:
    return {}

def get_system_performance_stats() -> Dict:
    return {}

def get_usage_statistics() -> Dict:
    return {}

def get_error_statistics() -> Dict:
    return {}