# -*- coding: utf-8 -*-
"""
Admin tracking routes
Show/No-Show Analytics and Appointment Tracking
"""

from flask import render_template, jsonify
from datetime import datetime
import pytz

from app.config.base import slot_config
from app.core.extensions import tracking_system
from app.utils.decorators import require_admin
from app.routes.admin import admin_bp

TZ = pytz.timezone(slot_config.TIMEZONE)


@admin_bp.route("/tracking")
@require_admin
def admin_tracking():
    """
    Admin Tracking Dashboard
    Zeigt Show/No-Show Statistiken für:
    - Letzte 5 Werktage
    - Seit 01.09.2025 (Go-Live)
    """
    try:
        if not tracking_system:
            # Fallback wenn tracking_system nicht verfügbar
            return render_template("admin_tracking.html",
                                 last_5_workdays=[],
                                 since_golive={
                                     "start_date": "2025-09-01",
                                     "days_tracked": 0,
                                     "total_slots": 0,
                                     "completed": 0,
                                     "no_shows": 0,
                                     "cancelled": 0,
                                     "appearance_rate": 0.0,
                                     "daily_data": []
                                 },
                                 error="Tracking-System nicht verfügbar")

        # Hole letzte 5 Werktage
        last_5_workdays = tracking_system.get_last_n_workdays_stats(n=5)

        # Hole Stats seit Go-Live (01.09.2025)
        since_golive = tracking_system.get_stats_since_date("2025-09-01")

        return render_template("admin_tracking.html",
                             last_5_workdays=last_5_workdays,
                             since_golive=since_golive,
                             current_date=datetime.now(TZ).strftime("%d.%m.%Y"))

    except Exception as e:
        return render_template("admin_tracking.html",
                             last_5_workdays=[],
                             since_golive={
                                 "start_date": "2025-09-01",
                                 "days_tracked": 0,
                                 "total_slots": 0,
                                 "completed": 0,
                                 "no_shows": 0,
                                 "cancelled": 0,
                                 "appearance_rate": 0.0,
                                 "daily_data": []
                             },
                             error=str(e))


@admin_bp.route("/tracking/api/last-workdays")
@require_admin
def api_last_workdays():
    """
    API Endpoint für letzte N Werktage
    Für AJAX-Updates oder externe Abfragen
    """
    try:
        if not tracking_system:
            return jsonify({"success": False, "error": "Tracking-System nicht verfügbar"}), 503

        n = 5  # Kann über Query-Parameter erweitert werden
        data = tracking_system.get_last_n_workdays_stats(n=n)

        return jsonify({
            "success": True,
            "data": data,
            "count": len(data)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tracking/api/since-golive")
@require_admin
def api_since_golive():
    """
    API Endpoint für Stats seit Go-Live
    Für AJAX-Updates oder Charts
    """
    try:
        if not tracking_system:
            return jsonify({"success": False, "error": "Tracking-System nicht verfügbar"}), 503

        data = tracking_system.get_stats_since_date("2025-09-01")

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
