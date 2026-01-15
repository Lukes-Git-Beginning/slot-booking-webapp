# -*- coding: utf-8 -*-
"""
Admin tracking routes
Show/No-Show Analytics and Appointment Tracking
"""

from flask import render_template, jsonify, request
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


@admin_bp.route("/tracking/api/period-stats")
@require_admin
def api_period_stats():
    """
    API Endpoint für flexible Zeitraum-Statistiken

    Query Parameters:
        type: 'week' | 'month' | 'custom'
        year: Jahr (für week/month)
        week: Wochennummer (für type=week)
        month: Monatsnummer (für type=month)
        start_date: Start-Datum YYYY-MM-DD (für type=custom)
        end_date: End-Datum YYYY-MM-DD (für type=custom)
    """
    try:
        if not tracking_system:
            return jsonify({"success": False, "error": "Tracking-System nicht verfügbar"}), 503

        period_type = request.args.get("type", "week")

        if period_type == "week":
            year = int(request.args.get("year", datetime.now(TZ).year))
            week = int(request.args.get("week", datetime.now(TZ).isocalendar()[1]))
            data = tracking_system.get_weekly_stats(year, week)

        elif period_type == "month":
            year = int(request.args.get("year", datetime.now(TZ).year))
            month = int(request.args.get("month", datetime.now(TZ).month))
            data = tracking_system.get_monthly_stats(year, month)

        else:  # custom
            start_date = request.args.get("start_date", "2025-09-01")
            end_date = request.args.get("end_date", str(datetime.now(TZ).date()))
            data = tracking_system.get_stats_for_period(start_date, end_date)

        return jsonify({
            "success": True,
            "type": period_type,
            "data": data
        })

    except ValueError as e:
        return jsonify({"success": False, "error": f"Ungültige Parameter: {e}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tracking/api/combined-ranking")
@require_admin
def api_combined_ranking():
    """
    API Endpoint für kombiniertes Berater-Ranking

    Query Parameters:
        start_date: Start-Datum YYYY-MM-DD (default: 2025-09-01)
        end_date: End-Datum YYYY-MM-DD (default: heute)
    """
    try:
        from app.services.consultant_ranking import consultant_ranking_service

        start_date = request.args.get("start_date", "2025-09-01")
        end_date = request.args.get("end_date", str(datetime.now(TZ).date()))

        data = consultant_ranking_service.get_ranking_summary(start_date, end_date)

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/tracking/api/consultant-performance")
@require_admin
def api_consultant_performance():
    """
    API Endpoint für reine Show-Rate Performance pro Berater

    Query Parameters:
        start_date: Start-Datum YYYY-MM-DD
        end_date: End-Datum YYYY-MM-DD
    """
    try:
        if not tracking_system:
            return jsonify({"success": False, "error": "Tracking-System nicht verfügbar"}), 503

        start_date = request.args.get("start_date", "2025-09-01")
        end_date = request.args.get("end_date", str(datetime.now(TZ).date()))

        data = tracking_system.get_consultant_performance(start_date, end_date)

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
