# -*- coding: utf-8 -*-
"""
Admin user management routes
User administration, points management, and badge system
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import pytz

from app.config.base import slot_config
from app.core.extensions import data_persistence
from app.utils.decorators import require_admin
from app.utils.helpers import get_userlist
from app.routes.admin import admin_bp
from app.services.activity_tracking import activity_tracking
from app.services.user_management_service import user_management_service

TZ = pytz.timezone(slot_config.TIMEZONE)


@admin_bp.route("/users")
@require_admin
def admin_users():
    """User management interface"""
    users = user_management_service.get_all_users()

    total_users = len(users)
    active_users = total_users  # All visible users are active (deleted are filtered)
    admin_count = len([u for u in users if u['is_admin']])
    online_users = len([u for u in users if u['is_online']])

    return render_template("admin_users.html",
                         users=users,
                         total_users=total_users,
                         active_users=active_users,
                         admin_count=admin_count,
                         online_users=online_users)


@admin_bp.route("/users/add", methods=["POST"])
@require_admin
def admin_users_add():
    """Add a new user"""
    data = request.get_json()
    if not data:
        return jsonify(success=False, message="Keine Daten erhalten"), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    is_admin = data.get('is_admin', False)
    admin_username = session.get('user', 'unknown')

    success, message = user_management_service.add_user(username, password, is_admin, admin_username)
    status_code = 200 if success else 400
    return jsonify(success=success, message=message), status_code


@admin_bp.route("/users/<username>/delete", methods=["POST"])
@require_admin
def admin_users_delete(username):
    """Delete a user (soft-delete)"""
    admin_username = session.get('user', 'unknown')
    success, message = user_management_service.delete_user(username, admin_username)
    status_code = 200 if success else 400
    return jsonify(success=success, message=message), status_code


@admin_bp.route("/users/<username>/reset-password", methods=["POST"])
@require_admin
def admin_users_reset_password(username):
    """Reset a user's password"""
    admin_username = session.get('user', 'unknown')
    success, message, new_password = user_management_service.reset_password(username, admin_username)
    status_code = 200 if success else 400
    result = {'success': success, 'message': message}
    if success:
        result['new_password'] = new_password
    return jsonify(result), status_code


@admin_bp.route("/users/<username>/toggle-admin", methods=["POST"])
@require_admin
def admin_users_toggle_admin(username):
    """Toggle admin status for a user"""
    admin_username = session.get('user', 'unknown')
    success, message = user_management_service.toggle_admin(username, admin_username)
    status_code = 200 if success else 400
    return jsonify(success=success, message=message), status_code


@admin_bp.route("/users/<username>/detail")
@require_admin
def admin_users_detail(username):
    """Get detailed user data"""
    detail = user_management_service.get_user_detail(username)
    if not detail:
        return jsonify(success=False, message="Benutzer nicht gefunden"), 404
    return jsonify(success=True, data=detail)


@admin_bp.route("/badges/backfill")
@require_admin
def admin_badges_backfill():
    """Backfill badges for existing users"""
    try:
        processed_users = []

        try:
            from app.services.achievement_system import achievement_system
            if achievement_system:
                userlist = get_userlist()
                for username in userlist.keys():
                    new_badges = achievement_system.process_user_achievements(username)
                    if new_badges:
                        processed_users.append(f"{username} ({len(new_badges)} badges)")
        except ImportError:
            flash("Achievement-System nicht verfügbar", "warning")
            return redirect(url_for("admin.admin_users"))

        if processed_users:
            flash(f"Badges verarbeitet für: {', '.join(processed_users)}", "success")
        else:
            flash("Keine neuen Badges während Backfill vergeben", "info")

        return redirect(url_for("admin.admin_users"))

    except Exception as e:
        flash(f"Fehler beim Badge-Backfill: {str(e)}", "danger")
        return redirect(url_for("admin.admin_users"))


@admin_bp.route("/data/backfill-september")
@require_admin
def admin_backfill_september():
    """Backfill tracking data from September 2nd"""
    try:
        from app.services.tracking_system import backfill_september_data
        backfill_september_data()
        flash("September data backfill completed successfully! Dashboard now shows complete data from September 2nd.", "success")
    except Exception as e:
        flash(f"Error during September backfill: {str(e)}", "danger")

    return redirect(url_for("admin.admin_users"))
