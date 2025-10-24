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

TZ = pytz.timezone(slot_config.TIMEZONE)


@admin_bp.route("/users")
@require_admin
def admin_users():
    """User management interface"""
    from app.config.base import Config

    userlist = get_userlist()
    admin_users_list = Config.get_admin_users()

    # Build user objects for template
    users = []
    for username, password in userlist.items():
        users.append({
            'username': username,
            'password': password,  # Wird im Template nicht angezeigt, nur "***"
            'email': None,  # TODO: Email-System implementieren
            'active': True,  # Alle User aus USERLIST sind aktiv
            'is_admin': username in admin_users_list,
            'last_login': None  # TODO: Login-Tracking implementieren
        })

    # Sort by username
    users.sort(key=lambda x: x['username'])

    # Calculate statistics
    total_users = len(users)
    active_users = len([u for u in users if u['active']])
    admin_count = len([u for u in users if u['is_admin']])
    online_users = 0  # TODO: Online-Tracking implementieren

    return render_template("admin_users.html",
                         users=users,
                         total_users=total_users,
                         active_users=active_users,
                         admin_count=admin_count,
                         online_users=online_users)


# admin_fix_points and admin_debug_points endpoints removed - not needed for production


@admin_bp.route("/badges/backfill")
@require_admin
def admin_badges_backfill():
    """Backfill badges for existing users"""
    try:
        # This would trigger badge recalculation for all users
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

        # Run the backfill process
        backfill_september_data()

        flash("September data backfill completed successfully! Dashboard now shows complete data from September 2nd.", "success")

    except Exception as e:
        flash(f"Error during September backfill: {str(e)}", "danger")

    return redirect(url_for("admin.admin_users"))