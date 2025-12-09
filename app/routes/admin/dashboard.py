# -*- coding: utf-8 -*-
"""
Admin dashboard routes
Main admin interface and overview
"""

from flask import render_template, session, redirect, url_for, flash, jsonify, request
from datetime import datetime, timedelta
import pytz

from app.config.base import slot_config
from app.core.extensions import data_persistence, tracking_system
from app.services.activity_tracking import activity_tracking
from app.utils.decorators import require_admin
from app.utils.helpers import get_color_mapping_status
from app.routes.admin import admin_bp

TZ = pytz.timezone(slot_config.TIMEZONE)


@admin_bp.route("/dashboard")
@require_admin
def admin_dashboard():
    """Main admin dashboard with Hub-Style card navigation"""
    try:
        # Get quick stats for display
        today_stats = {
            'total_appointments': 0,
            'no_show_rate': 0.0,
            'active_users': 0
        }

        if tracking_system:
            # Hole Stats für heute
            today = datetime.now(TZ).date()
            today_str = str(today)

            try:
                import os
                import json
                metrics_file = os.path.join("data/tracking", "daily_metrics.json")
                if os.path.exists(metrics_file):
                    with open(metrics_file, "r", encoding="utf-8") as f:
                        all_metrics = json.load(f)
                        if today_str in all_metrics:
                            today_metrics = all_metrics[today_str]
                            today_stats['total_appointments'] = today_metrics.get('total_slots', 0)
                            today_stats['no_show_rate'] = today_metrics.get('no_show_rate', 0.0)
            except Exception as e:
                print(f"Error loading today's stats: {e}")

        # Count active users
        from app.utils.helpers import get_userlist
        today_stats['active_users'] = len(get_userlist())

        # Admin Tools für Card-Navigation
        admin_tools = [
            {
                'name': 'Tracking Analytics',
                'description': 'Show/No-Show Statistiken und Termin-Analytics',
                'url': '/admin/tracking',
                'icon': 'bar-chart-3',
                'color': 'from-primary/20 to-secondary/20',
                'status': 'active'
            },
            {
                'name': 'Telefonie System',
                'description': 'Weekly Points Management und Reports',
                'url': '/admin/telefonie',
                'icon': 'phone',
                'color': 'from-blue-500/20 to-indigo-500/20',
                'status': 'active'
            },
            {
                'name': 'User Management',
                'description': 'Benutzer verwalten und Berechtigungen ändern',
                'url': '/admin/users',
                'icon': 'users',
                'color': 'from-purple-500/20 to-pink-500/20',
                'status': 'active'
            },
            {
                'name': 'Online Users',
                'description': 'Live-Tracking aktuell eingeloggter Benutzer',
                'url': '/admin/activity/online-users',
                'icon': 'activity',
                'color': 'from-green-500/20 to-emerald-500/20',
                'status': 'active'
            },
            {
                'name': 'Login History',
                'description': 'Audit-Log aller Login-Versuche und Aktivitäten',
                'url': '/admin/activity/login-history',
                'icon': 'history',
                'color': 'from-cyan-500/20 to-blue-500/20',
                'status': 'active'
            },
            {
                'name': 'Blocked Dates',
                'description': 'Zeitslots und Zeiträume sperren',
                'url': '/admin/blocked-dates',
                'icon': 'calendar-x',
                'color': 'from-red-500/20 to-orange-500/20',
                'status': 'active'
            },
            {
                'name': 'Refactoring Status',
                'description': 'PostgreSQL migration & modernization progress',
                'url': '/admin/refactoring-status',
                'icon': 'trending-up',
                'color': 'from-violet-500/20 to-purple-500/20',
                'status': 'active'
            }
        ]

        return render_template("admin_dashboard.html",
                             admin_tools=admin_tools,
                             today_stats=today_stats,
                             current_time=datetime.now(TZ).strftime("%H:%M"))

    except Exception as e:
        flash(f"Fehler beim Laden des Dashboards: {str(e)}", "danger")
        return redirect(url_for("hub.dashboard"))


# admin_insights endpoint removed - functionality integrated into tracking dashboard


# ===== ACTIVITY TRACKING ENDPOINTS =====

@admin_bp.route("/activity/login-history")
@require_admin
def admin_login_history():
    """Admin-Seite: Login-History aller User"""
    try:
        # Hole letzte 50 Logins
        all_logins = activity_tracking.get_all_login_activity(limit=50)

        # Hole Login-Stats (letzte 30 Tage)
        login_stats = activity_tracking.get_login_stats(days=30)

        return render_template("admin_login_history.html",
                             all_logins=all_logins,
                             login_stats=login_stats,
                             current_time=datetime.now(TZ).strftime("%d.%m.%Y %H:%M"))

    except Exception as e:
        flash(f"Fehler beim Laden der Login-History: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/activity/online-users")
@require_admin
def admin_online_users():
    """Admin-Seite: Aktuell online User"""
    try:
        # Hole online Users (Timeout: 15 Minuten)
        online_users = activity_tracking.get_online_users(timeout_minutes=15)

        return render_template("admin_online_users.html",
                             online_users=online_users,
                             current_time=datetime.now(TZ).strftime("%d.%m.%Y %H:%M"))

    except Exception as e:
        flash(f"Fehler beim Laden der Online-User: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/refactoring-status")
@require_admin
def refactoring_status():
    """Refactoring progress dashboard"""
    try:
        from app.services.refactoring_status_service import refactoring_status_service

        status = refactoring_status_service.get_full_status()

        return render_template("admin_refactoring_status.html",
                             status=status,
                             current_time=datetime.now(TZ).strftime("%d.%m.%Y %H:%M"))

    except Exception as e:
        flash(f"Fehler beim Laden des Refactoring Status: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/api/activity/online-users")
@require_admin
def api_online_users():
    """API: Aktuell online User (für AJAX-Updates)"""
    try:
        online_users = activity_tracking.get_online_users(timeout_minutes=15)

        return jsonify({
            "success": True,
            "online_users": online_users,
            "count": len(online_users),
            "timestamp": datetime.now(TZ).isoformat()
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/activity/login-stats")
@require_admin
def api_login_stats():
    """API: Login-Statistiken (für Dashboards)"""
    try:
        # Parameter aus Query-String
        days = int(request.args.get('days', 30))
        username = request.args.get('username', None)

        stats = activity_tracking.get_login_stats(username=username, days=days)

        return jsonify({
            "success": True,
            "stats": stats,
            "timestamp": datetime.now(TZ).isoformat()
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/activity/user/<username>/history")
@require_admin
def api_user_login_history(username):
    """API: Login-History eines einzelnen Users"""
    try:
        limit = int(request.args.get('limit', 20))

        user_history = activity_tracking.get_user_login_history(username, limit=limit)

        return jsonify({
            "success": True,
            "username": username,
            "history": user_history,
            "count": len(user_history),
            "timestamp": datetime.now(TZ).isoformat()
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500