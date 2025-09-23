# -*- coding: utf-8 -*-
"""
Admin routes for blocked dates management
Holiday and custom date blocking interface
"""

from flask import render_template, request, jsonify, flash, redirect, url_for, session
from datetime import datetime, date, timedelta
import pytz

from app.config.base import slot_config
from app.services.holiday_service import holiday_service
from app.utils.decorators import require_admin
from app.routes.admin import admin_bp

TZ = pytz.timezone(slot_config.TIMEZONE)


@admin_bp.route("/blocked-dates")
@require_admin
def blocked_dates():
    """Main blocked dates management page"""
    try:
        current_year = request.args.get('year', datetime.now(TZ).year, type=int)

        # Get overview for the year
        overview = holiday_service.get_blocked_dates_overview(current_year)

        # Get upcoming holidays for quick reference
        upcoming_holidays = holiday_service.get_upcoming_holidays(90)  # Next 3 months

        # Get available years for dropdown
        available_years = []
        for year_offset in range(-2, 3):  # 2 years back, current, 2 years forward
            year = current_year + year_offset
            available_years.append(year)

        return render_template("admin_blocked_dates.html",
                             overview=overview,
                             upcoming_holidays=upcoming_holidays,
                             current_year=current_year,
                             available_years=available_years)

    except Exception as e:
        flash(f"Error loading blocked dates: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/blocked-dates/add", methods=["POST"])
@require_admin
def add_blocked_date():
    """Add a custom blocked date"""
    try:
        date_str = request.form.get('date')
        reason = request.form.get('reason', 'Gesperrt')
        user = session.get('user', 'Admin')

        if not date_str:
            return jsonify({"success": False, "error": "Datum ist erforderlich"}), 400

        # Parse the date
        try:
            block_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"success": False, "error": "Ungültiges Datumsformat"}), 400

        # Check if it's already a holiday
        if holiday_service.is_holiday(block_date):
            holiday_name = holiday_service.get_holiday_name(block_date)
            return jsonify({
                "success": False,
                "error": f"Datum ist bereits ein Feiertag: {holiday_name}"
            }), 400

        # Add the custom block
        success = holiday_service.add_custom_block(block_date, reason, user)

        if success:
            return jsonify({
                "success": True,
                "message": f"Datum {block_date.strftime('%d.%m.%Y')} erfolgreich gesperrt"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Fehler beim Speichern der Sperrung"
            }), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/blocked-dates/remove", methods=["POST"])
@require_admin
def remove_blocked_date():
    """Remove a custom blocked date"""
    try:
        date_str = request.form.get('date')

        if not date_str:
            return jsonify({"success": False, "error": "Datum ist erforderlich"}), 400

        # Parse the date
        try:
            block_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"success": False, "error": "Ungültiges Datumsformat"}), 400

        # Cannot remove holidays, only custom blocks
        if holiday_service.is_holiday(block_date):
            return jsonify({
                "success": False,
                "error": "Feiertage können nicht entfernt werden"
            }), 400

        # Remove the custom block
        success = holiday_service.remove_custom_block(block_date)

        if success:
            return jsonify({
                "success": True,
                "message": f"Sperrung für {block_date.strftime('%d.%m.%Y')} entfernt"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Fehler beim Entfernen der Sperrung"
            }), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/blocked-dates/check", methods=["GET"])
@require_admin
def check_blocked_date():
    """Check if a specific date is blocked and get reason"""
    try:
        date_str = request.args.get('date')

        if not date_str:
            return jsonify({"success": False, "error": "Datum ist erforderlich"}), 400

        try:
            check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"success": False, "error": "Ungültiges Datumsformat"}), 400

        is_blocked = holiday_service.is_blocked_date(check_date)
        reason = holiday_service.get_blocked_reason(check_date)
        is_holiday = holiday_service.is_holiday(check_date)

        return jsonify({
            "success": True,
            "date": date_str,
            "is_blocked": is_blocked,
            "reason": reason,
            "is_holiday": is_holiday,
            "formatted_date": check_date.strftime('%d.%m.%Y')
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/blocked-dates/upcoming", methods=["GET"])
@require_admin
def get_upcoming_holidays():
    """Get upcoming holidays for AJAX requests"""
    try:
        days_ahead = request.args.get('days', 30, type=int)
        upcoming = holiday_service.get_upcoming_holidays(days_ahead)

        return jsonify({
            "success": True,
            "holidays": upcoming
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500