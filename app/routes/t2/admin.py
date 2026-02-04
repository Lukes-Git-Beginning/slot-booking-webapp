# -*- coding: utf-8 -*-
"""
T2 Admin Routes - Analytics, Configuration & Management

Routes (18 total):
ANALYTICS - Pages (2 routes):
1. /t2/my-analytics - User analytics dashboard
2. /t2/admin/analytics - Admin analytics dashboard

ANALYTICS - APIs (7 routes):
3. /t2/api/analytics-data - Generic analytics API (type-based)
4. /t2/api/weekly-report - Weekly stats (stub)
5. /t2/admin/generate-pdf - PDF report generation (stub)
6. /t2/api/my-draw-history - User draw history with pagination
7. /t2/api/my-draw-stats - User draw statistics
8. /t2/api/combined-stats - Combined T1+T2+Draw stats
9. /t2/api/search-draws - Search draws by name
10. /t2/api/draw-timeline - Draw timeline chart data

CONFIGURATION (8 routes):
11. /t2/admin/manage-closers - Closer management UI
12. /t2/api/add-closer - Add closer API
13. /t2/api/update-closer - Update closer API
14. /t2/api/remove-closer - Remove closer API
15. /t2/admin/calendar-config - Calendar settings (read-only)
16. /t2/api/update-calendar - Update calendar API (stub)
17. /t2/admin/notification-test - Test notifications (stub)
18. /t2/admin/system-health - Health dashboard

Migration Status: Phase 6 - Implemented from t2_legacy.py
"""

