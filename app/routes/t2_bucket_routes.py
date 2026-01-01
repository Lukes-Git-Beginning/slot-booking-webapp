# -*- coding: utf-8 -*-
"""
T2 Bucket System Routes
New probability-based drawing system
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.utils.decorators import require_login
from app.core.extensions import csrf
from app.services.t2_bucket_system import (
    draw_closer,
    get_probabilities,
    update_probability,
    get_bucket_composition,
    reset_bucket,
    get_system_stats,
    get_available_closers,
    check_user_timeout,
    update_bucket_size,
    get_bucket_config,
    add_closer,
    remove_closer,
    update_closer_info
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
            customer_name = data.get('customer_name', '').strip()

            # Perform draw with customer name
            result = draw_closer(user, draw_type, customer_name if customer_name else None)

            if result['success']:
                # Store in session for booking
                session['t2_current_closer'] = result['closer']
                session['t2_closer_color'] = result['color']
                session.modified = True  # Force Flask to save session immediately

                log_msg = f"T2 Draw: {user} drew {result['closer']}"
                if customer_name:
                    log_msg += f" for customer '{customer_name}'"
                logger.info(log_msg)

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
        try:
            user = session.get('user')

            # Check admin
            from app.routes.t2.utils import is_admin_user
            if not is_admin_user(user):
                return redirect(url_for('t2.dashboard'))

            # Get current data with fallbacks
            probabilities = get_probabilities() if get_probabilities else {}
            bucket_comp = get_bucket_composition() if get_bucket_composition else {
                'composition': {},
                'total_tickets': 0,
                'draws_until_reset': 10,
                'max_draws_before_reset': 10,
                'default_probabilities': {}
            }
            system_stats = get_system_stats() if get_system_stats else {
                'total_all_time_draws': 0,
                'closer_distribution': {},
                'recent_draws': []
            }
            closers = get_available_closers() if get_available_closers else {}

            return render_template('t2/admin_bucket_config.html',
                                 user=user,
                                 probabilities=probabilities,
                                 bucket_composition=bucket_comp,
                                 bucket_stats={
                                     'current_bucket_size': bucket_comp.get('total_tickets', 0),
                                     'draws_until_reset': bucket_comp.get('draws_until_reset', 10),
                                     'draws_this_cycle': bucket_comp.get('max_draws_before_reset', 10) - bucket_comp.get('draws_until_reset', 10)
                                 },
                                 system_stats=system_stats,
                                 closers=closers)
        except Exception as e:
            logger.error(f"Error loading bucket config: {e}", exc_info=True)
            # Return safe fallback template
            return render_template('t2/admin_bucket_config.html',
                                 user=session.get('user', ''),
                                 probabilities={},
                                 bucket_composition={
                                     'composition': {},
                                     'total_tickets': 0,
                                     'draws_until_reset': 10,
                                     'max_draws_before_reset': 10,
                                     'default_probabilities': {}
                                 },
                                 bucket_stats={
                                     'current_bucket_size': 0,
                                     'draws_until_reset': 10,
                                     'draws_this_cycle': 0
                                 },
                                 system_stats={
                                     'total_all_time_draws': 0,
                                     'closer_distribution': {},
                                     'recent_draws': []
                                 },
                                 closers={},
                                 error="Fehler beim Laden der Bucket-Konfiguration")

    @t2_bp.route("/api/admin/update-probability", methods=['POST'])
    @require_login
    def api_admin_update_probability():
        """Update probability for a closer (Admin only)"""
        user = session.get('user')

        # Check admin
        from app.routes.t2.utils import is_admin_user
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
        from app.routes.t2.utils import is_admin_user
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

    @t2_bp.route("/api/admin/update-bucket-size", methods=['POST'])
    @require_login
    def api_admin_update_bucket_size():
        """Update bucket size (Admin only)"""
        user = session.get('user')

        # Check admin
        from app.routes.t2.utils import is_admin_user
        if not is_admin_user(user):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            data = request.get_json()
            bucket_size = int(data.get('bucket_size'))

            result = update_bucket_size(bucket_size)

            if result['success']:
                logger.info(f"Admin {user} updated bucket size to {bucket_size}")

            return jsonify(result)

        except Exception as e:
            logger.error(f"Error updating bucket size: {e}")
            return jsonify({
                'success': False,
                'message': 'Error updating bucket size'
            }), 500

    @t2_bp.route("/api/admin/add-closer", methods=['POST'])
    @require_login
    def api_admin_add_closer():
        """Add new closer (Admin only)"""
        user = session.get('user')

        # Check admin
        from app.routes.t2.utils import is_admin_user
        if not is_admin_user(user):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            data = request.get_json()
            name = data.get('name', '').strip()
            color = data.get('color', '').strip()
            full_name = data.get('full_name', '').strip()
            default_probability = float(data.get('default_probability', 1.0))

            if not name or not color or not full_name:
                return jsonify({
                    'success': False,
                    'message': 'Name, Farbe und vollständiger Name sind erforderlich'
                }), 400

            result = add_closer(name, color, full_name, default_probability)

            if result['success']:
                logger.info(f"Admin {user} added closer {name}")

            return jsonify(result)

        except Exception as e:
            logger.error(f"Error adding closer: {e}")
            return jsonify({
                'success': False,
                'message': 'Error adding closer'
            }), 500

    @t2_bp.route("/api/admin/remove-closer", methods=['POST'])
    @require_login
    def api_admin_remove_closer():
        """Remove closer (Admin only)"""
        user = session.get('user')

        # Check admin
        from app.routes.t2.utils import is_admin_user
        if not is_admin_user(user):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            data = request.get_json()
            name = data.get('name', '').strip()

            if not name:
                return jsonify({
                    'success': False,
                    'message': 'Closer-Name erforderlich'
                }), 400

            result = remove_closer(name)

            if result['success']:
                logger.info(f"Admin {user} removed closer {name}")

            return jsonify(result)

        except Exception as e:
            logger.error(f"Error removing closer: {e}")
            return jsonify({
                'success': False,
                'message': 'Error removing closer'
            }), 500

    @t2_bp.route("/api/admin/update-closer-info", methods=['POST'])
    @require_login
    def api_admin_update_closer_info():
        """Update closer info (Admin only)"""
        user = session.get('user')

        # Check admin
        from app.routes.t2.utils import is_admin_user
        if not is_admin_user(user):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

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

            result = update_closer_info(name, new_color, new_full_name)

            if result['success']:
                logger.info(f"Admin {user} updated closer {name}")

            return jsonify(result)

        except Exception as e:
            logger.error(f"Error updating closer: {e}")
            return jsonify({
                'success': False,
                'message': 'Error updating closer'
            }), 500
