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
    userlist = get_userlist()
    scores = data_persistence.load_scores()

    # Load all user badges from achievement system
    try:
        from app.services.achievement_system import achievement_system
        all_badges = {}
        for username in userlist.keys():
            try:
                user_badges = achievement_system.get_user_badges(username)
                all_badges[username] = user_badges.get('badges', [])
            except Exception:
                all_badges[username] = []
    except Exception as e:
        print(f"Error loading user badges: {e}")
        all_badges = {}

    # Calculate user statistics
    user_stats = []
    current_month = datetime.now(TZ).strftime("%Y-%m")

    for username in userlist.keys():
        user_score = scores.get(username, {}).get(current_month, 0)
        user_badges = all_badges.get(username, [])
        total_badges = len(user_badges)

        # Calculate total all-time score
        total_score = sum(scores.get(username, {}).values())

        user_stats.append({
            'username': username,
            'current_month_score': user_score,
            'total_score': total_score,
            'total_badges': total_badges,
            'recent_badges': user_badges[-3:] if user_badges else []  # Last 3 badges
        })

    # Sort by current month score
    user_stats.sort(key=lambda x: x['current_month_score'], reverse=True)

    # Calculate statistics for template
    total_users = len(user_stats)
    base_users_count = len(userlist)

    return render_template("admin_users.html",
                         user_stats=user_stats,
                         current_month=current_month,
                         total_users=total_users,
                         base_users_count=base_users_count)


@admin_bp.route("/fix-points")
@require_admin
def admin_fix_points():
    """Point system maintenance and fixes"""
    try:
        # Load current scores
        scores = data_persistence.load_scores()

        # Perform any necessary fixes
        fixed_users = []

        # Example fix: Remove negative scores
        for user, user_scores in scores.items():
            for month, score in user_scores.items():
                if score < 0:
                    scores[user][month] = 0
                    fixed_users.append(f"{user} ({month})")

        # Save fixed scores
        if fixed_users:
            data_persistence.save_scores(scores)
            flash(f"Negative Punkte korrigiert für: {', '.join(fixed_users)}", "success")
        else:
            flash("Keine Probleme im Punktesystem gefunden", "info")

        return redirect(url_for("admin.admin_users"))

    except Exception as e:
        flash(f"Fehler beim Korrigieren der Punkte: {str(e)}", "danger")
        return redirect(url_for("admin.admin_users"))


@admin_bp.route("/debug-points")
@require_admin
def admin_debug_points():
    """Debug point system - show detailed breakdown"""
    try:
        scores = data_persistence.load_scores()

        # Create debug information
        debug_info = {
            'total_users': len(scores),
            'total_months': 0,
            'score_distribution': {},
            'user_details': []
        }

        all_months = set()
        for user, user_scores in scores.items():
            all_months.update(user_scores.keys())

            user_total = sum(user_scores.values())
            debug_info['user_details'].append({
                'user': user,
                'total_score': user_total,
                'months_active': len(user_scores),
                'monthly_breakdown': user_scores
            })

        debug_info['total_months'] = len(all_months)
        debug_info['user_details'].sort(key=lambda x: x['total_score'], reverse=True)

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


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