from flask import Blueprint, render_template, jsonify, request, send_file, session
from app.utils.decorators import require_login
from app.services.t2_analytics_service import t2_analytics_service
from app.services.t2_bucket_system import (
    get_available_closers,
    get_probabilities,
    get_system_stats,
    get_bucket_composition,
    add_closer as bucket_add_closer,
    remove_closer as bucket_remove_closer,
    update_closer_info as bucket_update_closer_info
)
from .utils import is_admin_user, T2_CLOSERS
from datetime import date, timedelta
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Create sub-blueprint
admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator for admin-only routes"""
    @wraps(f)
    @require_login
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not is_admin_user(user):
            return render_template('errors/403.html'), 403
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# ANALYTICS - PAGE ROUTES
# ============================================================================

@admin_bp.route('/my-analytics')
@require_login
def my_analytics():
    """
    Personal Analytics Hub - Draw-Historie, Combined Stats, Quick Links

    MIGRATED FROM: t2_legacy.py line 1035
    TEMPLATE: templates/t2/analytics.html
    """
    user = session.get('user')

    draw_stats = t2_analytics_service.get_user_draw_stats(user)
    combined_stats = t2_analytics_service.get_combined_user_stats(user)

    return render_template('t2/analytics.html',
                         user=user,
                         is_admin=is_admin_user(user),
                         draw_stats=draw_stats,
                         combined_stats=combined_stats)


@admin_bp.route('/admin/analytics')
@admin_required
def admin_analytics():
    """
    Admin analytics dashboard - 2h Booking Statistics (ADMIN ONLY)

    TEMPLATE: templates/t2/admin_analytics.html
    """
    user = session.get('user')

    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        analytics = t2_analytics_service.get_2h_booking_analytics(start_date, end_date)
    except Exception as e:
        logger.error(f"Error loading admin analytics: {e}", exc_info=True)
        analytics = {}

    return render_template('t2/admin_analytics.html',
                         user=user,
                         analytics=analytics,
                         active_page='t2')


# ============================================================================
# ANALYTICS - API ROUTES
# ============================================================================

@admin_bp.route('/api/my-draw-history')
@require_login
def api_my_draw_history():
    """
    API: Get user's draw history with pagination and filters

    MIGRATED FROM: t2_legacy.py line 1068
    Query params: limit, offset, start_date, end_date, closer
    """
    try:
        user = session.get('user')

        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        closer_filter = request.args.get('closer')

        history = t2_analytics_service.get_user_draw_history(
            username=user,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            closer_filter=closer_filter
        )

        return jsonify({'success': True, **history})

    except Exception as e:
        logger.error(f"Error getting draw history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/my-draw-stats')
@require_login
def api_my_draw_stats():
    """
    API: Get aggregated draw statistics for user

    MIGRATED FROM: t2_legacy.py line 1105
    """
    try:
        user = session.get('user')
        stats = t2_analytics_service.get_user_draw_stats(user)

        return jsonify({'success': True, 'stats': stats})

    except Exception as e:
        logger.error(f"Error getting draw stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/combined-stats')
@require_login
def api_combined_stats():
    """
    API: Get combined statistics (T1 Slots + T2 Bookings + Draw Activity)

    MIGRATED FROM: t2_legacy.py line 1125
    """
    try:
        user = session.get('user')
        combined = t2_analytics_service.get_combined_user_stats(user)

        return jsonify({'success': True, 'stats': combined})

    except Exception as e:
        logger.error(f"Error getting combined stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/search-draws')
@require_login
def api_search_draws():
    """
    API: Search draws by customer name or closer name

    MIGRATED FROM: t2_legacy.py line 1145
    Query params: q (query string, min 2 chars)
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
        logger.error(f"Error searching draws: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/draw-timeline')
@require_login
def api_draw_timeline():
    """
    API: Get draw timeline data for charts (last N days)

    MIGRATED FROM: t2_legacy.py line 1175
    Query params: days (default: 30)
    """
    try:
        user = session.get('user')
        days = int(request.args.get('days', 30))

        timeline = t2_analytics_service.get_draw_timeline_data(user, days)

        return jsonify({'success': True, **timeline})

    except Exception as e:
        logger.error(f"Error getting draw timeline: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/analytics-data', methods=['GET', 'POST'])
@require_login
def analytics_data():
    """
    Generic analytics data endpoint

    Query params:
        type: draw_stats | combined | 2h_analytics (admin only)
        days: number of days for 2h_analytics (default: 30)
    """
    try:
        user = session.get('user')
        data_type = request.args.get('type', 'draw_stats')

        if data_type == 'draw_stats':
            data = t2_analytics_service.get_user_draw_stats(user)
        elif data_type == 'combined':
            data = t2_analytics_service.get_combined_user_stats(user)
        elif data_type == '2h_analytics':
            if not is_admin_user(user):
                return jsonify({'success': False, 'error': 'Admin-Berechtigung erforderlich'}), 403
            days = int(request.args.get('days', 30))
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            data = t2_analytics_service.get_2h_booking_analytics(start_date, end_date)
        else:
            return jsonify({'success': False, 'error': f'Unknown data type: {data_type}'}), 400

        return jsonify({'success': True, 'data': data})

    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid parameter value'}), 400
    except Exception as e:
        logger.error(f"Error getting analytics data: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/weekly-report', methods=['GET'])
@admin_required
def weekly_report():
    """
    Weekly statistics report API (ADMIN ONLY)

    TODO: Implement weekly aggregation when reporting requirements are defined
    """
    return jsonify({
        'success': False,
        'report': {},
        'message': 'Weekly report not yet implemented'
    }), 501


@admin_bp.route('/admin/generate-pdf', methods=['POST'])
@admin_required
def generate_pdf():
    """
    PDF report generation (ADMIN ONLY)

    TODO: Implement PDF generation when reporting requirements are defined
    """
    return jsonify({
        'success': False,
        'message': 'PDF generation not yet implemented'
    }), 501


# ============================================================================
# CONFIGURATION ROUTES
# ============================================================================

@admin_bp.route('/admin/manage-closers')
@admin_required
def manage_closers():
    """
    Closer management UI (ADMIN ONLY)

    TEMPLATE: templates/t2/manage_closers.html
    """
    try:
        closers = get_available_closers()
        probabilities = get_probabilities()
    except Exception as e:
        logger.error(f"Error loading closer data: {e}", exc_info=True)
        closers = {}
        probabilities = {}

    return render_template('t2/manage_closers.html',
                         active_page='t2',
                         closers=closers,
                         probabilities=probabilities)


@admin_bp.route('/api/add-closer', methods=['POST'])
@admin_required
def add_closer():
    """Add new closer API (ADMIN ONLY)"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        color = data.get('color', '').strip()
        full_name = data.get('full_name', '').strip()
        default_probability = float(data.get('default_probability', 1.0))

        if not name or not color or not full_name:
            return jsonify({
                'success': False,
                'message': 'Name, Farbe und vollstaendiger Name sind erforderlich'
            }), 400

        result = bucket_add_closer(name, color, full_name, default_probability)

        if result['success']:
            logger.info(f"Admin {session.get('user')} added closer {name}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error adding closer: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error adding closer'}), 500


@admin_bp.route('/api/update-closer', methods=['POST'])
@admin_required
def update_closer():
    """Update closer details API (ADMIN ONLY)"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        new_color = data.get('color', '').strip() or None
        new_full_name = data.get('full_name', '').strip() or None

        if not name:
            return jsonify({
                'success': False,
                'message': 'Closer-Name erforderlich'
            }), 400

        result = bucket_update_closer_info(name, new_color, new_full_name)

        if result['success']:
            logger.info(f"Admin {session.get('user')} updated closer {name}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error updating closer: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error updating closer'}), 500


@admin_bp.route('/api/remove-closer', methods=['POST'])
@admin_required
def remove_closer():
    """Remove closer API (ADMIN ONLY)"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({
                'success': False,
                'message': 'Closer-Name erforderlich'
            }), 400

        result = bucket_remove_closer(name)

        if result['success']:
            logger.info(f"Admin {session.get('user')} removed closer {name}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error removing closer: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error removing closer'}), 500


@admin_bp.route('/admin/calendar-config')
@admin_required
def calendar_config():
    """
    Calendar configuration UI (ADMIN ONLY) - Read-only view

    TEMPLATE: templates/t2/calendar_config.html
    """
    return render_template('t2/calendar_config.html',
                         active_page='t2',
                         closers=T2_CLOSERS)


@admin_bp.route('/api/update-calendar', methods=['POST'])
@admin_required
def update_calendar():
    """
    Update calendar configuration API (ADMIN ONLY)

    TODO: Implement when calendar config editing is needed
    """
    return jsonify({
        'success': False,
        'message': 'Calendar configuration updates not yet implemented'
    }), 501


@admin_bp.route('/admin/notification-test', methods=['POST'])
@admin_required
def notification_test():
    """
    Test notification system (ADMIN ONLY)

    TODO: Implement when notification system is ready
    """
    return jsonify({
        'success': False,
        'message': 'Notification testing not yet implemented'
    }), 501


@admin_bp.route('/admin/system-health')
@admin_required
def system_health():
    """
    System health dashboard (ADMIN ONLY)

    TEMPLATE: templates/t2/system_health.html
    """
    health = {}

    try:
        system_stats = get_system_stats()
        bucket_comp = get_bucket_composition()
        health['bucket_system'] = 'healthy'
        health['total_draws'] = system_stats.get('total_all_time_draws', 0)
        health['total_resets'] = system_stats.get('total_resets', 0)
        health['bucket_size'] = bucket_comp.get('total_tickets', 0)
        health['draws_until_reset'] = bucket_comp.get('draws_until_reset', 10)
        health['recent_draws'] = system_stats.get('recent_draws', [])[:10]
    except Exception as e:
        logger.error(f"Error loading bucket health: {e}", exc_info=True)
        health['bucket_system'] = 'error'
        health['bucket_error'] = str(e)

    try:
        from app.models import is_postgres_enabled
        health['postgres_enabled'] = is_postgres_enabled()
    except Exception:
        health['postgres_enabled'] = False

    try:
        closers = get_available_closers()
        health['active_closers'] = len(closers)
    except Exception:
        health['active_closers'] = 0

    return render_template('t2/system_health.html',
                         active_page='t2',
                         health=health)
