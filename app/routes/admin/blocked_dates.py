# -*- coding: utf-8 -*-
"""
Admin-Routes für gesperrte Termine-Verwaltung
Feiertags- und benutzerdefinierte Datums-Sperrungsschnittstelle
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
    """Hauptseite für die Verwaltung gesperrter Termine"""
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

        # Extract data from overview dict for template
        all_holidays = overview.get('holidays', [])
        custom_blocks = overview.get('custom_blocks', [])
        holiday_count = len(all_holidays)
        custom_blocks_count = len(custom_blocks)
        upcoming_count = len(upcoming_holidays)

        return render_template("admin_blocked_dates.html",
                             all_holidays=all_holidays,
                             custom_blocks=custom_blocks,
                             holiday_count=holiday_count,
                             custom_blocks_count=custom_blocks_count,
                             upcoming_count=upcoming_count,
                             upcoming_holidays=upcoming_holidays,
                             current_year=current_year,
                             available_years=available_years)

    except Exception as e:
        flash(f"Fehler beim Laden der gesperrten Termine: {str(e)}", "danger")
        return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/blocked-dates/add", methods=["POST"])
@require_admin
def add_blocked_date():
    """Fügt ein benutzerdefiniertes gesperrtes Datum hinzu (mit Support für verschiedene Block-Typen)"""
    try:
        block_type = request.form.get('block_type', 'full_day')
        reason = request.form.get('reason', 'Gesperrt')
        user = session.get('user', 'Admin')

        if block_type == 'full_day':
            date_str = request.form.get('date')
            if not date_str:
                return jsonify({"success": False, "error": "Datum ist erforderlich"}), 400

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

            success = holiday_service.add_custom_block(block_date, reason, user, block_type='full_day')
            message = f"Datum {block_date.strftime('%d.%m.%Y')} erfolgreich gesperrt"

        elif block_type == 'time_range':
            date_str = request.form.get('date')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')

            if not all([date_str, start_time, end_time]):
                return jsonify({"success": False, "error": "Datum, Start- und Endzeit erforderlich"}), 400

            try:
                block_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"success": False, "error": "Ungültiges Datumsformat"}), 400

            # Validate time format
            try:
                datetime.strptime(start_time, '%H:%M')
                datetime.strptime(end_time, '%H:%M')
            except ValueError:
                return jsonify({"success": False, "error": "Ungültiges Zeitformat (HH:MM)"}), 400

            if start_time >= end_time:
                return jsonify({"success": False, "error": "Startzeit muss vor Endzeit liegen"}), 400

            success = holiday_service.add_custom_block(
                block_date, reason, user,
                block_type='time_range',
                start_time=start_time,
                end_time=end_time
            )
            message = f"Zeitbereich {start_time}-{end_time} am {block_date.strftime('%d.%m.%Y')} gesperrt"

        elif block_type == 'date_range':
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')

            if not all([start_date_str, end_date_str]):
                return jsonify({"success": False, "error": "Start- und Enddatum erforderlich"}), 400

            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({"success": False, "error": "Ungültiges Datumsformat"}), 400

            if start_date > end_date:
                return jsonify({"success": False, "error": "Startdatum muss vor Enddatum liegen"}), 400

            days_count = (end_date - start_date).days + 1
            success = holiday_service.add_custom_block(
                start_date, reason, user,
                block_type='date_range',
                end_date=end_date
            )
            message = f"Zeitraum {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')} ({days_count} Tage) gesperrt"

        else:
            return jsonify({"success": False, "error": f"Unbekannter Block-Typ: {block_type}"}), 400

        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "error": "Fehler beim Speichern der Sperrung"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/blocked-dates/remove", methods=["POST"])
@require_admin
def remove_blocked_date():
    """Entfernt ein benutzerdefiniertes gesperrtes Datum (mit Support für Block-Keys)"""
    try:
        # Try to get block_key first (new method), fallback to date (backward compatibility)
        block_key = request.form.get('block_key')
        date_str = request.form.get('date')

        if not block_key and not date_str:
            return jsonify({"success": False, "error": "Block-Key oder Datum erforderlich"}), 400

        # If date_str is provided but no block_key, try to parse it
        if date_str and not block_key:
            try:
                block_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Cannot remove holidays, only custom blocks
                if holiday_service.is_holiday(block_date):
                    return jsonify({
                        "success": False,
                        "error": "Feiertage können nicht entfernt werden"
                    }), 400

                success = holiday_service.remove_custom_block(block_date=block_date)
                message = f"Sperrung für {block_date.strftime('%d.%m.%Y')} entfernt"

            except ValueError:
                return jsonify({"success": False, "error": "Ungültiges Datumsformat"}), 400

        else:
            # Use block_key directly
            success = holiday_service.remove_custom_block(block_key=block_key)
            message = f"Sperrung entfernt"

        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "error": "Fehler beim Entfernen der Sperrung"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/blocked-dates/check", methods=["GET"])
@require_admin
def check_blocked_date():
    """Prüft ob ein bestimmtes Datum gesperrt ist und gibt den Grund zurück"""
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
    """Liefert kommende Feiertage für AJAX-Anfragen"""
    try:
        days_ahead = request.args.get('days', 30, type=int)
        upcoming = holiday_service.get_upcoming_holidays(days_ahead)

        return jsonify({
            "success": True,
            "holidays": upcoming
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500