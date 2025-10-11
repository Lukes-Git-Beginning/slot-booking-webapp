# -*- coding: utf-8 -*-
"""
T2 Bucket System Routes
New probability-based drawing system
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.utils.decorators import require_login
from app.services.t2_bucket_system import (
    draw_closer,
    get_probabilities,
    update_probability,
    get_bucket_composition,
    reset_bucket,
    get_system_stats,
    get_available_closers,
    check_user_timeout
)
import logging

logger = logging.getLogger(__name__)

# Note: This will be added to main t2_bp in t2.py


def register_bucket_routes(t2_bp):
    """Register bucket system routes to T2 blueprint"""

    @t2_bp.route("/draw")
    @require_login
    def draw_page():
        """Draw closer page with animated UI"""
        user = session.get('user')

        # Get timeout info
        timeout_info = check_user_timeout(user, 'T2')

        # Get bucket stats
        bucket_comp = get_bucket_composition()

        return render_template('t2/draw_closer.html',
                             user=user,
                             timeout_info=timeout_info,
                             bucket_stats={
                                 'tickets_remaining': bucket_comp['total_tickets'],
                                 'draws_until_reset': bucket_comp['draws_until_reset'],
                                 'draws_this_cycle': 10 - bucket_comp['draws_until_reset']
                             },
                             closers=get_available_closers())

    @t2_bp.route("/api/draw-closer", methods=['POST'])
    @require_login
    def api_draw_closer():
        """Perform draw from bucket"""
        try:
            user = session.get('user')
            data = request.get_json() or {}
            draw_type = data.get('draw_type', 'T2')

            # Perform draw
            result = draw_closer(user, draw_type)

            if result['success']:
                # Store in session for booking
                session['t2_current_closer'] = result['closer']
                session['t2_closer_color'] = result['color']

                logger.info(f"T2 Draw: {user} drew {result['closer']}")

            return jsonify(result)

        except Exception as e:
            logger.error(f"Draw error: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'Error during draw'
            }), 500

    @t2_bp.route("/admin/bucket-config")
    @require_login
    def admin_bucket_config():
        """Admin page for bucket configuration"""
        user = session.get('user')

        # Check admin
        from app.routes.t2 import is_admin_user
        if not is_admin_user(user):
            return redirect(url_for('t2.dashboard'))

        # Get current data
        probabilities = get_probabilities()
        bucket_comp = get_bucket_composition()
        system_stats = get_system_stats()
        closers = get_available_closers()

        return render_template('t2/admin_bucket_config.html',
                             user=user,
                             probabilities=probabilities,
                             bucket_composition=bucket_comp['composition'],
                             bucket_stats={
                                 'current_bucket_size': bucket_comp['total_tickets'],
                                 'draws_until_reset': bucket_comp['draws_until_reset'],
                                 'draws_this_cycle': 10 - bucket_comp['draws_until_reset']
                             },
                             system_stats=system_stats,
                             closers=closers)

    @t2_bp.route("/api/admin/update-probability", methods=['POST'])
    @require_login
    def api_admin_update_probability():
        """Update probability for a closer (Admin only)"""
        user = session.get('user')

        # Check admin
        from app.routes.t2 import is_admin_user
        if not is_admin_user(user):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            data = request.get_json()
            closer_name = data.get('closer_name')
            probability = float(data.get('probability'))

            result = update_probability(closer_name, probability)

            if result['success']:
                logger.info(f"Admin {user} updated probability for {closer_name}: {probability}")

            return jsonify(result)

        except Exception as e:
            logger.error(f"Error updating probability: {e}")
            return jsonify({
                'success': False,
                'message': 'Error updating probability'
            }), 500

    @t2_bp.route("/api/admin/reset-bucket", methods=['POST'])
    @require_login
    def api_admin_reset_bucket():
        """Reset bucket (Admin only)"""
        user = session.get('user')

        # Check admin
        from app.routes.t2 import is_admin_user
        if not is_admin_user(user):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            result = reset_bucket()

            if result['success']:
                logger.info(f"Admin {user} reset bucket")

            return jsonify(result)

        except Exception as e:
            logger.error(f"Error resetting bucket: {e}")
            return jsonify({
                'success': False,
                'message': 'Error resetting bucket'
            }), 500
