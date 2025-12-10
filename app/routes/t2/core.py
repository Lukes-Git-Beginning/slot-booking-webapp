# -*- coding: utf-8 -*-
"""
T2 Core Routes - Dashboard & Health Checks

Routes:
1. /t2/ - Dashboard (Main T2 overview)
2. /t2/health - Health check endpoint

MIGRATED FROM: t2_legacy.py (Phase 4)
Migration Status: ✅ COMPLETE
"""

from flask import Blueprint, render_template, jsonify, session
from app.utils.decorators import require_login
from .utils import (
    is_admin_user,
    get_user_tickets_remaining,
    get_user_t2_bookings,
    get_next_t2_appointments,
    T2_CONFIG
)

# Create sub-blueprint (will be registered under /t2 prefix)
core_bp = Blueprint('core', __name__)


@core_bp.route('/')
@require_login
def dashboard():
    """
    T2-Dashboard mit Würfel-System

    MIGRATED FROM: t2_legacy.py line 135-151
    TEMPLATE: templates/t2/dashboard.html

    Phase 4: ✅ FULLY IMPLEMENTED
    """
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


@core_bp.route('/health')
def health():
    """
    Health check endpoint for monitoring

    NEW ROUTE (not in legacy t2.py)
    Returns service status and version info

    Phase 4: ✅ IMPLEMENTED
    """
    return jsonify({
        'status': 'healthy',
        'service': 't2_closer',
        'version': 'modular_v1',
        'blueprint': 'core',
        'routes_active': 2  # dashboard + health
    })
