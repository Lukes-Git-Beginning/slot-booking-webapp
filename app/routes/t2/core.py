# -*- coding: utf-8 -*-
"""
T2 Core Routes - Dashboard & Health Checks

Routes:
1. /t2/ - Root redirect
2. /t2/dashboard - Main T2 dashboard
3. /t2/health - Health check endpoint
4. /t2/legacy-analytics - Legacy analytics view (deprecated)
5. /t2/test-error - Sentry error test endpoint

Migration Status: Phase 2 - Stub created, implementation in Phase 4
"""

from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required, current_user

# Create sub-blueprint (will be registered under /t2 prefix)
core_bp = Blueprint('core', __name__)


@core_bp.route('/')
def root():
    """
    Root redirect - forwards to dashboard

    MIGRATED FROM: t2_legacy.py line 2089
    """
    return redirect(url_for('t2.core.dashboard'))


@core_bp.route('/dashboard')
@login_required
def dashboard():
    """
    T2 Closer Dashboard - Main overview

    MIGRATED FROM: t2_legacy.py line 156
    TEMPLATE: templates/t2/dashboard.html

    TODO Phase 4: Implement full dashboard logic
    - Load closer stats
    - Display bucket composition
    - Show recent draws
    - Admin controls
    """
    # Stub implementation
    return render_template('t2/dashboard.html',
                         active_page='t2',
                         message='Modular blueprint stub - Phase 4 will implement full logic')


@core_bp.route('/health')
def health():
    """
    Health check endpoint for monitoring

    MIGRATED FROM: t2_legacy.py line 1342

    Returns:
        JSON: {status, service, version}
    """
    return jsonify({
        'status': 'healthy',
        'service': 't2_closer',
        'version': 'modular_v1',
        'blueprint': 'core'
    })


@core_bp.route('/legacy-analytics')
@login_required
def legacy_analytics():
    """
    Legacy analytics view (DEPRECATED)

    MIGRATED FROM: t2_legacy.py line 1456
    NOTE: Will be removed in future version

    TODO Phase 4: Decide if this should redirect to /t2/my-analytics
    """
    # Stub - redirect to new analytics
    return redirect(url_for('t2.admin.my_analytics'))


@core_bp.route('/test-error')
@login_required
def test_error():
    """
    Sentry error test endpoint (Admin only)

    MIGRATED FROM: t2_legacy.py line 1502

    TODO Phase 4: Implement admin check
    """
    # Stub implementation
    if not current_user.is_admin:
        return jsonify({'error': 'Admin only'}), 403

    # Trigger test error
    raise Exception('Sentry test error from modular T2 blueprint')
