# -*- coding: utf-8 -*-
"""
Admin dashboard routes
Main admin interface and overview
"""

from flask import render_template, session, redirect, url_for, flash
from datetime import datetime, timedelta
import pytz

from app.config.base import slot_config
from app.core.extensions import data_persistence, tracking_system
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
                'name': 'Blocked Dates',
                'description': 'Zeitslots und Zeiträume sperren',
                'url': '/admin/blocked-dates',
                'icon': 'calendar-x',
                'color': 'from-red-500/20 to-orange-500/20',
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